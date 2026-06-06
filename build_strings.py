#!/usr/bin/env python3
"""doc-core: cross-version game-text / string catalog extractor for Derby Owners Club.

Reads in-game text straight from each NAOMI program ROM and emits one canonical JSON
(`doc_core_strings.json`) of labeled text blocks/regions per version, byte-exact, with
offset, encoding, category, count and the extracted strings. Source of truth = the binary.

Encoding (verified on bytes, see _core/areas/game-text.md):
  EN (Rev C / Rev D): 7-bit ASCII, NUL(0x00)-terminated, packed back-to-back. A leading
    0x0F (one or more) display-attribute prefix precedes some strings; engine strips it,
    so we do too. 0x0A appears literally inside multi-line strings.
  JP (DOC2000 / DOC'99): EUC-JP (JIS X 0208 2-byte lead 0xA1-0xFE, half-width kana 0x8E+0xA1-0xDF),
    ASCII single-byte pass-through, NUL-terminated. Same 0x0F prefix + 0x0A newline convention.

parseBlock mirrors DOC-ROM-Studio.html: walk a [start,end) window, split on NUL / non-text
bytes, keep runs whose printable ratio is high. Placeholders (%s,%d,%0d,%1d,%2d) are preserved
verbatim in the extracted text.

Self-verifies known strings decode at their offsets and prints PASS/FAIL.
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ONE = r"C:/Users/johnr/OneDrive - Indigenous Healthcare Advancements/Desktop/John and Pui/Derby Owners Club/DOC-Naomi Roms/Roms"
OUT = r"C:/DerbyOwnersClub/doc-core"

ROMS = {
    "drbyocwc": {"label": "World Edition (Rev C)",    "tag": "Rev C",    "rom": f"{ONE}/drbyocwc/epr-22336c.ic22", "lang": "EN", "enc": "ascii"},
    "derbyocw": {"label": "World Edition EX (Rev D)",  "tag": "Rev D",    "rom": f"{ONE}/derbyocw/epr-22336d.ic22", "lang": "EN", "enc": "ascii"},
    "derbyo2k": {"label": "DOC 2000 (JP)",             "tag": "DOC 2000", "rom": f"{ONE}/derbyo2k/epr-22284a.ic22", "lang": "JP", "enc": "euc-jp"},
    "derbyoc":  {"label": "DOC Original / '99 (JP)",   "tag": "DOC '99",  "rom": f"{ONE}/derbyoc/epr-22099b.ic22",  "lang": "JP", "enc": "euc-jp"},
}

# --- romaji reading aid (compact katakana -> romaji), reused from build_roster.py ---
_KR = {'ア':'a','イ':'i','ウ':'u','エ':'e','オ':'o','カ':'ka','キ':'ki','ク':'ku','ケ':'ke','コ':'ko','サ':'sa','シ':'shi','ス':'su','セ':'se','ソ':'so','タ':'ta','チ':'chi','ツ':'tsu','テ':'te','ト':'to','ナ':'na','ニ':'ni','ヌ':'nu','ネ':'ne','ノ':'no','ハ':'ha','ヒ':'hi','フ':'fu','ヘ':'he','ホ':'ho','マ':'ma','ミ':'mi','ム':'mu','メ':'me','モ':'mo','ヤ':'ya','ユ':'yu','ヨ':'yo','ラ':'ra','リ':'ri','ル':'ru','レ':'re','ロ':'ro','ワ':'wa','ヲ':'wo','ン':'n','ガ':'ga','ギ':'gi','グ':'gu','ゲ':'ge','ゴ':'go','ザ':'za','ジ':'ji','ズ':'zu','ゼ':'ze','ゾ':'zo','ダ':'da','ヂ':'ji','ヅ':'zu','デ':'de','ド':'do','バ':'ba','ビ':'bi','ブ':'bu','ベ':'be','ボ':'bo','パ':'pa','ピ':'pi','プ':'pu','ペ':'pe','ポ':'po','ヴ':'vu'}
_SM = {'ァ':'a','ィ':'i','ゥ':'u','ェ':'e','ォ':'o','ャ':'ya','ュ':'yu','ョ':'yo'}
def romaji(s):
    out, prev, arr = "", "", list(s)
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

def has_kana(s):
    return any(('゠' <= c <= 'ヿ') or ('぀' <= c <= 'ゟ') for c in s)

# --- string decoders ---
def _strip_prefix(raw):
    """drop leading 0x0F display-attribute bytes the engine strips (kept for EUC-JP path)."""
    i = 0
    while i < len(raw) and raw[i] == 0x0F: i += 1
    return raw[i:]

def is_text_ascii(b):
    return b == 0x0A or 0x20 <= b <= 0x7E

def decode_ascii(raw):
    raw = _strip_prefix(raw)
    return bytes(x & 0x7F for x in raw).decode("ascii", "replace")

def decode_eucjp(raw):
    raw = _strip_prefix(raw)
    try: return raw.decode("euc-jp")
    except Exception: return raw.decode("euc-jp", "replace")

def parse_ascii_block(buf, start, end, min_len=2):
    """Faithful port of DOC-ROM-Studio.html parseBlock(a,b): walk [start,end), skip any byte
    <32 or >126 as a separator (so NUL, the 0x0F display marker, 0x0A newline, and the
    length-prefix bytes 0x80/0xF0/0xFF all separate), accumulate a printable run, keep runs
    of length >= 2. 'cap' = bytes from the run start to the next non-zero byte (free space)."""
    out = []
    n = end
    i = start
    while i < n:
        while i < n and (buf[i] < 32 or buf[i] > 126): i += 1
        if i >= n: break
        s = i
        run = bytearray()
        while i < n and 32 <= buf[i] <= 126:
            run.append(buf[i]); i += 1
        j = i
        while j < n and buf[j] == 0: j += 1
        if len(run) >= min_len:
            out.append({"offset": "0x%X" % s, "text": run.decode("ascii", "replace"), "cap": j - s})
    return out

def _is_jp_char(c):
    o = ord(c)
    # katakana, hiragana, CJK ideographs, fullwidth forms
    return ('゠' <= c <= 'ヿ') or ('぀' <= c <= 'ゟ') or (0x4E00 <= o <= 0x9FFF) or (0xFF01 <= o <= 0xFF60) or (0x3000 <= o <= 0x303F)

def parse_eucjp_block(buf, start, end, min_len=2):
    """NUL-split a window into records; decode each as EUC-JP STRICTLY (reject any run that
    does not cleanly decode -- that rules out runs that begin mid-multibyte-char, i.e. window
    edge garbage and binary tables). Leading 0x0F display prefix is stripped. A record is kept
    only if it decodes clean AND either contains real JP text or is meaningful printable ASCII
    (UI label). 0x0A newlines are preserved verbatim inside the string."""
    out = []
    seg = buf[start:end]
    cur_start = start
    run = bytearray()
    def flush(soff, rawbytes):
        rb = _strip_prefix(bytes(rawbytes))
        if len(rb) < min_len: return
        try:
            txt = rb.decode("euc-jp")   # STRICT: no errors='replace'
        except Exception:
            return                      # mid-char / binary -> drop
        if "�" in txt: return
        # reject runs carrying control bytes other than the 0x0A newline (binary tables decode
        # to a lone kanji + a stray \r/\x01/\x0c etc. -- those are not real strings)
        if any(ord(c) < 0x20 and c != "\n" for c in txt): return
        body = txt.replace("\n", "")
        if not body.strip(): return
        jp = sum(1 for c in body if _is_jp_char(c))
        asc = sum(1 for c in body if 0x20 <= ord(c) <= 0x7E)
        # keep if it has real JP content (>=2 JP chars), or is essentially clean ascii (UI label)
        if jp >= 1 and (jp + asc) / max(len(body), 1) < 0.8: return
        if jp == 0:
            if asc < 3 or asc / max(len(body), 1) < 0.9: return
        elif jp == 1 and asc == 0 and len(body) < 2:
            return
        entry = {"offset": "0x%X" % (soff + (len(rawbytes) - len(rb))), "text": txt}
        if has_kana(txt):
            rj = romaji(txt)
            if rj != txt: entry["romaji"] = rj
        out.append(entry)
    for i, b in enumerate(seg):
        if b == 0x00:
            flush(cur_start, run)
            run = bytearray(); cur_start = start + i + 1
        else:
            if not run: cur_start = start + i
            run.append(b)
    flush(cur_start, run)
    return out

# ============================================================================
# CURATED BLOCK TABLES (offsets verified against the real bytes — see verify())
# ============================================================================
# EN Rev C — the 26 curated blocks (matches DOC-ROM-Studio GAMETEXT[]).
REVC_BLOCKS = [
    ("Horse Race Comments",            "dialogue", 0x104548, 0x107DFA),
    ("Trainer & Race Dialogue",        "dialogue", 0x128F38, 0x12B767),
    ("Trainer Comments (2)",           "dialogue", 0x122FA0, 0x123740),
    ("Interaction Menu & Result Text", "menu",     0x0E83D0, 0x0EA492),
    ("Foal / New Horse Comments",      "dialogue", 0x107E26, 0x1081B0),
    ("Feeding Comments",               "dialogue", 0x127B78, 0x12802B),
    ("Post-Food Comments",             "dialogue", 0x12874C, 0x128D66),
    ("Leg-Type Change Messages",       "dialogue", 0x12755C, 0x1277BC),
    ("Stable / Event Messages",        "dialogue", 0x0CA798, 0x0CAE20),
    ("Farm & Card Tutorial",           "dialogue", 0x103CF0, 0x104230),
    ("Auto-Suggested Horse Names",     "names",    0x10FF70, 0x11048C),
    ("Pre-Race Well-Wishes",           "dialogue", 0x128EA8, 0x128F10),
    ("Banned Names List",              "banned",   0x12B7A2, 0x12BC17),
    ("Coin / Insert-Card Prompts",     "card",     0x10FCC8, 0x10FE70),
    ("Attract Mode Text",              "attract",  0x10E804, 0x10EA00),
    ("G1 Selection Screen",            "menu",     0x0EBA8C, 0x0EBB77),
    ("Name-Entry Prompt",              "menu",     0x10FEF4, 0x10FF6F),
    ("Track Condition (Pre-Race)",     "menu",     0x10EA05, 0x10EAB2),
    ("Track Condition",                "menu",     0x10EB3D, 0x10EB62),
    ("Pre-Race Lead / Style Text",     "menu",     0x10EAB3, 0x10EB3C),
    ("Leg-Type Labels (Retirement)",   "menu",     0x0EE270, 0x0EE297),
    ("Retirement Screen Text",         "menu",     0x0ED5B4, 0x0EE0A6),
    ("Retirement Info (SIRE/DAM)",     "menu",     0x0EBEF8, 0x0EBFF0),
    ("Race Board Text",                "menu",     0x0C898C, 0x0C8A64),
    ("Ranking Screen Labels",          "menu",     0x0C80B8, 0x0C8120),
    ("Presented By / Created By",      "branding", 0x10E7BC, 0x10E800),
]

# EN Rev D — curated via anchor+shift (§4). Each block parses from a verified start to an end.
# Anchors verified on bytes; ends chosen at the next structural boundary / size-matched to Rev C.
REVD_BLOCKS = [
    ("Horse Race Comments",          "dialogue", 0x104C75, 0x108800),
    ("Trainer & Race Dialogue",      "dialogue", 0x12B190, 0x12DBA0),
    ("Coin / Insert-Card Prompts",   "card",     0x10FF24, 0x1100D0),
    ("Banned Names List",            "banned",   0x12DCF0, 0x12E160),
    ("Branding / Copyright",         "branding", 0x10FDFC, 0x10FE60),
    ("Retirement Info (SIRE/DAM)",   "menu",     0x0EC328, 0x0EC420),
]

# JP DOC 2000 — dense-EUC-JP regions (§5). Verified region starts; window-scanned.
DOC2K_REGIONS = [
    ("Coat / Sex Labels",            "menu",     0x0CA2C0, 0x0CA600),
    ("Interaction Menu",             "menu",     0x0EB400, 0x0EB900),
    ("Race / Result Dialogue",       "dialogue", 0x0EC000, 0x0ED200),
    ("Card Error / OK Prompts",      "card",     0x0F0800, 0x0F0E00),
    ("Horse / Sire Comments",        "dialogue", 0x105000, 0x108000),
    ("System Messages",              "card",     0x109000, 0x109600),
]

# JP DOC '99 — dense-EUC-JP regions (§5). Verified region starts; window-scanned.
DOC99_REGIONS = [
    ("Feeding / Difficulty Labels",  "menu",     0x0DC000, 0x0DC400),
    ("Interaction Results",          "dialogue", 0x0DD000, 0x0DD600),
    ("Retirement Text",              "menu",     0x0E1000, 0x0E1800),
    ("Horse Comments",               "dialogue", 0x0F2000, 0x0F4000),
    ("Track Names",                  "menu",     0x0BDC00, 0x0BE200),
    ("Card Prompts",                 "card",     0x0FD800, 0x0FE000),
    ("Training Method Help",         "dialogue", 0x115000, 0x116000),
]

CAP = 250  # max strings kept per block (keeps file well under 2 MB)

def build_blocks(buf, blocks, enc):
    out = []
    for name, cat, start, end in blocks:
        if enc == "ascii":
            strings = parse_ascii_block(buf, start, end)
        else:
            strings = parse_eucjp_block(buf, start, end)
        full = len(strings)
        capped = strings[:CAP]
        out.append({
            "block": name, "category": cat,
            "start": "0x%X" % start, "end": "0x%X" % end,
            "encoding": "ASCII (NUL/0x0A)" if enc == "ascii" else "EUC-JP (NUL/0x0A)",
            "count": full, "shown": len(capped),
            "strings": capped,
        })
    return out

# ============================================================================
# VERIFICATION — known strings must decode at their offsets
# ============================================================================
def verify(buf_by_key):
    checks = [
        ("drbyocwc", 0x104548, "He's quite a popular racehorse. He has super stamina.", "ascii"),
        ("drbyocwc", 0x129FF4, "Wow! It's great!\n...But your horse is running away.", "ascii"),
        ("drbyocwc", 0x10FCC8, "TO CREATE A NEW HORSE. PRESS START BUTTON.", "ascii"),
        ("drbyocwc", 0x10E7BC, "Presented By", "ascii"),
        ("derbyocw", 0x10FF24, "TO CREATE A NEW HORSE, PRESS START BUTTON.", "ascii"),
        ("derbyocw", 0x12DCF0, "anal", "ascii"),
        ("derbyo2k", 0x0EC018, "%sは、初めての\n  レースで精一杯頑張りました。", "euc-jp"),
        ("derbyoc",  0x0BDCA7, "東京 ダート １２００Ｍ", "euc-jp"),
    ]
    results = []
    allpass = True
    for key, off, expect, enc in checks:
        buf = buf_by_key[key]
        raw = buf[off:off + 200].split(b"\x00")[0]
        got = decode_ascii(raw) if enc == "ascii" else decode_eucjp(raw)
        ok = got == expect
        allpass = allpass and ok
        results.append({"version": key, "offset": "0x%X" % off, "expected": expect, "got": got, "pass": ok})
        print(f"  [{'PASS' if ok else 'FAIL'}] {key} @0x{off:X}: {got!r}")
    return allpass, results

def main():
    os.makedirs(OUT, exist_ok=True)
    bufs = {k: open(c["rom"], "rb").read() for k, c in ROMS.items()}

    print("=== doc-core string-catalog verification ===")
    allpass, vresults = verify(bufs)
    print("VERIFY:", "ALL PASS" if allpass else "FAILURES PRESENT")

    print("\n=== extraction ===")
    versions = {}
    for key, cfg in ROMS.items():
        if key == "drbyocwc": blocks = build_blocks(bufs[key], REVC_BLOCKS, "ascii")
        elif key == "derbyocw": blocks = build_blocks(bufs[key], REVD_BLOCKS, "ascii")
        elif key == "derbyo2k": blocks = build_blocks(bufs[key], DOC2K_REGIONS, "euc-jp")
        else: blocks = build_blocks(bufs[key], DOC99_REGIONS, "euc-jp")
        total = sum(b["count"] for b in blocks)
        versions[key] = {
            "label": cfg["label"], "tag": cfg["tag"], "lang": cfg["lang"],
            "encoding": "ASCII" if cfg["enc"] == "ascii" else "EUC-JP",
            "romSize": "0x%X" % len(bufs[key]),
            "blockCount": len(blocks), "stringCount": total,
            "blocks": blocks,
        }
        print(f"  {key:9} {cfg['tag']:9} {len(blocks):2} blocks, {total:5} strings")

    data = {
        "_about": ("doc-core cross-version game-text / string catalog, byte-exact from the program ROMs. "
                   "EN=ASCII (NUL/0x0A-delimited, leading 0x0F display prefix stripped); JP=EUC-JP. "
                   "Placeholders (%s,%d,%0d,%1d,%2d) and 0x0A newlines preserved verbatim. "
                   "Strings capped at " + str(CAP) + " per block. Offsets verified against the real bytes."),
        "categories": {
            "dialogue": "Trainer/race/foal/feeding flavor text (heavy %s/%d + 0x0A)",
            "menu": "UI labels, retirement headers, ranking/board, track condition, coat/sex labels",
            "names": "Auto-suggested horse names (EN)",
            "banned": "ASCII profanity blocklist for name entry (EN)",
            "card": "Insert-card / coin / card-error / system prompts",
            "attract": "Attract-loop text",
            "branding": "Presented By / copyright (version-stamped)",
        },
        "verification": vresults,
        "verifyAllPass": allpass,
        "versions": versions,
    }
    path = f"{OUT}/doc_core_strings.json"
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    size = os.path.getsize(path)
    print(f"\nwrote {path} ({size:,} bytes)")
    if size > 2_000_000: print("WARNING: file exceeds 2 MB")
    print("VERDICT:", "PASS" if allpass else "FAIL")

if __name__ == "__main__":
    main()
