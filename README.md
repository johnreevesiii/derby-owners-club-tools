# DOC Tools Suite — engine & card codec

Open-source code behind the **Derby Owners Club Tools Suite**: a set of browser tools for the Sega
NAOMI arcade game *Derby Owners Club*, built on a byte-exact reverse-engineering of the game ROMs.

**▶ Live tools (run in your browser, nothing to install):** https://doc.johnreevesiii.com/tools/
**📖 Game mechanics & card byte map (community wiki):** *(link TBD)*

## What's in here
- `build_*.py` — generators that render each tool (race simulator + odds, foal predictor, feeding
  advisor, roster/opponent browser, breeding, tracks, version diff, card differ, ROM studio, string
  tool, NVRAM dashboard, fingerprinter, personality/bond advisor, …) into self-contained HTML.
- `doc_card.py` — the canonical 207-byte **`.card` codec** (US + JP), byte-exact round-trip
  (`decode` / `encode` / `info` / `selftest`). Useful on its own for anyone working with DOC cards.
- `ROM_ARCHITECTURE.md` — how the cart is laid out (memory map, the runtime offset, pointer-table
  conventions, record formats, version divergence) — the methodology the generators rely on.

## What's intentionally NOT here (and why)
- **No game data.** The `doc_core_*.json` files the generators read (horse names, in-game text,
  rosters) are derived from Sega's copyrighted ROMs and are **not** distributed. Bring your own
  ROM-derived data to build the data-driven tools.
- **No ROMs, no built HTML with embedded game text, no game executables.** *Derby Owners Club* is
  Sega's. This repo is the original tooling/code only. (See why the game itself isn't on GitHub:
  https://doc.johnreevesiii.com/why.html)

## Using the card codec (no game data needed)
```
python doc_card.py info  yourhorse.card     # human-readable summary
python doc_card.py decode yourhorse.card    # JSON
python doc_card.py encode yourhorse.json    # byte-exact .card
python doc_card.py selftest                 # round-trip checks
```

## Building the tools
Each `python build_<tool>.py` reads the (not-included) `doc_core_*.json` data and writes a
self-contained `<tool>.html`. Validate with any JS parser; everything is offline, no runtime deps
except `tailwind.js` for the card editor.

## Why trust it
Every field/constant was verified against the real ROMs/cards (the codec's `selftest` round-trips
real cards byte-for-byte). Where a value is approximate or inferred it is flagged as such.

## Contributing
Issues and PRs welcome — tool UX, new views over the data, codec coverage, methodology corrections.

## License
MIT — see `LICENSE`. The game and its data are not covered by this license and are not included.
