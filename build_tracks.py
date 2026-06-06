#!/usr/bin/env python3
"""doc-core: tracks / courses / G1-calendar extractor for Derby Owners Club.

Reads the on-screen DISPLAY string tables (course list, course display names, special &
handicap race labels, and the G1 race-name list) straight from each program ROM and emits
one canonical JSON (all 4 versions). Source of truth = the binary; every offset below was
verified against the real .ic22 bytes (see VERIFIED notes) before being trusted.

These tables are null-terminated DISPLAY strings, NOT packed binary race records: surface
(TURF/DIRT) and distance (e.g. 1600M) live inside the string text itself. The English
(WE Rev C/D) tables are ASCII; the Japanese ('99, 2000) tables are EUC-JP with inline
format-control bytes (0x0f / 0xff 0x0f / f0 8b f0 / ff ee fb ...) between/before strings.
We strip those controls and decode EUC-JP, anchoring on the known first-char of each row.

VERIFIED THIS BUILD (corrections to _core/areas/tracks-races.md noted with [FIX]):
  Rev C (drbyocwc): course 0x0C6940 = 36, G1 0x0C6CA0 = 20 strings (19 races + NO NAME),
                    display 0x0C6DF0 = 26, special 0x0C70C8 = 12, handicap 0x0C7248 = 12.   [doc correct]
  Rev D (derbyocw): uniform -0x6E0 shift; readable strings byte-identical to Rev C (only the
                    inline control bytes differ, e.g. 0f ff 0f vs f0 8b f0).                 [doc correct]
  DOC 2000 (derbyo2k): course 0x0CA335 = 36, G1 0x0CA62D = 21, display 0x0CA7AB = 36,
                       special 0x0CAB0B = 12, handicap 0x0CAC5B = 12.                          [doc correct]
  DOC '99 (derbyoc):  course 0x0BD875 = 29  [FIX: doc said 30 -> real bytes = 29],
                      G1 0x0BDAD5 = 19       [FIX: doc said 20 -> real bytes = 19; doc's own
                                              "21 minus 高松宮記念 + ジャパンカップダート" = 19 too],
                      display 0x0BDC2D, special 0x0BDEE7 = 10, NO handicap table.             [10/none correct]
Self-verifies a known value per version and prints PASS/FAIL.
"""
import json, os, re, sys
from collections import Counter
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ONE = r"C:/Users/johnr/OneDrive - Indigenous Healthcare Advancements/Desktop/John and Pui/Derby Owners Club/DOC-Naomi Roms/Roms"
OUT = r"C:/DerbyOwnersClub/doc-core"

# Section boundaries are [start, end). Verified against real bytes (see header).
VERSIONS = {
    "drbyocwc": {
        "label": "World Edition (Rev C)", "tag": "Rev C", "rom": f"{ONE}/drbyocwc/epr-22336c.ic22",
        "enc": "ascii", "sig": "dc99020c9cc8210c",
        "sections": {
            "course":   (0x0C6940, 0x0C6CA0), "g1":       (0x0C6CA0, 0x0C6DF0),
            "display":  (0x0C6DF0, 0x0C70C8), "special":  (0x0C70C8, 0x0C7248),
            "handicap": (0x0C7248, 0x0C73C8),
        },
        "verify": ("course", 0, "EASTERN CITY TURF 1600M"),
    },
    "derbyocw": {
        "label": "World Edition EX (Rev D)", "tag": "Rev D", "rom": f"{ONE}/derbyocw/epr-22336d.ic22",
        "enc": "ascii", "sig": "09004ad20ee347d0",
        "sections": {  # Rev C offsets minus 0x6E0
            "course":   (0x0C6940 - 0x6E0, 0x0C6CA0 - 0x6E0), "g1":       (0x0C6CA0 - 0x6E0, 0x0C6DF0 - 0x6E0),
            "display":  (0x0C6DF0 - 0x6E0, 0x0C70C8 - 0x6E0), "special":  (0x0C70C8 - 0x6E0, 0x0C7248 - 0x6E0),
            "handicap": (0x0C7248 - 0x6E0, 0x0C73C8 - 0x6E0),
        },
        "verify": ("g1", 0, "WINTER STAKES"),
    },
    "derbyo2k": {
        "label": "DOC 2000 (JP)", "tag": "DOC 2000", "rom": f"{ONE}/derbyo2k/epr-22284a.ic22",
        "enc": "euc-jp", "sig": "162f047ffcf5fcf6",
        "sections": {
            "course":   (0x0CA335, 0x0CA62D), "g1":       (0x0CA62D, 0x0CA7AB),
            "display":  (0x0CA7AB, 0x0CAB0B), "special":  (0x0CAB0B, 0x0CAC5B),
            "handicap": (0x0CAC5B, 0x0CAD7B),
        },
        "verify": ("course", 0, "東京芝１６００Ｍ"),
    },
    "derbyoc": {
        "label": "DOC Original / '99 (JP)", "tag": "DOC '99", "rom": f"{ONE}/derbyoc/epr-22099b.ic22",
        "enc": "euc-jp", "sig": "188bee02f1532838",
        "sections": {  # no handicap table in '99
            "course":   (0x0BD875, 0x0BDAD5), "g1":       (0x0BDAD5, 0x0BDC2D),
            "display":  (0x0BDC2D, 0x0BDEE7), "special":  (0x0BDEE7, 0x0BE00E),
        },
        "verify": ("g1", 18, "ダービーオーナーズカップ"),
    },
}

