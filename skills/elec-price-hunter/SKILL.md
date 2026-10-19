---
name: elec-price-hunter
description: Look up electronic components - search by keyword or model, CNY and USD tier prices, stock, MOQ, parameters and datasheet PDFs from LCSC China (szlcsc via JLCEDA), LCSC international, JLCPCB assembly library, Mouser and DigiKey. Use when the user asks for a part's price, stock, datasheet, specs, an LCSC C-number, or to compare distributors. 元器件检索、立创价格、人民币报价、datasheet、参数、库存。
---

# elec-price-hunter

All data comes from `scripts/eph.py` (Python 3 stdlib, no install). Output is JSON.

```bash
S=<this skill dir>/scripts/eph.py
python3 $S search "<keyword or model>" [--source lceda|mouser|digikey] [--limit 10]
python3 $S part <C-code|MPN> [more ids...] [--sources lceda,lcsc,jlc,mouser,digikey] [--qty 10,100,1000]
python3 $S datasheet <C-code|MPN|PDF URL> [-o DIR]
python3 $S check        # live health check of every source
```

## Hard rules

1. Every part number, price, stock figure and parameter you report must come from the script output of this session. Never fill in, guess or "recall" one. If the script says not found, say not found.
2. Always state currency and tax basis with a price: `lceda` is CNY incl. 13% VAT (立创标价); all others are USD excl. tax. Do not convert currencies unless asked, and label any conversion as an estimate.
3. When a model search returns several parts (`candidates`, or several records with different brands/packages), list them and let the user choose. Do not silently pick one.
4. Report `errors` per source honestly ("Mouser: not configured", "DigiKey: upstream failed"). A failed source is not "out of stock".
5. Give the source and `fetched_at` time when presenting prices; prices change daily.

## Which command

| Need | Command |
| --- | --- |
| Find parts from a description ("10k 0402", "LDO 3.3V SOT-23") | `search` (default lceda: CNY, Chinese catalogue, best coverage) |
| Price/stock of a known C code or model, all distributors | `part` |
| Cost at a build quantity | `part ... --qty N` → `at_qty[]`: `buy` (after MOQ/multiple/first tier), `unit`, `total`, `stock_ok` |
| Specs | `part` → `params` (from `lcsc`, `mouser`, `digikey`); for detail read the datasheet |
| Datasheet | `datasheet` downloads the PDF, then read the file |
| Many parts (BOM) | `part id1 id2 ...` in one call; do the BOM arithmetic yourself from `at_qty` |

`part` with a model number resolves it to C codes by an exact model match on lceda, then queries
lcsc and jlc by C code and Mouser/DigiKey by model. With a C code, the model from lceda/lcsc is used
for Mouser/DigiKey.

## Sources

| source | data | needs |
| --- | --- | --- |
| `lceda` | 立创商城 CNY tiers, stock, pack size, datasheet, JLC part class, search | nothing |
| `lcsc` | LCSC.com USD tiers, structured params, datasheet, alternates, lifecycle | nothing (C code only) |
| `jlc` | JLCPCB assembly stock and USD price, Basic/Extended | nothing (C code only) |
| `mouser` | USD tiers, stock, lead time, params | `MOUSER_SEARCH_API_KEY`; without it, part lookup goes through the shared pcbparts.dev quota and `search` is unavailable |
| `digikey` | USD tiers per packaging, params, status | `DIGIKEY_CLIENT_ID` + `DIGIKEY_CLIENT_SECRET`; without them, part lookup goes through pcbparts.dev |

Record fields: `source currency tax sku mpn brand package description category stock moq multiple
pack_qty pack_unit price_breaks[{qty,price}] datasheet url params lifecycle jlc_class alternates note fetched_at`.
`null` means the source does not provide it.

## Reading the numbers

- `price_breaks[0].qty` is the smallest buyable quantity (lceda passives often start at 100).
- LCSC USD ≈ lceda CNY / 6.07 for most parts; a large deviation means different price lists, not an error.
- `jlc` stock is the assembly warehouse, separate from LCSC retail stock.
- lceda prices are list prices; coupons, member prices and shipping are not included.

## When things fail

- `SchemaError`: the upstream API changed layout. Report it; do not work around it with guesses.
- `check` exits non-zero if any source is down; run it when results look wrong.
- These are undocumented endpoints for low-volume interactive use. Do not loop over thousands of parts.
