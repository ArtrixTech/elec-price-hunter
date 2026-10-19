"""Keyless fallback for Mouser/DigiKey through the hosted pcbparts MCP (https://pcbparts.dev/mcp).

Shared daily quota on their side; used only when the user has no own API key.
"""
from __future__ import annotations

import json

from .common import SchemaError, SourceError, breaks, http, num, record

URL = "https://pcbparts.dev/mcp"


def call(tool, args):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}
    status, _, raw = http(URL, data=body, headers={"Accept": "application/json, text/event-stream"}, timeout=40)
    if status != 200:
        raise SourceError(f"pcbparts HTTP {status}: {raw[:200]!r}")
    text = raw.decode("utf-8", "replace")
    # Reply is plain JSON or an SSE stream ("data: {...}").
    lines = (l[5:].strip() if l.startswith("data:") else l.strip() for l in text.splitlines())
    line = next((l for l in lines if l.startswith("{")), None)
    try:
        msg = json.loads(line)
        payload = json.loads(msg["result"]["content"][0]["text"])
    except (TypeError, ValueError, KeyError, IndexError):
        raise SchemaError(f"pcbparts: unexpected reply {text[:200]!r}") from None
    if isinstance(payload, dict) and payload.get("error"):
        raise SourceError(f"pcbparts: {payload['error']}")
    return payload


def to_record(src, r):
    if "mfr_part_number" not in r and "part_number" not in r:
        raise SchemaError(f"pcbparts: result keys {sorted(r)[:12]}")
    pb = breaks((b.get("qty"), num(b.get("price"))) for b in (r.get("price_breaks") or []))
    params = r.get("parameters") or None
    return record(
        source=src, currency=r.get("currency") or "USD", tax="excl.", sku=r.get("part_number"),
        mpn=r.get("mfr_part_number"), brand=r.get("manufacturer"), description=r.get("description"),
        category=r.get("category"), stock=r.get("stock"), moq=r.get("min_qty"),
        multiple=r.get("multiple"), price_breaks=pb, datasheet=r.get("datasheet_url") or None,
        url=r.get("product_url"), params=params, lifecycle=r.get("lifecycle"),
        note="via pcbparts.dev (no own API key)",
    )