# Anchor first-chars so the EUC control-strip lands on the real text (JP only).
VENUE_FIRST = set("東阪中京セ")                 # course / display / special / handicap rows
G1_FIRST    = set("フ桜皐天Ｎオ日安宝ス秋菊エマジ有ダ高")  # G1 race names

# EN <-> JP venue localization map (Section 4, verified by 1:1 positional course alignment).
VENUE_MAP = [
    {"en": "EASTERN CITY",  "jp": "東京",   "reading": "Tokyo",    "realTrack": "Tokyo Racecourse"},
    {"en": "WESTERN HILL",  "jp": "阪神",   "reading": "Hanshin",  "realTrack": "Hanshin"},
    {"en": "NORTHERN PARK", "jp": "中山",   "reading": "Nakayama", "realTrack": "Nakayama"},
    {"en": "CENTRAL CITY",  "jp": "京都",   "reading": "Kyoto",    "realTrack": "Kyoto"},
    {"en": "SEGA",          "jp": "セガ",   "reading": "Sega",     "realTrack": "(fictional Sega track)"},
    {"en": "SOUTHERN PARK", "jp": "中京",   "reading": "Chukyo",   "realTrack": "Chukyo"},
]
JP_VENUES = {v["jp"]: v for v in VENUE_MAP}
EN_VENUES = sorted({v["en"] for v in VENUE_MAP}, key=len, reverse=True)

# ---- string-table walkers ----------------------------------------------------
def split_null_chunks(buf, start, end):
    """Yield (offset, raw_bytes) for each run of non-null bytes in [start,end)."""
    i = start
    while i < end:
        while i < end and buf[i] == 0: i += 1
        if i >= end: break
        j = i
        while j < end and buf[j] != 0: j += 1
        yield i, buf[i:j]
        i = j

def parse_ascii(buf, start, end):
    """WE (ASCII): each chunk is a printable run; strip control bytes (<0x20, >=0x7f)."""
    out = []
    for off, ch in split_null_chunks(buf, start, end):
        s = bytes(b for b in ch if 0x20 <= b < 0x7f).decode("ascii", "replace").rstrip()
        if s:
            out.append({"offset": hex(off), "text": s})
    return out

def decode_euc_anchored(ch, first_set):
    """EUC-JP chunk preceded by 1-3 inline control bytes. Try skip offsets 0..6 and pick the
    decode whose first char is in first_set (else fewest U+FFFD, then smallest skip)."""
    best = None
    for skip in range(7):
        body = ch[skip:]
        try: s = body.decode("euc-jp")
        except Exception: continue
        if not s: continue
        good = 0 if s[0] in first_set else 1
        score = (good, s.count("�"), skip)
        if best is None or score < best[0]:
            best = (score, s)
    return best[1] if best else ch.decode("euc-jp", "replace")

def parse_euc(buf, start, end, first_set):
    out = []
    for off, ch in split_null_chunks(buf, start, end):
        s = decode_euc_anchored(ch, first_set)
        # drop boundary junk: empty, or a single non-text replacement glyph
        if not s.strip() or (len(s) == 1 and s == "�"):
            continue
        out.append({"offset": hex(off), "text": s})
    return out

