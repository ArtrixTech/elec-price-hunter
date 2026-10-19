"""Mouser Search API v1 (own key: MOUSER_SEARCH_API_KEY). Falls back to pcbparts.dev without a key.

Field notes adapted from kicad-happy (MIT, Andrew Klofas): prices and stock are strings,
IsDiscontinued is "true"/"false", Mouser SKUs carry a vendor prefix (511-...).
"""
from __future__ import annotations

import json
import os

from . import pcbparts
from .common import NotConfigured, SchemaError, SourceError, breaks, http, intnum, num, record

NAME = "mouser"
API = "https://api.mouser.com/api/v1/search"


def _key():
    return os.environ.get("MOUSER_SEARCH_API_KEY", "").strip()


def _post(path, body):
    status, _, raw = http(f"{API}/{path}?apiKey={_key()}", data=body)
    try:
        d = json.loads(raw)
    except ValueError:
        raise SourceError(f"mouser HTTP {status}: {raw[:200]!r}") from None
    errs = d.get("Errors") or []
    if errs:
        raise SourceError("mouser: " + "; ".join(e.get("Message", str(e)) for e in errs))
    if status != 200 or "SearchResults" not in d:
        raise SchemaError(f"mouser HTTP {status}: keys {list(d)}")
    return (d["SearchResults"] or {}).get("NumberOfResult"), (d["SearchResults"] or {}).get("Parts") or []


def _rec(p):
    if "ManufacturerPartNumber" not in p:
        raise SchemaError(f"mouser: part keys {sorted(p)[:12]}")
    pb = breaks((b.get("Quantity"), num(b.get("Price"))) for b in (p.get("PriceBreaks") or []))
    cur = next((b.get("Currency") for b in (p.get("PriceBreaks") or []) if b.get("Currency")), "USD")
    params = {a.get("AttributeName"): a.get("AttributeValue") for a in (p.get("ProductAttributes") or [])}
    life = p.get("LifecycleStatus") or ("Discontinued" if str(p.get("IsDiscontinued")).lower() == "true" else None)
    return record(
        source=NAME, currency=cur, tax="excl.", sku=p.get("MouserPartNumber"), mpn=p["ManufacturerPartNumber"],
        brand=p.get("Manufacturer"), description=p.get("Description"), category=p.get("Category"),
        stock=intnum(p.get("AvailabilityInStock")) or 0, moq=intnum(p.get("Min")), multiple=intnum(p.get("Mult")),
        price_breaks=pb, datasheet=p.get("DataSheetUrl") or None, url=p.get("ProductDetailUrl"),
        params=params or None, lifecycle=life,
        alternates=[p["SuggestedReplacement"]] if p.get("SuggestedReplacement") else None,
        note=f"lead time {p['LeadTime']}" if p.get("LeadTime") else None,
    )


def search(keyword, limit=10):
    if not _key():
        raise NotConfigured("MOUSER_SEARCH_API_KEY not set (keyword search needs it; part lookup falls back)")
    total, parts = _post("keyword", {"SearchByKeywordRequest": {
        "keyword": keyword, "records": limit, "startingRecord": 0, "searchOptions": "", "searchWithYourSignUpLanguage": ""}})
    return total, [_rec(p) for p in parts[:limit]]


def part(mpn):
    """Exact MPN (or Mouser SKU). Returns all exact matches (packaging variants), [] if none."""
    if _key():
        _, parts = _post("partnumber", {"SearchByPartRequest": {"mouserPartNumber": mpn, "partSearchOptions": "Exact"}})
        recs = [_rec(p) for p in parts]
    else:
        res = pcbparts.call("mouser_get_part", {"part_number": mpn}).get("results") or []
        recs = [pcbparts.to_record(NAME, r) for r in res]
    u = mpn.upper()
    return [r for r in recs if u in ((r["mpn"] or "").upper(), (r["sku"] or "").upper())]
