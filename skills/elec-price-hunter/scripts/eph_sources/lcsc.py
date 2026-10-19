"""LCSC international (lcsc.com): USD tier prices, parameters, datasheet, alternates. Detail by C code only."""
from __future__ import annotations

from urllib.parse import urlencode

from .common import SchemaError, breaks, get_json, intnum, is_lcsc_code, num, record

NAME = "lcsc"
API = "https://wmsc.lcsc.com/ftps/wm/product/detail"


def _rec(r):
    if "productCode" not in r or "productPriceList" not in r:
        raise SchemaError(f"lcsc: result missing productCode/productPriceList, keys {sorted(r)[:12]}")
    pb = breaks((t.get("ladder"), num(t.get("usdPrice") or t.get("productPrice")))
                for t in (r.get("productPriceList") or []))
    params = {p.get("paramNameEn") or p.get("paramName"): p.get("paramValueEn") or p.get("paramValue")
              for p in (r.get("paramVOList") or []) if p.get("paramValueEn") not in (None, "", "-")}
    alts = [a.get("productCode") for a in (r.get("alternatePartList") or []) if a.get("productCode")]
    return record(
        source=NAME, currency=r.get("currencyType") or "USD", tax="excl.", sku=r["productCode"],
        mpn=r.get("productModel"), brand=r.get("brandNameEn"), package=r.get("encapStandard"),
        description=r.get("productIntroEn") or r.get("productNameEn"), category=r.get("catalogName"),
        stock=intnum(r.get("stockNumber")), moq=intnum(r.get("minBuyNumber")) or (pb[0]["qty"] if pb else None),
        multiple=intnum(r.get("split")), pack_qty=intnum(r.get("minPacketNumber")),
        pack_unit=r.get("minPacketUnit"), price_breaks=pb, datasheet=r.get("pdfUrl"),
        url=r.get("url") or f"https://www.lcsc.com/product-detail/{r['productCode']}.html",
        params=params or None, lifecycle=r.get("productCycle"), alternates=alts or None,
    )


def part(code):
    if not is_lcsc_code(code):
        raise ValueError(f"not an LCSC code: {code}")
    d = get_json(API + "?" + urlencode({"productCode": code.upper()}))
    if "result" not in d:
        raise SchemaError(f"lcsc: unexpected payload keys {list(d)}")
    return _rec(d["result"]) if d["result"] else None
