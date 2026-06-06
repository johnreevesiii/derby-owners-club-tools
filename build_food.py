#!/usr/bin/env python3
"""doc-core: canonical Food / Feed table extractor for Derby Owners Club.

Reads the packed food-record array straight from each program ROM and emits one canonical
JSON (all 4 versions, every decoded field + names). Source of truth = the binary.
Self-verifies the table geometry (start / stride / count / terminator) and the documented
beer-effect byte change against the real bytes; prints PASS/FAIL.

Food table geometry (BYTE-VERIFIED against the ROMs, _core/areas/items-feeding.md confirmed):
  drbyocwc 0x166A7C  45 foods  ascii   | derbyocw 0x16980C  45 foods  ascii
  derbyo2k 0x171F34  45 foods  euc-jp  | derbyoc  0x15C9EC  41 foods  euc-jp
  44-byte records in ALL FOUR versions. Terminator = all-zero record, idx=0.

Record layout (record-start relative, 44 bytes) — verified:
  +0  [24] name (ascii null-pad on EN / EUC-JP null-pad on JP)
  +24 u32 LE  graphic pointer (RAM addr ~0x0D8xxxxx)
  +28 [7]     effect deltas cols 0..6  (col0 Speed, col1 Stamina, col2 Sharp, cols3-6 secondary)
  +35 [1]     effect-class flag (0x01 normal feed / 0x00 growth-only class)
  +36 [1]     rarity/size flag (0x00 small-common / 0x01 large-special)
  +37 [1]     reserved (always 0x00)
  +38 [2]     reserved (always 0x0000)
  +40 u32 LE  food index/id (1..39 real; trailing dupes reuse 39 or 1; terminator=0)

Beer (DOC 2000 / WE only; '99 has no beer): two trailing records DRAFT BEER + BLACK DRAFT BEER,
shipped with all-zero effects. The documented "Enable Beer" patch writes +2/+4 to the first six
effect columns (KOREAN-GINSENG template). For drbyocwc that is the 12-byte change at 0x1671FC
(DRAFT +28..33) and 0x167228 (BLACK +28..33), proven by Beer-Experiment/beer_effects_test.ic22.
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ONE = r"C:/Users/johnr/OneDrive - Indigenous Healthcare Advancements/Desktop/John and Pui/Derby Owners Club/DOC-Naomi Roms/Roms"
OUT = r"C:/DerbyOwnersClub/doc-core"
BEER_TEST = r"C:/DerbyOwnersClub/Beer-Experiment/beer_effects_test.ic22"

REC = 44
NAME_W = 24
EFF_OFF = 28      # cols 0..6 (7 bytes), then +35 class flag
CLASS_OFF = 35
RARITY_OFF = 36
INDEX_OFF = 40
ROM_SIZE = 4194304

# 7 effect columns. Cols 0/1/2 = Speed/Stamina/Sharp (SOLID). Cols 3-6 secondary growth (names tentative).
EFFECT_COLS = ["Speed", "Stamina", "Sharp", "col3 (Spirit?)", "col4 (Power?)", "col5", "col6"]

VERSIONS = {
    "drbyocwc": {"label": "World Edition (Rev C)",    "tag": "Rev C",    "rom": f"{ONE}/drbyocwc/epr-22336c.ic22", "table": 0x166A7C, "enc": "ascii",  "hasBeer": True},
    "derbyocw": {"label": "World Edition EX (Rev D)",  "tag": "Rev D",    "rom": f"{ONE}/derbyocw/epr-22336d.ic22", "table": 0x16980C, "enc": "ascii",  "hasBeer": True},
    "derbyo2k": {"label": "DOC 2000 (JP)",             "tag": "DOC 2000", "rom": f"{ONE}/derbyo2k/epr-22284a.ic22", "table": 0x171F34, "enc": "euc-jp", "hasBeer": True},
    "derbyoc":  {"label": "DOC Original / '99 (JP)",    "tag": "DOC '99",  "rom": f"{ONE}/derbyoc/epr-22099b.ic22",  "table": 0x15C9EC, "enc": "euc-jp", "hasBeer": False},
}

def decode_name(raw, enc):
    raw = raw.split(b"\x00")[0]
    if enc == "ascii":
        return bytes(b & 0x7f for b in raw).decode("ascii", "replace").strip()
    try: return raw.decode("euc-jp")
    except Exception: return raw.decode("euc-jp", "replace")

def extract(cfg):
    buf = open(cfg["rom"], "rb").read()
    base, enc = cfg["table"], cfg["enc"]
    foods, n, term = [], 0, None
    while True:
        r = base + REC * n
        rec = buf[r:r + REC]
        if len(rec) < REC: break
        name = decode_name(rec[0:NAME_W], enc)
        idx = int.from_bytes(rec[INDEX_OFF:INDEX_OFF + 4], "little")
        if idx == 0 and name == "":
            term = r
            break
        eff = list(rec[EFF_OFF:EFF_OFF + 7])
        foods.append({
            "slot": n,
            "recOffset": r,
            "recOffsetHex": f"0x{r:06X}",
            "index": idx,
            "name": name,
            "graphicPtr": f"0x{int.from_bytes(rec[24:28],'little'):08x}",
            "effect": eff,                                   # 7 cols
            "effectHex": rec[EFF_OFF:EFF_OFF + 7].hex(),
            "classFlag": rec[CLASS_OFF],                     # +35 0x01 feed / 0x00 growth
            "rarityFlag": rec[RARITY_OFF],                   # +36 0x00 small / 0x01 large
            "isBeer": name.upper() in ("DRAFT BEER", "BLACK DRAFT BEER") or name in ("生中", "黒生中"),
            "effectFieldOffset": r + EFF_OFF,                # absolute offset of col0 (patch target)
            "effectFieldOffsetHex": f"0x{r + EFF_OFF:06X}",
        })
        n += 1
        if n > 64:
            break
    beers = [f for f in foods if f["isBeer"]]
    return buf, foods, term, beers

def main():
    os.makedirs(OUT, exist_ok=True)
    data = {
        "_about": ("doc-core canonical Food/Feed table, byte-exact from the program ROMs. "
                   "44-byte records, terminator = all-zero idx=0 record. Effect cols 0/1/2 = "
                   "Speed/Stamina/Sharp (verified); cols 3-6 secondary growth stats (tentative). "
                   "Beer is a disabled all-zero placeholder in DOC 2000 + WE; DOC '99 has no beer."),
        "recordSize": REC,
        "layout": {
            "name": "+0..23", "graphicPtr": "+24 u32LE", "effect": "+28..34 (cols 0-6)",
            "classFlag": "+35 (0x01 feed / 0x00 growth)", "rarityFlag": "+36 (0x00 small / 0x01 large)",
            "reserved": "+37..39", "index": "+40 u32LE (1..39; terminator 0)",
        },
        "effectColumns": EFFECT_COLS,
        "romSize": ROM_SIZE,
        "versions": {},
        "verification": {},
    }
    print("=== doc-core food extraction ===")
    all_pass = True
    for key, cfg in VERSIONS.items():
        buf, foods, term, beers = extract(cfg)
        data["versions"][key] = {
            "label": cfg["label"], "tag": cfg["tag"], "table": hex(cfg["table"]),
            "nameEnc": cfg["enc"], "count": len(foods),
            "terminator": (f"0x{term:06X}" if term is not None else None),
            "hasBeer": cfg["hasBeer"],
            "beerRecords": [{"name": b["name"], "recOffsetHex": b["recOffsetHex"],
                             "effectFieldOffsetHex": b["effectFieldOffsetHex"], "index": b["index"]} for b in beers],
            "foods": foods,
        }
        f1 = foods[0]
        print(f"  {key:9} {cfg['tag']:9} table={hex(cfg['table'])} count={len(foods):2d} "
              f"#1='{f1['name']}' eff={f1['effectHex']} beers={len(beers)}")

    # ---- self-verification ----
    # (a) geometry: counts + terminators
    geom_ok = (data["versions"]["drbyocwc"]["count"] == 45 and data["versions"]["derbyocw"]["count"] == 45
               and data["versions"]["derbyo2k"]["count"] == 45 and data["versions"]["derbyoc"]["count"] == 41)
    # (b) known value: CARROT (slot 0) Speed+2, hex 0200000000000001-ish (eff cols+class)
    carrot = data["versions"]["drbyocwc"]["foods"][0]
    carrot_ok = carrot["name"] == "CARROT" and carrot["effect"][0] == 2 and sum(carrot["effect"][1:]) == 0
    # (c) KOREAN GINSENG +2 all six (the beer template)
    kg = next(f for f in data["versions"]["drbyocwc"]["foods"] if f["name"] == "KOREAN GINSENG")
    kg_ok = kg["effect"][:6] == [2, 2, 2, 2, 2, 2]
    # (d) beer placeholder is all-zero in WE/2K
    beer_zero_ok = all(b["index"] >= 0 for b in [])  # placeholder; check below
    we_beers = data["versions"]["drbyocwc"]["foods"]
    draft = next(f for f in we_beers if f["name"] == "DRAFT BEER")
    black = next(f for f in we_beers if f["name"] == "BLACK DRAFT BEER")
    beer_zero_ok = sum(draft["effect"]) == 0 and sum(black["effect"]) == 0
    # (e) beer-edit patch: applying +2 to DRAFT col0..5 and +4 to BLACK col0..5 of base drbyocwc
    #     must reproduce beer_effects_test.ic22 byte-exact (12 bytes change @ draft+28 and black+28).
    patch_ok = None
    diff_runs = None
    if os.path.exists(BEER_TEST):
        base = buf if key == "drbyocwc" else open(VERSIONS["drbyocwc"]["rom"], "rb").read()
        base = open(VERSIONS["drbyocwc"]["rom"], "rb").read()
        test = open(BEER_TEST, "rb").read()
        patched = bytearray(base)
        for i in range(6):
            patched[draft["effectFieldOffset"] + i] = 2
            patched[black["effectFieldOffset"] + i] = 4
        diffs = [i for i in range(min(len(base), len(test))) if base[i] != test[i]]
        runs = []
        for i in diffs:
            if runs and i == runs[-1][1] + 1: runs[-1][1] = i
            else: runs.append([i, i])
        diff_runs = [{"start": f"0x{s:06X}", "end": f"0x{e:06X}", "len": e - s + 1} for s, e in runs]
        patch_ok = (bytes(patched) == test) and len(diffs) == 12 and len(patched) == ROM_SIZE

    data["verification"] = {
        "geometryCountsOK": geom_ok,
        "carrotKnownValueOK": carrot_ok,
        "koreanGinsengTemplateOK": kg_ok,
        "beerPlaceholderAllZeroOK": beer_zero_ok,
        "beerPatchReproducesTestROM": patch_ok,
        "beerExperimentDiffRuns": diff_runs,
        "beerEditDeltas": {"DRAFT BEER": "+2 to cols 0-5", "BLACK DRAFT BEER": "+4 to cols 0-5"},
    }

    path = f"{OUT}/doc_core_food.json"
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote {path} ({os.path.getsize(path):,} bytes)")

    checks = [
        ("geometry counts 45/45/45/41", geom_ok),
        ("CARROT slot0 = Speed+2", carrot_ok),
        ("KOREAN GINSENG = +2 all six", kg_ok),
        ("beer placeholder all-zero (WE)", beer_zero_ok),
        ("beer patch reproduces beer_effects_test.ic22 (12 bytes)", patch_ok if patch_ok is not None else "SKIP (test rom missing)"),
    ]
    print("\n--- self-verification ---")
    for label, ok in checks:
        if ok == "SKIP (test rom missing)":
            print(f"  SKIP {label}")
        else:
            print(f"  {'PASS' if ok else 'FAIL'} {label}")
            if not ok: all_pass = False
    if diff_runs:
        print(f"  beer diff runs: {diff_runs}")
    print("\nVERDICT:", "PASS" if all_pass else "FAIL")

if __name__ == "__main__":
    main()
