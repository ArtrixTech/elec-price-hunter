"""LCSC China (szlcsc.com) via the JLCEDA Pro product search: CNY tier prices, no login."""
from __future__ import annotations

from urllib.parse import urlencode

from .common import SchemaError, breaks, get_json, intnum, is_lcsc_code, num, record

NAME = "lceda"
API = "https://pro.lceda.cn/api/eda/product/search"
ATTA = "https://atta.szlcsc.com"


def _query(keyword, page=1, size=20):
    d = get_json(API + "?" + urlencode({"keyword": keyword, "currPage": page, "pageSize": size}))
    res = d.get("result")
    if not isinstance(res, dict) or not isinstance(res.get("productList"), list):
        raise SchemaError(f"lceda: unexpected payload keys {list(d)}")
    return res.get("total") or 0, res["productList"]


def _rec(p):
    if "code" not in p or "priceList" not in p:
        raise SchemaError(f"lceda: product missing code/priceList, keys {sorted(p)[:12]}")
    pb = breaks((t.get("startNumber"), num(t.get("price"))) for t in (p.get("priceList") or []))
    pdf = p.get("pdfFileUrl")
    pack = intnum(p.get("packageNumber"))
    # stockNumber is counted in order units of splitRatio pieces (C25744: 4532 x 100 = LCSC's 453200).
    split = intnum(p.get("splitRatio")) or 1
    stock = intnum(p.get("stockNumber"))
    return record(
        source=NAME, currency="CNY", tax="incl. 13% VAT", sku=p["code"], mpn=p.get("model"),
        brand=p.get("brandName"), package=p.get("standard"), description=p.get("name"),
        category=p.get("catalogName"), stock=None if stock is None else stock * split,
        moq=pb[0]["qty"] if pb else None, multiple=split,
        pack_qty=pack, pack_unit=p.get("packageUnit"), price_breaks=pb,
        datasheet=(ATTA + pdf) if pdf and pdf.startswith("/") else pdf,
        url=f"https://item.szlcsc.com/{p['id']}.html" if p.get("id") else None,
        jlc_class=p.get("JLCPCB Part Class"),
        note=None if pb else "listed without price (isShowPrice=%s)" % p.get("isShowPrice"),
    )


def search(keyword, limit=10):
    total, items = _query(keyword, size=max(limit, 1))
    return total, [_rec(p) for p in items[:limit]]


def part(code):
    """Exact LCSC code (C8734). Returns None when the code is unknown."""
    if not is_lcsc_code(code):
        raise ValueError(f"not an LCSC code: {code}")
    code = code.upper()
    _, items = _query(code, size=20)
    hit = [p for p in items if str(p.get("code", "")).upper() == code]
    return _rec(hit[0]) if hit else None