# ---- attribute parsing (surface + distance out of the display text) ----------
def surface_distance(text, enc):
    """Pull TURF/DIRT + distance (metres) out of a course/display string where parseable."""
    surface = dist = venue = None
    if enc == "ascii":
        up = text.upper()
        if "TURF" in up: surface = "TURF"
        elif "DIRT" in up: surface = "DIRT"
        m = re.search(r"(\d{3,4})\s*M\b", up)
        if m: dist = int(m.group(1))
        for v in EN_VENUES:
            if up.startswith(v): venue = v; break
    else:  # EUC-JP / fullwidth
        if "芝" in text: surface = "TURF"
        elif "ダート" in text: surface = "DIRT"
        # fullwidth digits U+FF10..FF19 -> ascii
        fw = "".join(chr(ord(c) - 0xFEE0) if 0xFF10 <= ord(c) <= 0xFF19 else c for c in text)
        m = re.search(r"(\d{3,4})", fw)
        if m: dist = int(m.group(1))
        for jp, v in JP_VENUES.items():
            if text.startswith(jp): venue = v["en"]; break
    return venue, surface, dist

def enrich_courses(rows, enc):
    out = []
    for r in rows:
        v, surf, d = surface_distance(r["text"], enc)
        out.append({**r, "venue": v, "surface": surf, "distanceM": d})
    return out

# ---- extract one version -----------------------------------------------------
def extract(cfg):
    buf = open(cfg["rom"], "rb").read()
    enc = cfg["enc"]
    secs = {}
    for name, (s, e) in cfg["sections"].items():
        if enc == "ascii":
            rows = parse_ascii(buf, s, e)
        else:
            fs = G1_FIRST if name == "g1" else VENUE_FIRST
            rows = parse_euc(buf, s, e, fs)
        if name in ("course", "display"):
            rows = enrich_courses(rows, enc)
        secs[name] = {"start": hex(s), "end": hex(e), "count": len(rows), "entries": rows}
    return buf, secs

def venue_breakdown(course_rows):
    c = Counter(r.get("venue") or "?" for r in course_rows)
    surf = Counter(r.get("surface") or "?" for r in course_rows)
    return {"byVenue": dict(c), "bySurface": dict(surf)}

def main():
    os.makedirs(OUT, exist_ok=True)
    data = {
        "_about": "doc-core canonical tracks / courses / G1 calendar, byte-exact display string tables "
                  "from the 4 DOC program ROMs. These are on-screen labels (surface+distance encoded in "
                  "the text); the per-race binary schedule/grade/purse table is separate and NOT decoded "
                  "here. EN<->JP venue map is positional (verified by 1:1 course alignment).",
        "venueMap": VENUE_MAP,
        "versions": {},
        "verification": {},
    }
    print("=== doc-core tracks extraction ===")
    all_pass = True
    for key, cfg in VERSIONS.items():
        buf, secs = extract(cfg)
        sig_ok = buf[0x8000:0x8008].hex() == cfg["sig"]
        sec, idx, expect = cfg["verify"]
        got = secs[sec]["entries"][idx]["text"] if idx < len(secs[sec]["entries"]) else None
        v_ok = (got == expect)
        all_pass &= sig_ok and v_ok
        data["versions"][key] = {
            "label": cfg["label"], "tag": cfg["tag"], "encoding": cfg["enc"],
            "sig8000": cfg["sig"],
            "counts": {n: secs[n]["count"] for n in secs},
            "venueBreakdown": venue_breakdown(secs["course"]["entries"]),
            "hasHandicap": "handicap" in secs,
            "sections": secs,
        }
        data["verification"][key] = {
            "sig8000": "PASS" if sig_ok else f"FAIL(got {buf[0x8000:0x8008].hex()})",
            "anchor": f"{sec}[{idx}]", "expected": expect, "got": got,
            "result": "PASS" if v_ok else "FAIL",
        }
        cl = secs["course"]["count"]; g1 = secs["g1"]["count"]
        print(f"  {key:9} {cfg['tag']:9} sig={'OK' if sig_ok else 'BAD'} "
              f"courses={cl} g1={g1} special={secs['special']['count']} "
              f"handicap={secs.get('handicap',{}).get('count','-')} "
              f"| verify {sec}[{idx}]={'PASS' if v_ok else 'FAIL'} ({got!r})")
    path = f"{OUT}/doc_core_tracks.json"
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote {path} ({os.path.getsize(path):,} bytes)")
    print("OVERALL:", "PASS" if all_pass else "FAIL")

if __name__ == "__main__":
    main()
