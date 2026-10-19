# Architecture

## Components

- **Skill definition** — instructions and hard rules the agent follows: `skills/elec-price-hunter/SKILL.md`.
- **CLI** — `search` / `part` / `datasheet` / `check` commands, cross-source orchestration (model → C code → overseas MPN), JSON output: `skills/elec-price-hunter/scripts/eph.py`.
- **Common layer** — HTTP, canonical part record, number parsing, quantity pricing (`at_qty`), error types: `skills/elec-price-hunter/scripts/eph_sources/common.py`.
- **Source adapters** — one module per channel, each mapping its payload to the canonical record: `skills/elec-price-hunter/scripts/eph_sources/`
  - `lceda.py` — 立创商城 CNY via `pro.lceda.cn` product search (also keyword search).
  - `lcsc.py` — LCSC.com USD, parameters, datasheet, alternates (by C code).
  - `jlc.py` — JLCPCB assembly library via jlcsearch (by C code).
  - `mouser.py`, `digikey.py` — official APIs with user keys; keyless fallback through `pcbparts.py`.
  - `pcbparts.py` — client for the hosted pcbparts.dev MCP.
- **Tests** — offline parser and pricing tests with recorded payloads: `tests/test_eph.py`, `tests/fixtures/`.

## Key Relationships

`eph.py` → `eph_sources/*` → `common.py`. `mouser`/`digikey` depend on `pcbparts` only when credentials are absent.
