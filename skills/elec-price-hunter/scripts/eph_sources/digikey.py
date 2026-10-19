"""DigiKey Product Information API v4 (own app: DIGIKEY_CLIENT_ID / DIGIKEY_CLIENT_SECRET).

Falls back to pcbparts.dev for single-part lookup without credentials.
OAuth client-credentials token lasts 10 min; cached in the system temp dir (approach from kicad-happy, MIT).
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from urllib.parse import quote, urlencode

from . import pcbparts
from .common import NotConfigured, SchemaError, SourceError, breaks, fix_url, http, num, record

NAME = "digikey"
HOST = "https://api.digikey.com"
TOKEN_CACHE = os.path.join(tempfile.gettempdir(), "eph_digikey_token.json")


def _creds():
    return os.environ.get("DIGIKEY_CLIENT_ID", "").strip(), os.environ.get("DIGIKEY_CLIENT_SECRET", "").strip()


def _token():
    cid, sec = _creds()
    try:
        with open(TOKEN_CACHE) as f:
            c = json.load(f)
        if c.get("client_id") == cid and c.get("expires", 0) > time.time() + 30:
            return c["token"]
    except (OSError, ValueError, KeyError):
        pass
    status, _, raw = http(HOST + "/v1/oauth2/token", data=urlencode(
        {"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"}),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        d = json.loads(raw)
    except ValueError:
        d = {}
    if status != 200 or not d.get("access_token"):
        raise SourceError(f"digikey oauth HTTP {status}: {d.get('ErrorMessage') or raw[:200]!r}")
    fd = os.open(TOKEN_CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"client_id": cid, "token": d["access_token"],
                   "expires": time.time() + int(d.get("expires_in", 600))}, f)
    return d["access_token"]


def _api(method, path, body=None):
    cid, _ = _creds()
    h = {"X-DIGIKEY-Client-Id": cid, "Authorization": f"Bearer {_token()}",
         "X-DIGIKEY-Locale-Currency": os.environ.get("DIGIKEY_CURRENCY", "USD"),
         "X-DIGIKEY-Locale-Site": os.environ.get("DIGIKEY_SITE", "US")}
    status, _, raw = http(HOST + path, data=body, headers=h, method=method)
    if status == 404:
        return None
    try:
        d = json.loads(raw)
    except ValueError:
        raise SourceError(f"digikey HTTP {status}: {raw[:200]!r}") from None
    if status != 200:
        raise SourceError(f"digikey HTTP {status}: {d.get('ErrorMessage') or d.get('detail') or d}")
    return d


def _rec(p, currency):
    if "ManufacturerProductNumber" not in p:
        raise SchemaError(f"digikey: product keys {sorted(p)[:12]}")
    var = p.get("ProductVariations") or []
    # Cut Tape is the buyable-in-small-quantity variant; otherwise the first.
    v = next((x for x in var if "Cut Tape" in ((x.get("PackageType") or {}).get("Name") or "")), var[0] if var else {})
    pb = breaks((b.get("BreakQuantity"), num(b.get("UnitPrice"))) for b in (v.get("StandardPricing") or []))
    params = {x.get("ParameterText"): x.get("ValueText") for x in (p.get("Parameters") or [])
              if x.get("ValueText") not in (None, "", "-")}
    desc = p.get("Description") or {}
    return record(
        source=NAME, currency=currency, tax="excl.", sku=v.get("DigiKeyProductNumber"),
        mpn=p["ManufacturerProductNumber"], brand=(p.get("Manufacturer") or {}).get("Name"),
        description=desc.get("ProductDescription"), category=(p.get("Category") or {}).get("Name"),
        stock=p.get("QuantityAvailable"), moq=v.get("MinimumOrderQuantity"),
        pack_qty=v.get("StandardPackage"), pack_unit=(v.get("PackageType") or {}).get("Name"),
        price_breaks=pb, datasheet=fix_url(p.get("DatasheetUrl")), url=p.get("ProductUrl"),
        params=params or None, lifecycle=(p.get("ProductStatus") or {}).get("Status"),
        note=f"{len(var)} packaging variants" if len(var) > 1 else None,
    )


def search(keyword, limit=10):
    if not all(_creds()):
        raise NotConfigured("DIGIKEY_CLIENT_ID/SECRET not set (keyword search needs them; part lookup falls back)")
    d = _api("POST", "/products/v4/search/keyword", {"Keywords": keyword, "Limit": min(limit, 50), "Offset": 0})
    cur = (d.get("SearchLocaleUsed") or {}).get("Currency") or "USD"
    return d.get("ProductsCount"), [_rec(p, cur) for p in (d.get("Products") or [])[:limit]]


def part(mpn):
    if all(_creds()):
        d = _api("GET", f"/products/v4/search/{quote(mpn, safe='')}/productdetails")
        if not d or not d.get("Product"):
            return []
        cur = (d.get("SearchLocaleUsed") or {}).get("Currency") or "USD"
        return [_rec(d["Product"], cur)]
    res = pcbparts.call("digikey_get_part", {"product_number": mpn})
    res = res.get("results") or ([res] if res.get("mfr_part_number") else [])
    return [pcbparts.to_record(NAME, r) for r in res]
