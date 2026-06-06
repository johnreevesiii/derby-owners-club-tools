#!/usr/bin/env python3
"""doc-core: canonical CPU-roster extractor for Derby Owners Club.

Reads the 244-horse stat table + name table straight from each program ROM and emits one
canonical JSON (all 4 versions, every decoded field). Source of truth = the binary.
Self-verifies the contested coat offset against the real bytes.

Name tables (stride 18, id-ordered, parallel to the stat table within each version):
  drbyocwc 0x10AD50 ASCII | derbyocw 0x10C098 ASCII | derbyo2k 0x10CC68 EUC-JP | derbyoc 0xF8480 EUC-JP
  (JP offsets confirmed by the 'DOC Rom Data Bookmarks' tab + the アイオー signature; stride 18 verified.)

Field map (record-start relative), per _core/areas/horse-stats.md (SOLID, 244/244), coat re-verified here:
  32-byte: hiddenA+1 id+2 dirt+5 grade+8 start+9..spurt+14 hiddenB+16 style+21 coat+22 hX+23/24 stam/spd/shp+29/30/31
  28-byte: hiddenA+0 id+1 dirt+4 grade+7 start+9..spurt+14 hiddenB+17 style+18 coat+19 hX+20/21 stam/spd/shp+24/25/26
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ONE = r"C:/Users/johnr/OneDrive - Indigenous Healthcare Advancements/Desktop/John and Pui/Derby Owners Club/DOC-Naomi Roms/Roms"
OUT = r"C:/DerbyOwnersClub/doc-core"

VERSIONS = {
    "drbyocwc": {"label": "World Edition (Rev C)",   "tag": "Rev C",    "rom": f"{ONE}/drbyocwc/epr-22336c.ic22", "fmt": 32, "rec": 0x108E03, "names": 0x10AD50, "enc": "ascii"},
    "derbyocw": {"label": "World Edition EX (Rev D)", "tag": "Rev D",    "rom": f"{ONE}/derbyocw/epr-22336d.ic22", "fmt": 32, "rec": 0x10A14B, "names": 0x10C098, "enc": "ascii"},
    "derbyo2k": {"label": "DOC 2000 (JP)",            "tag": "DOC 2000", "rom": f"{ONE}/derbyo2k/epr-22284a.ic22", "fmt": 32, "rec": 0x10AD1B, "names": 0x10CC68, "enc": "euc-jp"},
    "derbyoc":  {"label": "DOC Original / '99 (JP)",  "tag": "DOC '99",  "rom": f"{ONE}/derbyoc/epr-22099b.ic22",  "fmt": 28, "rec": 0x0F6902, "names": 0xF8480,  "enc": "euc-jp"},
}
COUNT, NAME_STRIDE = 244, 18
COAT  = {0: "Default", 192: "Chestnut", 193: "Black", 199: "Brown", 202: "Bay", 204: "Dark Gray", 207: "Light Gray", 222: "Special"}
GRADE = {0: "Ungraded", 1: "G3", 2: "G2", 3: "G1"}
STYLE = {0: "Front-runner", 1: "Start dash", 2: "Last spurt", 3: "Stretch-runner", 7: "Almighty"}
FIELDS = {
    32: dict(hiddenA=1, id=2, dirt=5, grade=8, start=9, corner=10, oob=11, comp=12, tenac=13, spurt=14, hiddenB=16, style=21, coat=22, hxLo=23, hxHi=24, idEcho=25, stam=29, speed=30, sharp=31),
    28: dict(hiddenA=0, id=1, dirt=4, grade=7, start=9, corner=10, oob=11, comp=12, tenac=13, spurt=14, hiddenB=17, style=18, coat=19, hxLo=20, hxHi=21, idEcho=22, stam=24, speed=25, sharp=26),
}

# compact katakana -> romaji (reading aid)
_KR = {'ア':'a','イ':'i','ウ':'u','エ':'e','オ':'o','カ':'ka','キ':'ki','ク':'ku','ケ':'ke','コ':'ko','サ':'sa','シ':'shi','ス':'su','セ':'se','ソ':'so','タ':'ta','チ':'chi','ツ':'tsu','テ':'te','ト':'to','ナ':'na','ニ':'ni','ヌ':'nu','ネ':'ne','ノ':'no','ハ':'ha','ヒ':'hi','フ':'fu','ヘ':'he','ホ':'ho','マ':'ma','ミ':'mi','ム':'mu','メ':'me','モ':'mo','ヤ':'ya','ユ':'yu','ヨ':'yo','ラ':'ra','リ':'ri','ル':'ru','レ':'re','ロ':'ro','ワ':'wa','ヲ':'wo','ン':'n','ガ':'ga','ギ':'gi','グ':'gu','ゲ':'ge','ゴ':'go','ザ':'za','ジ':'ji','ズ':'zu','ゼ':'ze','ゾ':'zo','ダ':'da','ヂ':'ji','ヅ':'zu','デ':'de','ド':'do','バ':'ba','ビ':'bi','ブ':'bu','ベ':'be','ボ':'bo','パ':'pa','ピ':'pi','プ':'pu','ペ':'pe','ポ':'po','ヴ':'vu'}
_SM = {'ァ':'a','ィ':'i','ゥ':'u','ェ':'e','ォ':'o','ャ':'ya','ュ':'yu','ョ':'yo'}
def romaji(s):
    out, prev = "", ""
    arr = list(s)
    for i, ch in enumerate(arr):
        if ch == 'ー': out += prev or "-"; continue
        if ch == 'ッ':
            nx = _KR.get(arr[i+1]) if i+1 < len(arr) else None
            if nx: out += nx[0]
            continue
        if ch in _SM:
            sm = _SM[ch]
            if ch in 'ャュョ': out = out[:-1] if out and out[-1] == 'i' else out
            elif out and out[-1] in 'aiueo': out = out[:-1]
            out += sm; prev = sm[-1]; continue
        b = _KR.get(ch)
        if b: out += b; prev = b[-1]
        else: out += ch; prev = ""
    return out

def read_name(buf, base, idx, enc):
    if base is None: return None
    slot = buf[base + NAME_STRIDE * idx: base + NAME_STRIDE * idx + NAME_STRIDE]
    raw = slot.split(b'\x00')[0]
    if enc == "ascii":
        return bytes(b & 0x7f for b in raw).decode("ascii", "replace").strip() or None
    try: return raw.decode("euc-jp")
    except Exception: return raw.decode("euc-jp", "replace")

def extract(cfg):
    buf = open(cfg["rom"], "rb").read()
    F = FIELDS[cfg["fmt"]]
    out = []
    for n in range(COUNT):
        r = cfg["rec"] + cfg["fmt"] * n
        g = lambda f: buf[r + F[f]]
        nm = read_name(buf, cfg["names"], n, cfg["enc"])
        jp = cfg["enc"] == "euc-jp"
        out.append({
            "id": g("id"),
            "name": None if jp else nm,
            "nameJP": nm if jp else None,
            "romaji": romaji(nm) if (jp and nm) else None,
            "grade": GRADE.get(g("grade"), g("grade")), "dirt": g("dirt"),
            "externals": {"start": g("start"), "corner": g("corner"), "oob": g("oob"), "competing": g("comp"), "tenacious": g("tenac"), "spurt": g("spurt")},
            "internals": {"stamina": g("stam"), "speed": g("speed"), "sharp": g("sharp")},
            "extTotal": sum(g(f) for f in ("start", "corner", "oob", "comp", "tenac", "spurt")),
            "style": STYLE.get(g("style"), g("style")), "coat": COAT.get(g("coat"), f"0x{g('coat'):02x}"),
            "hidden": {"A": g("hiddenA"), "B": g("hiddenB"), "X": g("hxLo") | (g("hxHi") << 8)},
        })
    return buf, out

def verify_coat(buf, cfg):
    F = FIELDS[cfg["fmt"]]
    return {cand: sum(1 for n in range(COUNT) if buf[cfg["rec"] + cfg["fmt"] * n + cand] in COAT) for cand in (F["coat"], 13)}

def main():
    os.makedirs(OUT, exist_ok=True)
    data = {"_about": "doc-core canonical CPU roster, byte-exact from the program ROMs; name[n] aligns with stat[n] within each version", "versions": {}, "coatOffsetVerification": {}}
    print("=== doc-core roster extraction ===")
    for key, cfg in VERSIONS.items():
        buf, horses = extract(cfg)
        data["coatOffsetVerification"][key] = verify_coat(buf, cfg)
        data["versions"][key] = {"label": cfg["label"], "tag": cfg["tag"], "recordFmt": cfg["fmt"], "recordStart": hex(cfg["rec"]), "nameTable": hex(cfg["names"]), "nameEnc": cfg["enc"], "count": len(horses), "horses": horses}
        h1 = horses[0]
        disp = h1["name"] or f"{h1['nameJP']} ({h1['romaji']})"
        print(f"  {key:9} {cfg['tag']:9} #1 = {disp} | grade={h1['grade']} ext={list(h1['externals'].values())} style={h1['style']} coat={h1['coat']}")
    path = f"{OUT}/doc_core_roster.json"
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote {path} ({os.path.getsize(path):,} bytes)")
    print("coat offset verdict:", {k: f"+{max(v,key=v.get)} ({max(v.values())}/244)" for k, v in data["coatOffsetVerification"].items()})

if __name__ == "__main__":
    main()
