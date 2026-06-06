# Derby Owners Club — ROM Architecture & How It Shapes the Game

A reference for how the DOC cart is built at the byte level, and how those structural facts ripple
into gameplay, tooling, and what's editable. Companion to `CARD_BYTE_MAP.md` (player card) and
`HIDDEN_RULES.md` (gameplay). Everything here is byte-verified unless flagged.

---

## 1. Hardware & image
- **Platform:** Sega NAOMI, **SH-4 (SuperH-4, little-endian)** CPU; DOC is a **multiboard** cabinet
  (a server/master board + satellites; the master runs the race sim).
- **Program ROM:** one 4 MB mask ROM `epr-22336*.ic22` per version (4 MB = `0x400000`).
- **Four versions**, identified by a 16-byte signature at file **`0x8000`** (and NAOMI header
  serial/date at `0x130`):
  | tag | file | sig@0x8000 (first bytes) | roster fmt |
  |---|---|---|---|
  | Rev C (World Edition) | epr-22336c | `dc99020c…` | 32-byte |
  | Rev D (WE EX) | epr-22336d | `09004ad2…` | 32-byte |
  | DOC 2000 (JP) | epr-22284a | `162f047f…` | 32-byte |
  | DOC '99 (JP) | epr-22099b | `188bee02…` | 28-byte |

## 2. The address rule that governs everything: runtime = file + 0x20000
NAOMI DMAs the cart into RAM at an offset. **A byte at file offset X executes / is pointed-to at
runtime address `X + 0x0C020000`** (proven by matching ROM code bytes into live RAM for 4 functions).
- Ghidra/static analysis loads at base `0x0C000000` (so a Ghidra address = file + 0x0C000000).
- **Baked data/code pointers in the ROM are RUNTIME values** (file + 0x0C020000). To read a baked
  pointer's target from the ROM file: `file = pointer − 0x0C020000`.
- Three coordinate frames in play — file, Ghidra-static (+0x0C000000), runtime (+0x0C020000) — and
  mixing them is the #1 source of "the pointer isn't there" confusion.

## 3. Pointer-table conventions & the "no pointer" wall
Two ways the ROM reaches its tables, and the second is why some mechanics were hard to find:
1. **Literal-pool pointers** — a baked runtime pointer in a function's constant pool. Findable by
   scanning the ROM for the 4-byte LE runtime address (this is how we located roster, breeding,
   food, string, and the personality-interaction reader).
2. **Computed / PC-relative (`mova`) access** — the table address is *computed* (base register +
   index, or `mova @(disp,PC)`), with **no standalone pointer anywhere**. Scans for a pointer return
   nothing even though the table is real. The race FPU tables and the personality table are reached
   this way; you must disassemble the *reader* to recover the index math.
- **Gameplay consequence:** the parts of the game that resisted RE the longest (the stat→speed
  curve, the personality multiplier indexing) are exactly the computed-access ones — which is why
  community knowledge of them stayed fuzzy.

## 4. The data tables (per-version offsets in the area docs)
| table | what | layout |
|---|---|---|
| **CPU roster** | 244 racing horses | 32-byte (Rev C/D/2000) or 28-byte ('99) records; field map in `areas/horse-stats.md` |
| **Name table** | horse names | stride 18, ASCII (EN) / EUC-JP (JP), `name[n]` aligns to `stat[n]` |
| **Breeding pool** | 167/177 sire+dam "mater" records | 60-byte (EN) / 56-byte ('99); one contiguous block, reconcile by NAME not index |
| **Food table** | 45/41 foods | 44-byte records: name + 7 effect columns (Speed/Stamina/Sharp confirmed) + class/rarity flags |
| **String blocks** | dialogue/menu/names | NUL-packed; EN uses `0x0A` as a line separator; JP is EUC-JP |
| **Race tables** | distance→pace multiplier (12 keys @ `0x10F204`), dirt 4-band curve, condition gates, FPU coeff pools | mix of literal-pool and computed access |
| **Personality interaction** | post-race bond multipliers | 6×5 float table @ `0x0E7D20`, computed access (reader @ `0x0C027F80`) |
| **NVRAM (BBSRAM)** | leaderboards, track records, bookkeeping | two redundant 0x13c4-strided regions + LE16 checksums; **no money/horses/career stored** |

## 5. Version divergence — why "the best version" is a real question
- **Rev C and Rev D rosters are byte-identical** (Rev D changes names/breeders, not CPU stats).
- **Rev C vs DOC 2000:** ~a dozen CPU racing records differ (a genuine stat rebalance), plus the
  whole JP roster is renamed.
- **DOC '99:** a *different* roster entirely, 28-byte records, 29 courses / 19 G1 / 41 foods.
- **Gameplay consequence:** opponent difficulty, the food meta (no beer/banana on '99), and the
  track/G1 calendar are version-dependent. A cross-version ROM patch is **unsafe** for the diverged
  records — tools must gate on the divergence map.

## 6. The card layers (see CARD_BYTE_MAP.md for the field map)
- A horse lives on a **207-byte `.card`** payload: 3 tracks × 69, **stored reversed per track**.
- **No whole-card checksum** in the payload → freely editable (and silently mis-editable).
- US/World cards are **full-stat** (`SEGABEF0` marker); JP cards are **identity/pedigree only** —
  stats are held cabinet-side, which is why JP card *creation* needs the cabinet's lead-id/trailer
  recipe (still open).

## 7. Emulation / RE notes (for tool builders)
- The GDB-stub Flycast rig runs with **Dynarec ON**, so **software breakpoints don't fire** (the JIT
  executes recompiled blocks); memory reads/writes work fine. Interpreter mode is needed for code
  breakpoints.
- The cart's live RAM base means structs move per boot; locate by scanning, not hard-coded address.

*Provenance:* version sigs (`doc_core_versions.json`); runtime base (ROM-byte→RAM match, `_sh4`);
table layouts (`areas/*.md`, byte-verified); personality reader (`areas/personality-interaction.md`);
dynarec/rig (`memory/DOC_RACE_FORMULA_SH4.md`).
