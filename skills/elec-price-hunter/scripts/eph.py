#!/usr/bin/env python3
"""elec-price-hunter: component search, prices (CNY + USD), stock, parameters and datasheets.

  eph.py search <keyword> [--source lceda|mouser|digikey] [--limit N]
  eph.py part <C-code|MPN>... [--sources lceda,lcsc,jlc,mouser,digikey] [--qty 1,100,1000]
  eph.py datasheet <C-code|MPN|URL> [-o DIR]
  eph.py check            # live contract test of every source

Output is JSON on stdout. Every record carries source, currency, tax basis and fetched_at.
A source that fails is listed under "errors"; nothing is filled in for it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eph_sources import SOURCES  # noqa: E402
from eph_sources.common import NotConfigured, SourceError, at_qty, http, is_lcsc_code  # noqa: E402

DEFAULT_PART_SOURCES = ["lceda", "lcsc", "jlc", "mouser", "digikey"]


def err(e):
    kind = "not_configured" if isinstance(e, NotConfigured) else type(e).__name__
    return {"type": kind, "message": str(e)}


def run(fn, *a):
    try:
        return fn(*a), None
    except (SourceError, ValueError) as e:
        return None, err(e)


def as_list(v):
    return [] if v is None else (v if isinstance(v, list) else [v])


def with_qty(rec, qtys):
    if qtys:
        rec["at_qty"] = [at_qty(rec, q) for q in qtys]
    return rec


# ---- part ----
def lookup(ident, sources, qtys):
    """One identifier across sources. C codes resolve to an MPN for the overseas distributors."""
    ident = ident.strip()
    out = {"query": ident, "records": [], "errors": {}, "not_found": []}
    codes, mpn = [], None
    if is_lcsc_code(ident):
        codes = [ident.upper()]
    else:
        mpn = ident

    china = [s for s in ("lceda", "lcsc", "jlc") if s in sources]
    if mpn and china:
        # Model -> C codes through the lceda search; only exact model matches count.
        res, e = run(SOURCES["lceda"].search, mpn, 20)
        if e:
            out["errors"]["lceda"] = e
        else:
            exact = [r for r in res[1] if (r["mpn"] or "").upper() == mpn.upper()]
            codes = [r["sku"] for r in exact]
            if not codes:
                out["not_found"].append("lceda")
                near = [{"sku": r["sku"], "mpn": r["mpn"], "brand": r["brand"]} for r in res[1][:8]]
                if near:
                    out["candidates"] = near

    jobs = [(s, c) for c in codes for s in china]
    with ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(run, SOURCES[s].part, c): (s, c) for s, c in jobs}
        for f, (s, c) in futs.items():
            rec, e = f.result()
            if e:
                out["errors"][f"{s}:{c}"] = e
            elif not rec:
                out["not_found"].append(f"{s}:{c}")
            else:
                out["records"].append(with_qty(rec, qtys))

    if not mpn:
        mpn = next((r["mpn"] for r in out["records"] if r["source"] in ("lceda", "lcsc") and r["mpn"]), None)
    overseas = [s for s in ("mouser", "digikey") if s in sources]
    if mpn and overseas:
        with ThreadPoolExecutor(2) as ex:
            futs = {ex.submit(run, SOURCES[s].part, mpn): s for s in overseas}
            for f, s in futs.items():
                recs, e = f.result()
                if e:
                    out["errors"][s] = e
                elif not recs:
                    out["not_found"].append(f"{s}:{mpn}")
                else:
                    out["records"] += [with_qty(r, qtys) for r in as_list(recs)]
    order = {s: i for i, s in enumerate(DEFAULT_PART_SOURCES)}
    out["records"].sort(key=lambda r: (order.get(r["source"], 9), r["sku"] or ""))
    return out


# ---- datasheet ----
def download(url, out_dir, stem):
    status, headers, body = http(url, headers={"Accept": "application/pdf,*/*"}, timeout=60)
    if status != 200:
        raise SourceError(f"HTTP {status}")
    if not body.startswith(b"%PDF"):
        raise SourceError(f"not a PDF ({headers.get('Content-Type')}, {len(body)} bytes)")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, re.sub(r"[^\w.\-]+", "_", stem) + ".pdf")
    with open(path, "wb") as f:
        f.write(body)
    return {"path": path, "bytes": len(body), "url": url}


def datasheet(ident, out_dir):
    if re.match(r"https?://", ident):
        return {"query": ident, **download(ident, out_dir, os.path.basename(ident.split("?")[0]) or "datasheet")}
    info = lookup(ident, DEFAULT_PART_SOURCES, None)
    tried = []
    seen = set()
    for r in info["records"]:
        u = r.get("datasheet")
        if not u or u in seen:
            continue
        seen.add(u)
        try:
            d = download(u, out_dir, f"{r['mpn'] or ident}_{r['sku'] or r['source']}")
            return {"query": ident, "source": r["source"], "sku": r["sku"], "mpn": r["mpn"], **d}
        except SourceError as e:
            tried.append({"source": r["source"], "url": u, "error": str(e)})
    return {"query": ident, "error": "no downloadable datasheet", "tried": tried,
            "lookup_errors": info["errors"], "not_found": info["not_found"]}


# ---- check ----
CHECKS = [("lceda", "part", "C8734"), ("lceda", "search", "10k 0402"), ("lcsc", "part", "C8734"),
          ("jlc", "part", "C8734"), ("mouser", "part", "STM32F103C8T6"), ("digikey", "part", "STM32F103C8T6")]


def check():
    rows = []
    for s, op, arg in CHECKS:
        res, e = run(getattr(SOURCES[s], op), arg)
        recs = as_list(res[1] if op == "search" and res else res)
        ok = bool(recs) and all(r.get("price_breaks") for r in recs[:1])
        rows.append({"source": s, "op": op, "arg": arg, "ok": ok and not e,
                     "detail": e or (f"{len(recs)} records, first {recs[0]['sku']} "
                                     f"{recs[0]['currency']} {recs[0]['price_breaks'][:1]}" if recs else "empty")})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="eph.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("keyword")
    s.add_argument("--source", default="lceda", choices=["lceda", "mouser", "digikey"])
    s.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("part")
    p.add_argument("ids", nargs="+")
    p.add_argument("--sources", default=",".join(DEFAULT_PART_SOURCES))
    p.add_argument("--qty", default="")
    d = sub.add_parser("datasheet")
    d.add_argument("id")
    d.add_argument("-o", "--out", default="datasheets")
    sub.add_parser("check")
    a = ap.parse_args(argv)

    if a.cmd == "search":
        res, e = run(SOURCES[a.source].search, a.keyword, a.limit)
        out = {"query": a.keyword, "source": a.source, "error": e} if e else \
              {"query": a.keyword, "source": a.source, "total": res[0], "records": res[1]}
    elif a.cmd == "part":
        srcs = [x.strip() for x in a.sources.split(",") if x.strip()]
        bad = [x for x in srcs if x not in SOURCES]
        if bad:
            ap.error(f"unknown sources {bad}")
        qtys = [int(q) for q in a.qty.split(",") if q.strip()]
        out = [lookup(i, srcs, qtys) for i in a.ids]
        out = out[0] if len(out) == 1 else out
    elif a.cmd == "datasheet":
        out = datasheet(a.id, a.out)
    else:
        out = check()
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    failed = (a.cmd == "check" and not all(r["ok"] for r in out)) or (isinstance(out, dict) and out.get("error"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
