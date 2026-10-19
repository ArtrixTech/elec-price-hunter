# Devlog

## feat: add elec-price-hunter component lookup skill

`(pending)` | 2026-10-19

- **Changes**: New repo. `SKILL.md` + stdlib CLI `eph.py` (`search`/`part`/`datasheet`/`check`); adapters lceda (立创 CNY), lcsc (USD, params, datasheet, alternates), jlc (jlcsearch, by C code), mouser/digikey (own keys, keyless fallback via pcbparts.dev); 16 offline tests with recorded payloads; AGENTS.md (upstream 78c3a94), Architecture.md, README.
- **Reason**: No existing skill/MCP gives 立创 CNY prices; product scope is reliable search + price + datasheet + params, China and overseas, lceda/LCSC first.
- **User feedback**: "好用、可靠的元件检索、报价、datasheet、参数等获取的skills。海外国内都要。接入lceda/lcsc为主。mouser等可以从原来其他mcp里面扣过来" ; Mouser/DigiKey in v1, debug them; no BOM feature (model handles BOM).
- **Process**: Live-tested every endpoint. Mouser/DigiKey field quirks from kicad-happy (MIT); keyless path via pcbparts.dev `mouser_get_part`/`digikey_get_part`. jlcsearch keyword search ranks model numbers badly (STM32G030F6P6 → unrelated TVS), so jlc is C-code only. lceda `stockNumber` is in order units of `splitRatio` (C25744 4532×100 = LCSC 453200); fixed to pieces, `multiple=splitRatio`.
- **Result**: unittest 16/16 OK; `eph.py check` 6/6 OK (lceda part+search, lcsc, jlc, mouser, digikey via pcbparts). Datasheet download for C8734 verified (2.0 MB PDF from atta.szlcsc.com).
- **Notes**: pcbparts DigiKey failed with "network/connection error" for ~10 min then recovered — transient upstream. Mouser/DigiKey keyword `search` needs own keys (untested live, no keys available). lceda `productParams` is null; params come from lcsc. `wmsc.lcsc.com` search endpoint is Akamai-blocked; only detail works. Multi-part `part` call with overseas fallback takes ~13 s/part (pcbparts latency).
