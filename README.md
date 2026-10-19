# elec-price-hunter

Agent skill for electronic component lookup: search, CNY and USD tier prices, stock, parameters and datasheets.
Main sources are LCSC China (立创商城, via JLCEDA) and LCSC international; JLCPCB, Mouser and DigiKey are also queried.

```bash
python3 skills/elec-price-hunter/scripts/eph.py part C8734 --qty 10,100,1000
python3 skills/elec-price-hunter/scripts/eph.py search "10k 0402"
python3 skills/elec-price-hunter/scripts/eph.py datasheet STM32F103C8T6 -o ./datasheets
python3 skills/elec-price-hunter/scripts/eph.py check
```

Install: link or copy `skills/elec-price-hunter/` into your agent's skills directory (e.g. `~/.claude/skills/`).

Optional credentials (without them Mouser/DigiKey part lookups go through the shared pcbparts.dev quota):
`MOUSER_SEARCH_API_KEY`, `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`.

Tests: `python3 -m unittest discover -s tests`.

The China/LCSC endpoints are undocumented and meant for low-volume interactive use.
Mouser/DigiKey field handling is adapted from [kicad-happy](https://github.com/aklofas/kicad-happy) (MIT).
