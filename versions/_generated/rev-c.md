# Derby Owners Club World Edition (Rev C)

> GENERATED FILE, do not edit. Source: `rev-c.json`. Regenerate with `python tools/render_version_doc.py rev-c`.

## Identity

| Field | Value |
|---|---|
| Region | World |
| MAME set | `drbyocwc` |
| Program ROM | `epr-22336c.ic22` |
| ROM size | 4,194,304 bytes (0x400000) |
| SHA-256 | `2d2e76d4f7bb498d90211410c38291e832ce7175647a5cebed1003b8d641995e` |
| Signature @ 0x8000 | `dc99020c9cc8210ce0b8210c80b6210c` |
| NAOMI build date | 2001-10-30 |
| NAOMI game code | BEF0 |
| Derived from | none (original mask ROM) |

## Confirm your ROM

Before trusting any offset below, confirm your dump matches:

```python
import zipfile, hashlib
z = zipfile.ZipFile("drbyocwc.zip")
d = next(z.read(n) for n in z.namelist()
         if n.lower().endswith(".ic22") and z.getinfo(n).file_size == 4194304)
print(hashlib.sha256(d).hexdigest())   # expect identity.sha256
print(d[0x8000:0x8010].hex())          # expect identity.signature.bytes
```

## Encoding

Names: `ascii`. Strings: `ascii`. Line separator: 0x0a.

## Record formats

| Structure | Width | Count |
|---|---|---|
| Roster record | 32 bytes | 244 |
| Name entry | stride 18 | aligns to roster index |
| Breeding mater | 60 bytes | 167 |
| Food record | 44 bytes | 45 |

## Data tables

File offsets are raw ROM positions. Runtime is where the byte lands once the cart is DMAed into RAM (file + 0x0C020000).

| Table | File offset | Runtime | Access | Verified |
|---|---|---|---|---|
| roster | 0x108e03 | 0x0c128e03 | literal-pool | yes |
| names | 0x10ad50 | 0x0c12ad50 | literal-pool | yes |
| sire | 0x10bf1c | 0x0c12bf1c | literal-pool | yes |
| dam | 0x10d2cc | 0x0c12d2cc | literal-pool | yes |
| g1 | 0xc6ca0 | 0x0c0e6ca0 | literal-pool | yes |
| tracks | 0xc6940 | 0x0c0e6940 | literal-pool | yes |
| foods | 0x166a7c | 0x0c186a7c | literal-pool | yes |
| strings | 0x104548 | 0x0c124548 | literal-pool | yes |
| racePace | 0x10f204 | 0x0c12f204 | literal-pool | yes |
| personality | 0x0e7d20 | 0x0c107d20 | computed | yes |

Notes:

- **roster:** 244 CPU racing horses, 32-byte records. (source: doc_core_roster.json; areas/horse-stats.md)
- **names:** Stride 18, ASCII; name[n] aligns to roster[n]. (source: doc_core_roster.json)
- **sire:** 60-byte mater records; 84 sires. (source: build_breeding.py; areas/breeding-system.md)
- **dam:** 60-byte mater records; 83 dams. (source: build_breeding.py; areas/breeding-system.md)
- **g1:** 19 G1 races. (source: doc_core_tracks.json)
- **tracks:** 36 courses. (source: doc_core_tracks.json)
- **foods:** 44-byte records, 45 foods; terminator 0x167238. (source: doc_core_food.json)
- **strings:** First of 26 blocks (Horse Race Comments); NUL/0x0A; full block map in doc_core_strings.json. (source: doc_core_strings.json)
- **racePace:** Distance to pace multiplier, 12 keys. (source: areas/race-formula.md; _sh4/RACE_FORMULA_FINDINGS.md)
- **personality:** 6x5 post-race bond multiplier float table; reader at runtime 0x0C027F80. (source: areas/personality-interaction.md)

## Courses

Total courses: 36. G1 races: 19.

## Player card

Type: full-stat. Marker: SEGABEF0. Payload: 207 bytes.

Full-stat US/World card. Marker code BEF0 matches NAOMI gameCode.

## Divergence and patch safety

Roster stat records identical to: none.
Roster renamed vs World Edition baseline: no.
Food meta: beer yes, banana yes.

> World Edition baseline. Rev D CPU stat records are byte-identical to this version.

## Appendix: shared constants

- Platform: Sega NAOMI, SH-4 (SuperH-4), little-endian, multiboard (server/master board + satellites; master runs the race sim).
- Address rule: runtime = file + 0x0C020000; file = runtime - 0x0C020000; ghidra = file + 0x0C000000.
- Baked data/code pointers in the ROM are RUNTIME values. Mixing the three frames (file, ghidra, runtime) is the top source of pointer-not-found confusion.
- Literal-pool access: A baked runtime pointer in a function constant pool. Findable by scanning the ROM for the 4-byte LE runtime address. Located roster, breeding, food, strings, and the personality-interaction reader.
- Computed access: PC-relative or base+index access (mova @(disp,PC)); no standalone pointer exists. Scans return nothing even though the table is real. The race FPU tables and the personality table are reached this way; disassemble the reader to recover index math.
- Card: 207-byte payload, 3 tracks x 69 bytes, stored reversed per track. Whole-card checksum: no.
- NVRAM (BBSRAM): stores leaderboards, track records, bookkeeping; does not store money, horses, career progress.

_Generated 2026-06-07 from `rev-c.json` and `_shared.json`._
