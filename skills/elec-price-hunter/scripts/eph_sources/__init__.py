from . import digikey, jlc, lceda, lcsc, mouser

SOURCES = {m.NAME: m for m in (lceda, lcsc, jlc, mouser, digikey)}
