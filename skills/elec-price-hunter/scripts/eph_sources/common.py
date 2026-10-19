"""Shared HTTP helpers, the canonical part record and quantity pricing."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 20

FIELDS = ("source", "currency", "tax", "sku", "mpn", "brand", "package", "description",
          "category", "stock", "moq", "multiple", "pack_qty", "pack_unit", "price_breaks",
          "datasheet", "url", "params", "lifecycle", "jlc_class", "alternates", "note")


class SourceError(Exception):
    """Source unreachable, refused, or returned an error."""


class SchemaError(SourceError):
    """Source answered, but the payload no longer has the expected layout."""


class NotConfigured(SourceError):
    """Source needs credentials that are not set."""


def http(url, data=None, headers=None, method=None, timeout=TIMEOUT):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    h.update(headers or {})
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        data = data.encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SourceError(f"network: {e}") from e


def get_json(url, **kw):
    status, _, body = http(url, **kw)
    if status != 200:
        raise SourceError(f"HTTP {status}: {body[:200]!r}")
    try:
        return json.loads(body)
    except ValueError:
        raise SourceError(f"non-JSON response: {body[:200]!r}") from None


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def record(**kw):
    rec = dict.fromkeys(FIELDS)
    rec.update(kw)
    rec["fetched_at"] = now()
    return rec


def num(v):
    """'$1,234.50' / '7,50 €' / 3 / None -> float or None."""
    if v is None or isinstance(v, (int, float)):
        return v
    s = re.sub(r"[^\d.,\-]", "", str(v))
    if not s or s in ("-", ".", ","):
        return None
    if "," in s and "." in s:
        s = s.replace(",", "")                       # 1,234.50
    elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
        s = s.replace(",", ".")                      # 7,50 (decimal comma)
    else:
        s = s.replace(",", "")                       # 1,234
    try:
        return float(s)
    except ValueError:
        return None


def intnum(v):
    f = num(v)
    return None if f is None else int(f)


def breaks(pairs):
    """[(qty, price), ...] -> sorted [{'qty', 'price'}], dropping unusable rows."""
    out = [{"qty": int(q), "price": float(p)} for q, p in pairs
           if q is not None and p is not None and p > 0]
    return sorted(out, key=lambda b: b["qty"])


def at_qty(rec, qty):
    """Tier price for buying `qty`, after MOQ and order multiple."""
    pb = rec.get("price_breaks") or []
    if not pb:
        return {"qty": qty, "error": "no price"}
    buy = max(qty, rec.get("moq") or 1, pb[0]["qty"])
    mult = rec.get("multiple") or 1
    if mult > 1 and buy % mult:
        buy += mult - buy % mult
    tier = [b for b in pb if b["qty"] <= buy][-1]
    stock = rec.get("stock")
    return {"qty": qty, "buy": buy, "tier": tier["qty"], "unit": tier["price"],
            "total": round(tier["price"] * buy, 4), "currency": rec.get("currency"),
            "stock_ok": None if stock is None else stock >= buy}


def is_lcsc_code(s):
    return re.fullmatch(r"[Cc]\d{1,10}", s.strip()) is not None


def fix_url(u):
    if not u:
        return None
    u = u.strip()
    if u.startswith("//"):
        u = "https:" + u
    m = re.search(r"[?&]gotoUrl=([^&]+)", u)          # TI redirect wrapper
    if m:
        from urllib.parse import unquote
        u = unquote(m.group(1))
    return u
