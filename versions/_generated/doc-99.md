# Derby Owners Club (Original) (DOC '99)

> GENERATED FILE, do not edit. Source: `doc-99.json`. Regenerate with `python tools/render_version_doc.py doc-99`.

## Identity

| Field | Value |
|---|---|
| Region | Japan |
| MAME set | `derbyoc` |
| Program ROM | `epr-22099b.ic22` |
| ROM size | 4,194,304 bytes (0x400000) |
| SHA-256 | `f096b811a30fa2a9b947dd08133a44ddc6a3318d2b3ad95457ab5104dc524863` |
| Signature @ 0x8000 | `188bee02f15328385a482c732df33cfd` |
| NAOMI build date | 1999-10-01 |
| NAOMI game code | BAX0 |
| Derived from | none (original mask ROM) |

## Confirm your ROM

Before trusting any offset below, confirm your dump matches:

```python
import zipfile, hashlib
z = zipfile.ZipFile("derbyoc.zip")
d = next(z.read(n) for n in z.namelist()
         if n.lower().endswith(".ic22") and z.getinfo(n).file_size == 4194304)
print(hashlib.sha256(d).hexdigest())   # expect identity.sha256
print(d[0x8000:0x8010].hex())          # expect identity.signature.bytes
```

## Encoding

Names: `euc-jp`. Strings: `euc-jp`. Line separator: 0x0a.

## Record formats

| Structure | Width | Count |
|---|---|---|
| Roster record | 28 bytes | 244 |
| Name entry | stride 18 | aligns to roster index |
| Breeding mater | 56 bytes | 167 |
| Food record | 44 bytes | 41 |

## Data tables

File offsets are raw ROM positions. Runtime is where the byte lands once the cart is DMAed into RAM (file + 0x0C020000).

| Table | File offset | Runtime | Access | Verified |
|---|---|---|---|---|
| roster | 0xf6902 | 0x0c116902 | literal-pool | yes |
| names | 0xf8480 | 0x0c118480 | literal-pool | yes |
| sire | 0xf9680 | 0x0c119680 | literal-pool | yes |
| dam | not located | - | literal-pool | no |
| g1 | 0xbdad5 | 0x0c0ddad5 | literal-pool | yes |
| tracks | 0xbd875 | 0x0c0dd875 | literal-pool | yes |
| foods | 0x15c9ec | 0x0c17c9ec | literal-pool | yes |
| strings | 0xdc000 | 0x0c0fc000 | literal-pool | yes |
| racePace | not located | - | literal-pool | no |
| personality | not located | - | computed | no |

Notes:

- **roster:** 28-byte records; a different roster from the World Edition. (source: doc_core_roster.json; areas/horse-stats.md)
- **names:** EUC-JP. (source: doc_core_roster.json)
- **sire:** JP MERGED mater table (sire+dam combined), 56-byte stride, 167 records. Supersedes the registry value 0xf96cc, which did not decode cleanly. No separate dam table. (source: build_breeding.py; areas/breeding-system.md)
- **dam:** N/A: JP builds use one merged mater table (see sire); there is no separate dam table. (source: build_breeding.py)
- **g1:** 19 G1 races. (source: doc_core_tracks.json)
- **tracks:** 29 courses. (source: doc_core_tracks.json)
- **foods:** 44-byte records, 41 foods; terminator 0x15D0F8. (source: doc_core_food.json)
- **strings:** First of 7 blocks (Feeding / Difficulty Labels); EUC-JP, NUL/0x0A; full block map in doc_core_strings.json. (source: doc_core_strings.json)
- **racePace:** Not located in this version. Candidate for live-ROM RE. (source: areas/race-formula.md)
- **personality:** Not located in this version. Candidate for live-ROM RE. (source: areas/personality-interaction.md)

## Courses

Total courses: 29. G1 races: 19.

## Player card

Type: identity-only. Marker: none. Payload: see JP card spec.

JP card: identity/pedigree only, stats held cabinet-side. See _jp_re/JP_CARD_FORMAT_SPEC.md.

## Divergence and patch safety

Roster stat records identical to: none.
Roster renamed vs World Edition baseline: yes.
Food meta: beer no, banana no.

> Earliest version. Different roster entirely, 28-byte records, 56-byte merged breeding mater table (see tables.sire), 29 courses / 19 G1 / 41 foods. No beer or banana in the food meta. Cross-version patching against the World Edition is unsafe across the board.

## Appendix: shared constants

- Platform: Sega NAOMI, SH-4 (SuperH-4), little-endian, multiboard (server/master board + satellites; master runs the race sim).
- Address rule: runtime = file + 0x0C020000; file = runtime - 0x0C020000; ghidra = file + 0x0C000000.
- Baked data/code pointers in the ROM are RUNTIME values. Mixing the three frames (file, ghidra, runtime) is the top source of pointer-not-found confusion.
- Literal-pool access: A baked runtime pointer in a function constant pool. Findable by scanning the ROM for the 4-byte LE runtime address. Located roster, breeding, food, strings, and the personality-interaction reader.
- Computed access: PC-relative or base+index access (mova @(disp,PC)); no standalone pointer exists. Scans return nothing even though the table is real. The race FPU tables and the personality table are reached this way; disassemble the reader to recover index math.
- Card: 207-byte payload, 3 tracks x 69 bytes, stored reversed per track. Whole-card checksum: no.
- NVRAM (BBSRAM): stores leaderboards, track records, bookkeeping; does not store money, horses, career progress.

_Generated 2026-06-07 from `doc-99.json` and `_shared.json`._
