"""JLCPCB SMT assembly library via jlcsearch (tscircuit): USD prices and Basic/Extended, by C code.

Its keyword search ranks poorly for model numbers (STM32G030F6P6 -> an unrelated TVS),
so it is only used for exact C-code lookups.
"""
from __future__ import annotations

from urllib.parse import urlencode

from .common import SchemaError, breaks, get_json, num, record

NAME = "jlc"
API = "https://jlcsearch.tscircuit.com/components/list.json"


def _price(s):
    """'1-9:1.4415,10-29:1.2527,1000-:0.9192' -> breaks."""
    pairs = []
    for seg in (s or "").split(","):
        rng, _, p = seg.partition(":")
        pairs.append((num(rng.split("-")[0]), num(p)))
    return breaks(pairs)


def _rec(c):
    if "lcsc" not in c:
        raise SchemaError(f"jlc: component keys {sorted(c)[:12]}")
    pb = _price(c.get("price")) if isinstance(c.get("price"), str) else breaks([(1, num(c.get("price1")))])
    code = f"C{c['lcsc']}"
    cls = "Basic" if c.get("is_basic") else ("Preferred" if c.get("is_preferred") else "Extended")
    return record(
        source=NAME, currency="USD", tax="excl.", sku=code, mpn=c.get("mfr"), package=c.get("package"),
        description=c.get("description"), category=c.get("subcategory") or c.get("category"),
        stock=c.get("stock"), moq=pb[0]["qty"] if pb else None, price_breaks=pb,
        url=f"https://jlcpcb.com/partdetail/{code}", jlc_class=cls,
        note="JLC assembly stock (not LCSC retail)",
    )


def search(keyword, limit=10, package=None):
    q = {"search": keyword, "limit": limit}
    if package:
        q["package"] = package
    d = get_json(API + "?" + urlencode(q))
    if not isinstance(d.get("components"), list):
        raise SchemaError(f"jlc: unexpected payload keys {list(d)}")
    return None, [_rec(c) for c in d["components"][:limit]]


def part(code):
    _, recs = search(code.upper(), limit=5)
    hit = [r for r in recs if r["sku"].upper() == code.upper()]
    return hit[0] if hit else None
