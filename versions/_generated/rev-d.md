# Derby Owners Club World Edition EX (Rev D)

> GENERATED FILE, do not edit. Source: `rev-d.json`. Regenerate with `python tools/render_version_doc.py rev-d`.

## Identity

| Field | Value |
|---|---|
| Region | World |
| MAME set | `derbyocw` |
| Program ROM | `epr-22336d.ic22` |
| ROM size | 4,194,304 bytes (0x400000) |
| SHA-256 | `d4ba71dcb4d3dd38ad4419053c618992fb3fd969537431e91c420811d949410e` |
| Signature @ 0x8000 | `09004ad20ee347d02b4232203388018b` |
| NAOMI build date | 2001-10-30 |
| NAOMI game code | BEF0 |
| Derived from | none (original mask ROM) |

## Confirm your ROM

Before trusting any offset below, confirm your dump matches:

```python
import zipfile, hashlib
z = zipfile.ZipFile("derbyocw.zip")
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
| Breeding mater | 60 bytes | 177 |
| Food record | 44 bytes | 45 |

## Data tables

File offsets are raw ROM positions. Runtime is where the byte lands once the cart is DMAed into RAM (file + 0x0C020000).

| Table | File offset | Runtime | Access | Verified |
|---|---|---|---|---|
| roster | 0x10a14b | 0x0c12a14b | literal-pool | yes |
| names | 0x10c098 | 0x0c12c098 | literal-pool | yes |
| sire | 0x10d264 | 0x0c12d264 | literal-pool | yes |
| dam | 0x10e614 | 0x0c12e614 | literal-pool | yes |
| g1 | 0xc65c0 | 0x0c0e65c0 | literal-pool | yes |
| tracks | 0xc6260 | 0x0c0e6260 | literal-pool | yes |
| foods | 0x16980c | 0x0c18980c | literal-pool | yes |
| strings | 0x104c75 | 0x0c124c75 | literal-pool | yes |
| racePace | not located | - | literal-pool | no |
| personality | not located | - | computed | no |

Notes:

- **roster:** CPU stat records byte-identical to Rev C; offsets shifted. (source: doc_core_roster.json; areas/horse-stats.md)
- **names:** Names/breeders differ from Rev C. (source: doc_core_roster.json)
- **sire:** 60-byte mater records. (source: build_breeding.py; areas/breeding-system.md)
- **dam:** 60-byte mater records. (source: build_breeding.py; areas/breeding-system.md)
- **g1:** 19 G1 races. (source: doc_core_tracks.json)
- **tracks:** 36 courses. (source: doc_core_tracks.json)
- **foods:** 44-byte records, 45 foods; terminator 0x169FC8. (source: doc_core_food.json)
- **strings:** First of 6 blocks (Horse Race Comments); NUL/0x0A; full block map in doc_core_strings.json. (source: doc_core_strings.json)
- **racePace:** Located in Rev C (0x10f204); not separately confirmed in Rev D. Candidate for live-ROM RE. (source: areas/race-formula.md)
- **personality:** Located in Rev C (0x0e7d20); not separately confirmed in Rev D. Candidate for live-ROM RE. (source: areas/personality-interaction.md)

## Courses

Total courses: 36. G1 races: 19.

## Player card

Type: full-stat. Marker: SEGABEF0. Payload: 207 bytes.

Full-stat US/World card; shares BEF0 game code with Rev C.

## Divergence and patch safety

Roster stat records identical to: rev-c.
Roster renamed vs World Edition baseline: no.
Food meta: beer yes, banana yes.

> Rev D changes horse/breeder NAMES, not CPU stat records. Roster stat bytes are identical to Rev C; only the name and breeding tables differ. Breeding pool grew to 177 records. A cross-version stat patch from Rev C is safe; a name patch is not.

## Appendix: shared constants

- Platform: Sega NAOMI, SH-4 (SuperH-4), little-endian, multiboard (server/master board + satellites; master runs the race sim).
- Address rule: runtime = file + 0x0C020000; file = runtime - 0x0C020000; ghidra = file + 0x0C000000.
- Baked data/code pointers in the ROM are RUNTIME values. Mixing the three frames (file, ghidra, runtime) is the top source of pointer-not-found confusion.
- Literal-pool access: A baked runtime pointer in a function constant pool. Findable by scanning the ROM for the 4-byte LE runtime address. Located roster, breeding, food, strings, and the personality-interaction reader.
- Computed access: PC-relative or base+index access (mova @(disp,PC)); no standalone pointer exists. Scans return nothing even though the table is real. The race FPU tables and the personality table are reached this way; disassemble the reader to recover index math.
- Card: 207-byte payload, 3 tracks x 69 bytes, stored reversed per track. Whole-card checksum: no.
- NVRAM (BBSRAM): stores leaderboards, track records, bookkeeping; does not store money, horses, career progress.

_Generated 2026-06-07 from `rev-d.json` and `_shared.json`._
