#!/usr/bin/env python3
"""doc_card.py - the canonical Derby Owners Club .card codec (US + JP).

A clean, dependency-free, byte-exact codec for the 207-byte Flycast `.card`
(3 tracks x 0x45 bytes). It is the foundational layer other DOC card tools import,
mirroring the JS logic in Tools/DOC-Card-Creator.html (buildFlycastCard / loadFlycastCard /
buildArraysFromForm / populateForm) and the JP kana table from _jp_re/jp_decode.py.

KIND DETECTION (per file, verified on real cards):
  - ASCII "SEGABEF0" at file offset 0x8A..0x91  -> US / World Edition card (full 3-track stat card)
  - else bytes 0x20==0x03, 0x21==0x02           -> JP (DOC 2000 / DOC '99) identity/pedigree card

CONTAINER (verified):
  207 bytes = 3 tracks of 69 (0x45). Logical bytes are stored REVERSED per track:
  logical aN[k] (k=1..69) lives at file offset t*69 + (69-k). So aN[69]=track start, aN[1]=track end.

BYTE-EXACT ROUND-TRIP GUARANTEE:
  decode() keeps the full 207 source bytes (dict key "raw", hex). encode() rebuilds the canvas
  from "raw" when present, then overlays the editable fields. This preserves every documented-but-
  unmapped byte (US zero regions; JP lead-id, heap-leak tracks 2-3, and the per-write trailer nonce
  at 0x43/0x44 which is NOT a recomputable checksum). encode() of a freshly decoded dict is therefore
  byte-identical to the source. There is no whole-card checksum in the decoded 207-byte payload
  (integrity lives in the .raw physical layer, not here), so this is both correct and lossless.

CLI:
  python3 doc_card.py decode <file.card>            -> JSON to stdout
  python3 doc_card.py encode <file.json> [out.card] -> writes a byte-exact 207-byte .card
  python3 doc_card.py info   <file.card>            -> human-readable summary
  python3 doc_card.py selftest                       -> round-trip every bundled real card

Offsets/enums below were re-verified against real bytes (WillyJR Rev C, JP sat2/sat3 captures),
not trusted from the area docs. See doc-core/README.md for the house style.
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CARD_LEN = 207
TRACK = 69  # 0x45

# ----------------------------------------------------------------------------- enums / tables (US)

# Personality: raw 0-255 byte at a1[6]; 8 ROM-derived bands (us-card.md S2). The editor collapses
# to 5 anchors {R:0,I:48,C:64,H:80,S:208} which is lossy -- we keep the raw byte and label the band.
PERSONALITY_BANDS = [
    (0, 47, "Rough"), (48, 63, "Imposing"), (64, 111, "Calm"), (112, 127, "Firm"),
    (128, 175, "Sensitive"), (176, 191, "Moody"), (192, 239, "Gentle"), (240, 255, "Proud"),
]


def personality_band(v):
    for lo, hi, name in PERSONALITY_BANDS:
        if lo <= v <= hi:
            return name
    return "?"


# Coat: a1[8]=base, a1[9]=modifier (used only when base==63). Mirrors getColorName().
COAT_SPECIAL = {  # base==63: modifier -> name
    0: "Okapi", 16: "Cow", 48: "Panda", 64: "Platinum", 80: "White",
    112: "Org Panda", 192: "Zebra", 208: "Cow_2", 240: "Tiger",
}
_BAY = {77, 78, 79, 141, 142, 143, 205, 206, 207}
_BLACK = {65, 66, 67, 129, 130, 131, 193, 194, 195}
_BROWN = {69, 70, 71, 73, 74, 75, 133, 134, 135, 137, 138, 139, 197, 198, 199, 201, 202, 203}
_CHESTNUT = {64, 68, 72, 76, 128, 132, 136, 140, 192, 196, 200, 204}


def coat_name(c1, c2):
    if c1 == 63:
        return COAT_SPECIAL.get(c2, "Special")
    if c1 in _BAY:
        return "Bay"
    if c1 in _BLACK:
        return "Black"
    if c1 in _BROWN:
        return "Brown"
    if c1 in _CHESTNUT:
        return "Chestnut"
    return "Gray"


SILK_COLORS = ['Black', 'Grey', 'Blue', 'Teal', 'Brown', 'Maroon', 'Green', 'Light Green',
               'Magenta', 'Light Blue', 'Purple', 'Pink', 'Red', 'White', 'Yellow']
SEX = {0: "Male", 1: "Female", 2: "Gelding"}
LEG_TYPES = ["Front-runner", "Start dash", "Last spurt", "Stretch-runner", "Almighty"]

# G1 titles bitfield: 18 races across a2[55],a2[56],a2[57] (G1_RACES in Card-Creator, verified).
G1_RACES = [
    {"id": 1, "name": "Winter Stakes", "byte": 57, "bit": 1},
    {"id": 2, "name": "Sprinter Trophy", "byte": 55, "bit": 16},
    {"id": 3, "name": "Doc 1000", "byte": 57, "bit": 2},
    {"id": 4, "name": "Doc 2000", "byte": 57, "bit": 4},
    {"id": 5, "name": "Spring Classic", "byte": 57, "bit": 8},
    {"id": 6, "name": "American Oak", "byte": 57, "bit": 128},
    {"id": 7, "name": "American Derby", "byte": 57, "bit": 16},
    {"id": 8, "name": "Summer Grand Prix", "byte": 56, "bit": 1},
    {"id": 9, "name": "Super Dirt GPX", "byte": 56, "bit": 2},
    {"id": 10, "name": "Sprinter Stakes", "byte": 55, "bit": 1},
    {"id": 11, "name": "Stayers Stakes", "byte": 56, "bit": 16},
    {"id": 12, "name": "QE II", "byte": 56, "bit": 32},
    {"id": 13, "name": "Mile Champ", "byte": 56, "bit": 64},
    {"id": 14, "name": "Japan Cup Dirt", "byte": 55, "bit": 8},
    {"id": 15, "name": "Japan Cup", "byte": 56, "bit": 128},
    {"id": 16, "name": "Derby Owners Cup", "byte": 55, "bit": 4},
    {"id": 17, "name": "Hong Kong Derby", "byte": 57, "bit": 64},
    {"id": 18, "name": "Hong Kong Oaks", "byte": 57, "bit": 32},
]

# ----------------------------------------------------------------------------- JP kana table

_JP_COLS = {
    'a': list('アカサタナハマヤラワガザダバパ'),
    'i': ['イ', 'キ', 'シ', 'チ', 'ニ', 'ヒ', 'ミ', None, 'リ', None, 'ギ', 'ジ', 'ヂ', 'ビ', 'ピ'],
    'u': ['ウ', 'ク', 'ス', 'ツ', 'ヌ', 'フ', 'ム', 'ユ', 'ル', None, 'グ', 'ズ', 'ヅ', 'ブ', 'プ'],
    'e': ['エ', 'ケ', 'セ', 'テ', 'ネ', 'ヘ', 'メ', None, 'レ', None, 'ゲ', 'ゼ', 'デ', 'ベ', 'ペ'],
    'o': list('オコソトノホモヨロヲゴゾドボポ'),
}
JP_TABLE = {}
for _ci, _v in enumerate(['a', 'i', 'u', 'e', 'o']):
    for _r in range(15):
        if _JP_COLS[_v][_r] is not None:
            JP_TABLE[_ci * 15 + _r] = _JP_COLS[_v][_r]
JP_TABLE.update({0x4b: 'ァ', 0x4c: 'ィ', 0x4d: 'ゥ', 0x4e: 'ェ', 0x4f: 'ォ',
                 0x50: 'ャ', 0x51: 'ュ', 0x52: 'ョ', 0x53: 'ッ', 0x54: 'ー', 0x45: 'ン'})
JP_REV = {v: k for k, v in JP_TABLE.items()}
JP_PAD = 0x7d
JP_NAME_OFF = 0x28


def jp_decode_bytes(byts):
    return ''.join(JP_TABLE.get(b, f'[{b:02x}]') for b in byts)


def jp_encode_name(name):
    """Unicode katakana -> game bytes; returns None if any char is unmapped."""
    out = bytearray()
    for ch in name:
        if ch not in JP_REV:
            return None
        out.append(JP_REV[ch])
    return bytes(out)


# ----------------------------------------------------------------------------- logical-track helpers

def a_get(card, t, k):
    """Logical byte aN[k] (1-based) of track t (0-based) from the reversed file layout."""
    return card[t * TRACK + (TRACK - k)]


def a_set(card, t, k, val):
    card[t * TRACK + (TRACK - k)] = val & 0xFF


def a_off(t, k):
    """File offset of logical aN[k]."""
    return t * TRACK + (TRACK - k)


def _ascii_name(card, t, hi, lo):
    """Read an ASCII name from logical indices hi..lo (descending), printable only, masked 7-bit."""
    out = []
    for k in range(hi, lo - 1, -1):
        b = a_get(card, t, k) & 0x7f
        if 32 <= b < 127:
            out.append(chr(b))
    return ''.join(out).strip()


def _set_ascii_name(card, t, hi, text, maxlen=18):
    """Write text into logical aN[hi], aN[hi-1], ... (descending), 0-padded to maxlen. Mirrors setString."""
    for i in range(maxlen):
        a_set(card, t, hi - i, ord(text[i]) if i < len(text) else 0)


# ----------------------------------------------------------------------------- kind detection

def detect_kind(card):
    if len(card) < 0x92:
        return "unknown"
    if bytes(card[0x8A:0x92]) == b"SEGABEF0":
        return "us"
    if card[0x20] == 0x03 and card[0x21] == 0x02:
        return "jp"
    return "unknown"


# ----------------------------------------------------------------------------- US decode / encode

def _decode_g1(b55, b56, b57):
    titles = []
    for r in G1_RACES:
        v = {55: b55, 56: b56, 57: b57}[r["byte"]]
        if v & r["bit"]:
            titles.append(r["name"])
    return titles


def _leg_type_from_ext(ext):
    """On-screen leg type derived from externals (legTypeFromExt): rank of START, Corner excluded."""
    all6 = [ext["start"], ext["corner"], ext["oob"], ext["competing"], ext["tenacious"], ext["spurt"]]
    if all(v == all6[0] for v in all6):
        return 4  # Almighty
    considered = [ext["start"], ext["oob"], ext["competing"], ext["tenacious"], ext["spurt"]]
    rank = 1 + sum(1 for v in considered if v > ext["start"])
    if rank <= 1:
        return 0
    if rank == 2:
        return 1
    if rank == 3:
        return 2
    return 3


def decode_us(card):
    g = lambda t, k: a_get(card, t, k)
    uid = [g(0, 2), g(0, 3), g(0, 4), g(0, 5)]
    # current externals stored Spurt..Start ascending; display = byte+1
    ext = {"spurt": g(1, 38) + 1, "tenacious": g(1, 39) + 1, "competing": g(1, 40) + 1,
           "oob": g(1, 41) + 1, "corner": g(1, 42) + 1, "start": g(1, 43) + 1}
    ret_ext = {"spurt": g(1, 28) + 1, "tenacious": g(1, 29) + 1, "competing": g(1, 30) + 1,
               "oob": g(1, 31) + 1, "corner": g(1, 32) + 1, "start": g(1, 33) + 1}
    internals = {"stamina": min(g(1, 69), 60), "speed": min(g(1, 65), 60), "sharp": min(g(1, 61), 60)}
    ret_internals = {"stamina": min(g(1, 25), 45), "speed": min(g(1, 24), 45), "sharp": min(g(1, 23), 45)}
    earnings_internal = g(1, 51) * 65536 + g(1, 52) * 256 + g(1, 53)
    races = {"total": g(1, 35), "won": g(1, 49), "place": g(1, 48), "show": g(1, 47), "out": g(1, 46)}
    return {
        "kind": "us",
        "marker": "SEGABEF0",
        "uid": uid,
        "name": _ascii_name(card, 0, 69, 51),
        "sire": _ascii_name(card, 0, 49, 31),
        "dam": _ascii_name(card, 0, 29, 11),
        "personality": {"value": g(0, 6), "band": personality_band(g(0, 6))},
        "runStyleSeed": g(0, 7),
        "coat": {"base": g(0, 8), "modifier": g(0, 9), "name": coat_name(g(0, 8), g(0, 9))},
        "sex": {"value": g(1, 16), "name": SEX.get(g(1, 16), "?")},
        "legType": LEG_TYPES[_leg_type_from_ext(ext)],
        "externals": ext,
        "retirementExternals": ret_ext,
        "internals": internals,
        "retirementInternals": ret_internals,
        "hearts": (g(1, 37) + 1) // 4,
        "heartsByte": g(1, 37),
        "races": races,
        "earningsDollars": earnings_internal * 1000,
        "g1Titles": _decode_g1(g(1, 55), g(1, 56), g(1, 57)),
        "silk": {"pattern": g(1, 15), "color1": g(1, 14), "color1Name": SILK_COLORS[g(1, 14)] if g(1, 14) < len(SILK_COLORS) else "?",
                 "color2": g(1, 13), "color2Name": SILK_COLORS[g(1, 13)] if g(1, 13) < len(SILK_COLORS) else "?"},
        "hood": g(1, 26),
        "dirt": g(2, 61),
        "retired": g(2, 57) == 1,
        "breeds": g(2, 53) // 2,
        "raw": card.hex(),
    }


def encode_us(d):
    """Rebuild a byte-exact 207-byte US card. Starts from d['raw'] if present (preserving every
    unmapped byte) else from a known-good Rev C template; then overlays editable fields."""
    card = bytearray.fromhex(d["raw"]) if d.get("raw") else bytearray(_US_TEMPLATE())
    if len(card) != CARD_LEN:
        raise ValueError("raw is not 207 bytes")
    # markers (always enforce)
    sig = b"SEGABEF0"
    for i in range(8):
        card[0x8A + i] = sig[i]
    card[0x9C] = 0x30
    card[0x9D] = 0x10
    # UID (track 1) mirrored to all 3 tracks
    uid = d.get("uid")
    if uid:
        for t in range(3):
            for j, k in enumerate(range(2, 6)):
                a_set(card, t, k, uid[j])
    # names
    _set_ascii_name(card, 0, 69, d.get("name", ""))
    _set_ascii_name(card, 0, 49, d.get("sire", ""))
    _set_ascii_name(card, 0, 29, d.get("dam", ""))
    # personality (raw byte preferred; band-only would be lossy)
    pers = d.get("personality", {})
    if isinstance(pers, dict) and "value" in pers:
        a_set(card, 0, 6, pers["value"])
    if "runStyleSeed" in d:
        a_set(card, 0, 7, d["runStyleSeed"])
    coat = d.get("coat", {})
    if "base" in coat:
        a_set(card, 0, 8, coat["base"])
        a_set(card, 0, 9, coat.get("modifier", 0))
    # sex
    sex = d.get("sex", {})
    a_set(card, 1, 16, sex["value"] if isinstance(sex, dict) else sex)
    # externals (current): display-1
    ex = d["externals"]
    a_set(card, 1, 38, ex["spurt"] - 1)
    a_set(card, 1, 39, ex["tenacious"] - 1)
    a_set(card, 1, 40, ex["competing"] - 1)
    a_set(card, 1, 41, ex["oob"] - 1)
    a_set(card, 1, 42, ex["corner"] - 1)
    a_set(card, 1, 43, ex["start"] - 1)
    rex = d["retirementExternals"]
    a_set(card, 1, 28, rex["spurt"] - 1)
    a_set(card, 1, 29, rex["tenacious"] - 1)
    a_set(card, 1, 30, rex["competing"] - 1)
    a_set(card, 1, 31, rex["oob"] - 1)
    a_set(card, 1, 32, rex["corner"] - 1)
    a_set(card, 1, 33, rex["start"] - 1)
    intr = d["internals"]
    a_set(card, 1, 69, intr["stamina"])
    a_set(card, 1, 65, intr["speed"])
    a_set(card, 1, 61, intr["sharp"])
    rin = d["retirementInternals"]
    a_set(card, 1, 25, rin["stamina"])
    a_set(card, 1, 24, rin["speed"])
    a_set(card, 1, 23, rin["sharp"])
    # hearts: store raw byte if present, else reconstruct from display (hearts*4-1)
    if "heartsByte" in d:
        a_set(card, 1, 37, d["heartsByte"])
    else:
        a_set(card, 1, 37, d["hearts"] * 4 - 1)
    rc = d["races"]
    a_set(card, 1, 35, rc["total"])
    a_set(card, 1, 49, rc["won"])
    a_set(card, 1, 48, rc["place"])
    a_set(card, 1, 47, rc["show"])
    a_set(card, 1, 46, rc["out"])
    a_set(card, 1, 34, rc["won"])  # win duplicate
    earnings_internal = d["earningsDollars"] // 1000
    a_set(card, 1, 51, earnings_internal // 65536)
    a_set(card, 1, 52, (earnings_internal % 65536) // 256)
    a_set(card, 1, 53, earnings_internal % 256)
    # G1
    b55 = b56 = b57 = 0
    titles = set(d.get("g1Titles", []))
    by_name = {r["name"]: r for r in G1_RACES}
    for nm in titles:
        r = by_name.get(nm)
        if not r:
            continue
        if r["byte"] == 55:
            b55 |= r["bit"]
        elif r["byte"] == 56:
            b56 |= r["bit"]
        else:
            b57 |= r["bit"]
    a_set(card, 1, 55, b55)
    a_set(card, 1, 56, b56)
    a_set(card, 1, 57, b57)
    silk = d.get("silk", {})
    a_set(card, 1, 15, silk.get("pattern", 0))
    a_set(card, 1, 14, silk.get("color1", 0))
    a_set(card, 1, 13, silk.get("color2", 0))
    a_set(card, 1, 26, d.get("hood", 0))
    a_set(card, 2, 61, d["dirt"])
    a_set(card, 2, 57, 1 if d.get("retired") else 0)
    a_set(card, 2, 53, (d.get("breeds", 0) * 2) if d.get("retired") else 0)
    return bytes(card)


# Known-good Rev C structure (logical a1/a2/a3 from Card-Creator TPL_*), as a 207-byte file canvas.
def _US_TEMPLATE():
    tpl_a1 = [0, 0, 144, 78, 18, 28, 80, 86, 129, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 121, 114, 97, 77, 32, 115, 115, 105, 77, 0, 0, 0, 0, 0, 0, 0, 0, 114, 101, 100, 110, 111, 87, 32, 115, 115, 97, 114, 71, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 82, 74, 32, 121, 108, 108, 105, 87]
    tpl_a2 = [0, 0, 144, 78, 18, 28, 0, 0, 0, 0, 0, 0, 88, 3, 5, 6, 0, 0, 8, 8, 1, 1, 1, 45, 45, 33, 7, 0, 15, 6, 8, 12, 12, 12, 3, 4, 1, 63, 34, 12, 12, 28, 32, 32, 1, 1, 1, 0, 0, 3, 0, 0, 4, 36, 0, 0, 0, 0, 0, 0, 0, 49, 0, 0, 0, 57, 0, 0, 0, 58]
    tpl_a3 = [0, 8, 144, 78, 18, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 109, 48, 70, 69, 66, 65, 71, 69, 83]
    card = bytearray(CARD_LEN)
    for t, arr in enumerate((tpl_a1, tpl_a2, tpl_a3)):
        for i in range(TRACK):
            card[t * TRACK + i] = (arr[TRACK - i] if (TRACK - i) < len(arr) else 0) & 0xFF
    return card


# ----------------------------------------------------------------------------- JP decode / encode

def _jp_read_fields(card):
    """Return [horse, sire, dam] as Unicode + the raw byte spans, walking 0x28.. terminated by 0x7d.
    The dam field has no trailing PAD in real cards; it ends at 0x42 and the next 2 bytes (0x43,0x44)
    are the per-write trailer nonce, which bleeds into a naive walk. We capture spans to 0x44 but the
    decoded readable strings stop at the last mapped kana."""
    fields = []
    i = JP_NAME_OFF
    for _ in range(3):
        start = i
        seg = bytearray()
        while i < 0x45 and card[i] != JP_PAD:
            seg.append(card[i])
            i += 1
        fields.append((bytes(seg), start, i))
        while i < 0x45 and card[i] == JP_PAD:
            i += 1
    return fields


def _jp_clean(text):
    # strip a trailing run of unmapped [xx] tokens (trailer bleed)
    while text.endswith("]"):
        cut = text.rfind("[")
        if cut == -1:
            break
        text = text[:cut]
    return text


def decode_jp(card):
    fields = _jp_read_fields(card)
    horse = jp_decode_bytes(fields[0][0])
    sire = jp_decode_bytes(fields[1][0])
    dam = _jp_clean(jp_decode_bytes(fields[2][0]))
    return {
        "kind": "jp",
        "marker": None,
        "formatMarker": [card[0x20], card[0x21]],
        "leadId": [card[0x25], card[0x26], card[0x27]],
        "name": horse,
        "sire": sire,
        "dam": dam,
        "trailer": [card[0x43], card[0x44]],
        "note": "JP DOC 2000/'99 is an identity/pedigree card: stats/sex/leg-type are cabinet-side, not on the card.",
        "raw": card.hex(),
    }


def encode_jp(d):
    """Rebuild a byte-exact 207-byte JP card. Starts from d['raw'] (preserving lead-id, the trailer
    nonce, header skeleton, and the heap-leak tracks 2-3 which DOC 2000 never writes), then overlays
    the kana name/sire/dam region. encode of a decoded card is byte-identical."""
    if not d.get("raw"):
        raise ValueError("JP encode requires 'raw' (lead-id + trailer nonce are not derivable)")
    card = bytearray.fromhex(d["raw"])
    if len(card) != CARD_LEN:
        raise ValueError("raw is not 207 bytes")
    # Byte-exact strategy: the dam field has no terminating PAD, so its span boundary is ambiguous
    # (the trailer nonce at 0x43/0x44 bleeds in). We therefore only OVERWRITE a field when the caller
    # actually changed it from the decoded value, and we map the new kana over the *encodable* prefix
    # of that field's span (the bleed bytes are NOT re-encoded). For an unchanged field we touch
    # nothing, so encode(decode(raw)) == raw exactly.
    decoded = decode_jp(card)
    fields = _jp_read_fields(card)  # [(raw_bytes, start, end), ...]
    cur = [decoded["name"], decoded["sire"], decoded["dam"]]
    want = [d.get("name"), d.get("sire"), d.get("dam")]
    for idx, (orig_bytes, start, end) in enumerate(fields):
        if want[idx] is None or want[idx] == cur[idx]:
            continue  # unchanged -> keep original bytes verbatim (byte-exact)
        enc = jp_encode_name(want[idx])
        if enc is None:
            raise ValueError(f"unmapped kana in {want[idx]!r}")
        # length of the kana actually decoded for this field (excludes trailer bleed on the dam)
        decoded_len = len(cur[idx])
        if len(enc) != decoded_len:
            raise ValueError(
                f"JP field {idx} new length {len(enc)} != original {decoded_len}; "
                "a different-length kana name would shift the PADs/trailer (not byte-safe)")
        for j in range(len(enc)):
            card[start + j] = enc[j]
    return bytes(card)


# ----------------------------------------------------------------------------- public API

def decode(card_bytes):
    """Decode a 207-byte .card (bytes/bytearray) to a dict. kind = 'us' | 'jp' | 'unknown'."""
    if len(card_bytes) != CARD_LEN:
        raise ValueError(f"card must be {CARD_LEN} bytes, got {len(card_bytes)}")
    card = bytes(card_bytes)
    kind = detect_kind(card)
    if kind == "us":
        return decode_us(card)
    if kind == "jp":
        return decode_jp(card)
    return {"kind": "unknown", "raw": card.hex(),
            "note": "no SEGABEF0 marker and no 0x03/0x02 JP skeleton; cannot classify"}


def encode(d):
    """Encode a dict back to a byte-exact 207-byte .card."""
    kind = d.get("kind")
    if kind == "us":
        out = encode_us(d)
    elif kind == "jp":
        out = encode_jp(d)
    else:
        raise ValueError(f"cannot encode kind={kind!r}")
    if len(out) != CARD_LEN:
        raise ValueError("encoded card is not 207 bytes")
    return out


def validate(d):
    """Return a list of human-readable problems (empty = valid). US-only structural checks."""
    problems = []
    if d.get("kind") == "us":
        rc = d.get("races", {})
        s = rc.get("won", 0) + rc.get("place", 0) + rc.get("show", 0) + rc.get("out", 0)
        if s != rc.get("total", 0):
            problems.append(f"race results sum {s} != total {rc.get('total', 0)}")
        if d.get("earningsDollars", 0) % 1000 != 0:
            problems.append(f"earnings {d.get('earningsDollars')} is not a multiple of $1,000")
        for nm in d.get("g1Titles", []):
            if nm not in {r["name"] for r in G1_RACES}:
                problems.append(f"unknown G1 title {nm!r}")
    return problems


# ----------------------------------------------------------------------------- info / CLI

def info_text(d):
    lines = []
    k = d.get("kind")
    if k == "us":
        lines.append(f"US / World Edition card  (marker {d['marker']})")
        lines.append(f"  Name : {d['name']}")
        lines.append(f"  Sire : {d['sire']}")
        lines.append(f"  Dam  : {d['dam']}")
        lines.append(f"  Sex  : {d['sex']['name']}   Coat: {d['coat']['name']}   "
                     f"Personality: {d['personality']['band']} ({d['personality']['value']})")
        lines.append(f"  Leg  : {d['legType']}   Hearts: {d['hearts']}   Dirt: {d['dirt']}   "
                     f"Retired: {d['retired']}  Breeds: {d['breeds']}")
        ex = d['externals']
        lines.append("  Externals (cur): " + " ".join(f"{n}={ex[n]}" for n in
                     ("start", "corner", "oob", "competing", "tenacious", "spurt")))
        i = d['internals']
        lines.append(f"  Internals     : stamina={i['stamina']} speed={i['speed']} sharp={i['sharp']}")
        rc = d['races']
        lines.append(f"  Record        : {rc['total']} races  W{rc['won']} P{rc['place']} "
                     f"S{rc['show']} O{rc['out']}   Earnings ${d['earningsDollars']:,}")
        s = d['silk']
        lines.append(f"  Silks         : pattern {s['pattern']}  {s['color1Name']}/{s['color2Name']}  Hood {d['hood']}")
        lines.append(f"  G1 titles ({len(d['g1Titles'])}): " + (", ".join(d['g1Titles']) or "(none)"))
        lines.append(f"  UID           : {' '.join(f'{b:02x}' for b in d['uid'])}")
    elif k == "jp":
        lines.append("JP / DOC 2000 / DOC '99 card  (identity/pedigree)")
        lines.append(f"  Name : {d['name']}")
        lines.append(f"  Sire : {d['sire']}")
        lines.append(f"  Dam  : {d['dam']}")
        lines.append(f"  Lead-ID : {' '.join(f'{b:02x}' for b in d['leadId'])}   "
                     f"Trailer: {' '.join(f'{b:02x}' for b in d['trailer'])}")
        lines.append(f"  {d['note']}")
    else:
        lines.append("Unknown card kind: " + d.get("note", ""))
    probs = validate(d)
    if probs:
        lines.append("  VALIDATION: " + "; ".join(probs))
    return "\n".join(lines)


def _selftest():
    base = r"C:/DerbyOwnersClub"
    candidates = [
        f"{base}/Tools/Cards/WillyJR_patched.drbyocwc.card",
        f"{base}/Tools/Cards/BabyBoy.derbyocw.card",
        f"{base}/_jp_re/captures/frozen1/derbyo2k_sat1.card",
        f"{base}/_jp_re/captures/frozen1/derbyo2k_sat2.card",
        f"{base}/_jp_re/captures/frozen1/derbyo2k_sat3.card",
        f"{base}/_jp_re/captures/frozen1/derbyo2k_sat4.card",
        f"{base}/_jp_re/captures/derbyo2k_sat1_unknownname.card",
        f"{base}/_jp_re/captures/derbyo2k_sat2_unknownname.card",
        f"{base}/_jp_re/captures/derbyo2k_sat3_unknownname.card",
        f"{base}/_jp_re/captures/derbyo2k_sat4_unknownname.card",
        f"{base}/_jp_re/test_card_john.card",
    ]
    n_ok = n_fail = n_skip = 0
    for path in candidates:
        if not os.path.exists(path):
            n_skip += 1
            continue
        raw = open(path, "rb").read()
        if len(raw) != CARD_LEN:
            print(f"  SKIP  {os.path.basename(path)} (not 207 bytes)")
            n_skip += 1
            continue
        d = decode(raw)
        re = encode(d) if d["kind"] in ("us", "jp") else None
        ident = (re == raw) if re is not None else False
        nm = d.get("name", "")
        status = "PASS" if ident else "FAIL"
        if ident:
            n_ok += 1
        else:
            n_fail += 1
        print(f"  {status}  {os.path.basename(path):42} kind={d['kind']:7} name={nm!r}")
        if not ident and re is not None:
            diffs = [i for i in range(CARD_LEN) if re[i] != raw[i]]
            print(f"        {len(diffs)} byte diffs at offsets {[hex(x) for x in diffs[:16]]}")
    print(f"\n  round-trip: {n_ok} PASS, {n_fail} FAIL, {n_skip} skipped")
    return n_fail == 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "decode":
        d = decode(open(argv[2], "rb").read())
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    if cmd == "encode":
        d = json.load(open(argv[2], encoding="utf-8"))
        out = encode(d)
        dest = argv[3] if len(argv) > 3 else os.path.splitext(argv[2])[0] + ".card"
        open(dest, "wb").write(out)
        print(f"wrote {dest} ({len(out)} bytes)")
        return 0
    if cmd == "info":
        d = decode(open(argv[2], "rb").read())
        print(info_text(d))
        return 0
    if cmd == "selftest":
        print("=== doc_card.py round-trip selftest ===")
        ok = _selftest()
        print("VERDICT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    print(f"unknown command {cmd!r}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
