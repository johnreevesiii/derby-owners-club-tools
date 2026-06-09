# DOC ROM Version Specs

Machine-readable, byte-verified architecture specs for the four Derby Owners Club mask-ROM
versions. These are the source of truth: human-readable docs and tools are generated from them,
not the other way around.

Built so the community can take what we figured out and run with it. Save yourself the byte hunt.

## Files

| File | Purpose |
|---|---|
| `rom-spec.schema.json` | JSON Schema (draft 2020-12). The contract every version spec validates against. |
| `_shared.json` | Constants true for all versions: the address rule, pointer conventions, card and NVRAM structure. |
| `rev-c.json` | World Edition (epr-22336c, `drbyocwc`) |
| `rev-d.json` | World Edition EX (epr-22336d, `derbyocw`) |
| `doc-2000.json` | DOC 2000, JP (epr-22284a, `derbyo2k`) |
| `doc-99.json` | DOC Original '99, JP (epr-22099b, `derbyoc`) |

DOC II (`derbyoc2`) is intentionally excluded pending its own analysis. Rev R is a Rev C hack, not
a mask ROM, so it has no spec here; a hack spec would set `identity.derivedFrom` to `rev-c`.

## The one rule that prevents most mistakes: coordinate frames

Every offset declares the frame it is expressed in:

| frame | meaning | convert to file offset |
|---|---|---|
| `file` | raw byte position in the 4 MB ROM | (already a file offset) |
| `runtime` | where the byte lives once NAOMI DMAs the cart into RAM | `file = runtime - 0x0C020000` |
| `ghidra` | Ghidra static-analysis address | `file = ghidra - 0x0C000000` |

Baked pointers inside the ROM are `runtime` values. Mixing frames is the number-one reason a
pointer "isn't there." When in doubt, convert everything to `file` first.

## Trust model: `verified` and `source`

Every table entry and count carries `verified` (true only when byte-checked against that version's
ROM) and `source` (where the fact came from). `null` offset with `verified: false` means not yet
located, not "absent." Do not treat unverified fields as ground truth.

## Confirm your ROM before trusting offsets

Each spec carries the program ROM's `sha256` plus a 16-byte `signature` at `0x8000`. Check either
against your dump:

```bash
python - <<'PY'
import zipfile, hashlib
z = zipfile.ZipFile("drbyocwc.zip")
d = next(z.read(n) for n in z.namelist() if n.lower().endswith(".ic22") and z.getinfo(n).file_size == 4194304)
print("sha256   :", hashlib.sha256(d).hexdigest())
print("sig@0x8000:", d[0x8000:0x8010].hex())
PY
```

Match the printed values to `identity.sha256` and `identity.signature.bytes` in the spec. If they
do not match, the offsets in that spec do not apply to your dump.

## Cross-version patching is gated by `divergence`

`divergence.rosterIdenticalTo` tells you when one version's CPU stat records are byte-identical to
another's (Rev D to Rev C). `renamedRoster` and `foodMeta` flag where content diverges. Patching a
diverged record across versions corrupts data; gate any cross-version tool on these fields.

## Validate after editing

```bash
python tools/validate_specs.py
```

Run it after any edit. A spec that fails the schema should not ship.

## Generate the human-readable masters

```bash
python tools/render_version_doc.py            # render all four
python tools/render_version_doc.py rev-c      # render one
```

Output lands in `versions/_generated/<id>.md`, one master per version. Those files are generated:
do not edit them by hand, edit the JSON and re-render. Each master is self-contained (identity,
ROM-check snippet, record formats, data tables with file and runtime addresses, divergence, and a
shared-constants appendix), so it can be handed off on its own.

## Provenance

Offsets and signatures carried from `doc_core_versions.json`, `doc_core_roster.json`,
`doc_core_food.json`, `doc_core_tracks.json`, `doc_core_strings.json`, `build_breeding.py`, and the
byte-verified area docs in `_core/areas/`. Each spec field cites its own `source`. ROM signatures and
SHA-256 hashes re-verified against the ROMs on 2026-06-07.
Companion narrative: `../ROM_ARCHITECTURE.md`.
