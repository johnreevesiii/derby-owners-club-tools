#!/usr/bin/env python3
"""doc-core: NVRAM (cabinet battery save) decoder for Derby Owners Club.

Decodes the NAOMI cabinet BBSRAM (32 KB) + JVS EEPROM (128 B) into one canonical
JSON: the full schema (offsets/record layout) PLUS a byte-exact sample dump from the
demul07 `derbyocw.sram` save (the World Edition / Rev D cabinet save in this set).

This is the cabinet hall-of-fame, NOT the player card (card = 207-byte `card` area).
The SRAM holds two redundant SAVE REGIONS, each carrying:
  - a money leaderboard (50 records x 32 B, two copies: "standings" + "with metadata"),
  - a per-course track-record table (57 records x 28 B),
  - a region checksum/header,
plus a per-board bookkeeping header at 0x00 (coin/play counters + dip flags).

EVERY offset below was re-verified against the real bytes (see verify() / PASS/FAIL).
Corrections applied over _core/areas/nvram.md (per nvram_VERIFICATION.md, byte-confirmed):
  * region-2 money LB starts at 0x15f4 (NOT 0x1634); region-2 copy-2 at 0x1c34.
  * region stride/delta is +0x13c4 (5060), the same value stored as LE32 at 0x1fc.
  * copy-2 metadata bytes "80 16 00" decode little-endian to 0x1680 (5760), not 0x168000.
  * the 0x100 bookkeeping block is a SECOND distinct header, NOT a verbatim mirror of 0x00.
  * track-record TIME at +0x14 is LE16 in 1/40-second units (cs = raw*5//2), NOT an LE32 centisecond
    value; the old LE32 read swallowed the separate +0x16 field and ran 2.5x fast. See
    TRACK_RECORD_TIME_PRECISION.md.
"""
import json, os, struct, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

NV  = r"C:/Users/johnr/Downloads/demul07_280418/nvram"
OUT = r"C:/DerbyOwnersClub/doc-core"
SRAM   = f"{NV}/derbyocw.sram"      # satellite board sample (32 KB)
SRAM_M = f"{NV}/derbyocwm.sram"     # master board (for the master/satellite diff)
EEPROM = f"{NV}/derbyocw.eeprom"    # JVS EEPROM (128 B; byte-identical to master)

# ---- canonical geometry (byte-verified) -----------------------------------
REGION_STRIDE = 0x13c4              # region2 = region1 + this (= LE32 @0x1fc)
LB_REC = 32                         # money record stride
LB_COUNT = 50
TR_REC = 28                         # track-record stride
TR_COUNT = 57
# region-1 anchors
R1_HEADER   = 0x01f8                # 16-byte region header, doubled at +0x10
R1_MARKER   = 0x0218                # rank-0 sentinel (LE32 + "Big Shuttle")
R1_LB1      = 0x0230                # money LB copy 1 ("current standings")
R1_LB2      = 0x0870                # money LB copy 2 ("with metadata")
R1_TRACK    = 0x0f7c                # track-record table
R1_TRAILER  = 0x15c4                # region-1 trailer (secondary checksum + count)
# region-2 anchors (= region-1 + REGION_STRIDE), verified by the 417935500 money key
R2_HEADER   = R1_HEADER  + REGION_STRIDE  # 0x15bc
R2_LB1      = R1_LB1     + REGION_STRIDE  # 0x15f4  (CORRECTED from doc's 0x1634)
R2_LB2      = R1_LB2     + REGION_STRIDE  # 0x1c34
R2_TRACK    = R1_TRACK   + REGION_STRIDE  # 0x2340
R2_TRAILER  = R1_TRAILER + REGION_STRIDE  # 0x2988

COAT = {0: "Default", 192: "Chestnut", 193: "Black", 199: "Brown", 202: "Bay",
        204: "Dark Gray", 207: "Light Gray", 222: "Special"}


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


def ascii_name(b, o, n=20):
    raw = bytes(b[o:o + n]).split(b"\x00")[0]
    return bytes(c & 0x7f for c in raw).decode("ascii", "replace").strip()


def decode_money_record(b, o, copy2=False):
    rec = {
        "flag0": b[o + 0x00],          # 0,1,2,3,7 — per-record attribute bitfield (semantics open)
        "flag1": b[o + 0x01],          # 0xc0-0xde — grade/type/owner code (semantics open)
        "money": u32(b, o + 0x02),     # prize earnings, the descending sort key
        "name": ascii_name(b, o + 0x0c),
    }
    if copy2:
        rec["sub"] = b[o + 0x08]                 # small per-row counter {0,1,2}
        rec["meta"] = u32(b, o + 0x09) & 0xffffff  # 3 bytes LE -> 0x1680 (5760) constant
    return rec


def fmt_time(cs):
    """centiseconds -> M.SS.hh (matches the in-game RESULT screen)."""
    return f"{cs // 6000}.{(cs % 6000) // 100:02d}.{cs % 100:02d}"


def decode_track_record(b, o):
    # Time @+0x14 is a LE16 in 1/40-second units; cs = raw*5//2 (x2.5). It is NOT an LE32 centisecond
    # value -- reading 4 bytes swallows the separate +0x16 field and runs 2.5x fast on factory saves
    # / returns garbage on real records. See TRACK_RECORD_TIME_PRECISION.md.
    raw = u16(b, o + 0x14)
    cs = raw * 5 // 2
    return {
        "holder": ascii_name(b, o + 0x00),
        "raw": raw,                    # 1/40-second units, as stored
        "timeCs": cs,                  # centiseconds (raw x2.5)
        "time": fmt_time(cs),          # M.SS.hh
        "timeSec": round(cs / 100.0, 2),
        "field16": u16(b, o + 0x16),   # separate 2B field (marker/flags) -- NOT part of the time
        "tail": u32(b, o + 0x18),      # 4B (date-stamp on real records; 0 in factory save)
    }


def decode_region(b, base_hdr, base_lb1, base_lb2, base_track, base_trailer):
    return {
        "checksum16": u16(b, base_hdr),                 # the byte-pair that differs per board
        "lengthWord": u32(b, base_hdr + 0x04),          # = REGION_STRIDE (region payload length)
        "headerDoubledAt": hex(base_hdr + 0x10),
        "headerOk": b[base_hdr:base_hdr + 0x10] == b[base_hdr + 0x10:base_hdr + 0x20],
        "moneyLeaderboard": [decode_money_record(b, base_lb1 + i * LB_REC) for i in range(LB_COUNT)],
        "moneyLeaderboardCopy2": [decode_money_record(b, base_lb2 + i * LB_REC, copy2=True) for i in range(LB_COUNT)],
        "trackRecords": [decode_track_record(b, base_track + i * TR_REC) for i in range(TR_COUNT)],
        "trailerHex": bytes(b[base_trailer:base_trailer + 0x10]).hex(),
        "trailerChecksum16": u16(b, base_trailer + 0x04),  # secondary checksum (0x0a25 = 2597)
    }


def decode_eeprom(e):
    return {
        "sysCrc16": hex(u16(e, 0x00)),
        "gameTag": ascii_name(e, 0x30, 21),               # "DERBY OWNERS CLUB AM3"
        "gameCrcBE": hex(u32(e, 0x2c)),                    # 0xa3100460 family magic
        "befTagAt": "0x03 (BEF0) / 0x15 (mirror)",
        "mirroredHalves": e[0x00:0x12] == e[0x12:0x24] and e[0x2c:0x50] == e[0x54:0x78],
        "raw": e.hex(),
    }


def decode_bookkeeping(b):
    return {
        "header0": {
            "playCounterA": u32(b, 0x00), "playCounterB": u32(b, 0x04),
            "runtimeCounter": u32(b, 0x08),
            "settingFlags": {hex(o): b[o] for o in (0x10, 0x20, 0x30, 0x40, 0x44, 0x4c)},
        },
        # 0x100 is a SECOND distinct bookkeeping header (NOT a verbatim mirror of 0x00)
        "header100": {
            "leadingCounter": u32(b, 0x100),
            "raw": bytes(b[0x100:0x14c]).hex(),
        },
        "header0Hex": bytes(b[0x00:0x50]).hex(),
        "isVerbatimMirror": b[0:12] == b[0x100:0x10c],     # False — documented correction
        "marker": {"value": u32(b, R1_MARKER), "name": ascii_name(b, R1_MARKER + 0x04)},
    }


def master_satellite_diff(cw, cwm):
    diffs = [i for i in range(len(cw)) if cw[i] != cwm[i]]
    lb_id = cw[R1_LB1:R1_LB1 + LB_COUNT * LB_REC] == cwm[R1_LB1:R1_LB1 + LB_COUNT * LB_REC]
    tr_id = cw[R1_TRACK:R1_TRACK + TR_COUNT * TR_REC] == cwm[R1_TRACK:R1_TRACK + TR_COUNT * TR_REC]
    return {
        "differingByteCount": len(diffs),
        "differingOffsets": [hex(d) for d in diffs],
        "leaderboardByteIdentical": lb_id,
        "trackTableByteIdentical": tr_id,
        "note": "Only per-board bookkeeping/checksum/trailer differ; the leaderboard + track payload is shared cabinet-wide.",
    }


def verify(b, e):
    """Re-extract known truths from the bytes; return (checks, all_pass)."""
    c = []
    def chk(name, got, want): c.append((name, got == want, got, want))
    chk("sram size 32768", len(b), 32768)
    chk("eeprom size 128", len(e), 128)
    chk("hdr playCounterA = 3017", u32(b, 0x00), 3017)
    chk("hdr runtimeCounter = 28138", u32(b, 0x08), 28138)
    chk("region1 checksum @0x1f8 = 0x3536", u16(b, 0x1f8), 0x3536)
    chk("region length word @0x1fc = 0x13c4", u32(b, 0x1fc), REGION_STRIDE)
    chk("marker name = Big Shuttle", ascii_name(b, R1_MARKER + 4), "Big Shuttle")
    r0 = decode_money_record(b, R1_LB1)
    chk("LB rec0 name = City Commandant", r0["name"], "City Commandant")
    chk("LB rec0 money = 417935500", r0["money"], 417935500)
    chk("LB rec0 flag0/flag1 = 1/0xcc", (r0["flag0"], r0["flag1"]), (1, 0xcc))
    r49 = decode_money_record(b, R1_LB1 + 49 * LB_REC)
    chk("LB rec50 name = Big Shuttle", r49["name"], "Big Shuttle")
    chk("LB rec50 money = 4628541", r49["money"], 4628541)
    mono = all(u32(b, R1_LB1 + i * LB_REC + 2) >= u32(b, R1_LB1 + (i + 1) * LB_REC + 2) for i in range(49))
    chk("money strictly descending", mono, True)
    c2 = decode_money_record(b, R1_LB2, copy2=True)
    chk("copy2 rec0 meta = 0x1680 (5760)", c2["meta"], 0x1680)
    t0 = decode_track_record(b, R1_TRACK)
    chk("track rec0 holder = Hitmaker", t0["holder"], "Hitmaker")
    chk("track rec0 raw = 3876 (1/40s)", t0["raw"], 3876)
    chk("track rec0 time = 9690cs (1.36.90)", t0["timeCs"], 9690)
    chk("track rec1 raw = 3384 (1/40s)", u16(b, R1_TRACK + TR_REC + 0x14), 3384)
    chk("track rec25 raw = 7956 (1/40s)", u16(b, R1_TRACK + 25 * TR_REC + 0x14), 7956)
    chk("track table ends at 0x15b8", R1_TRACK + TR_COUNT * TR_REC, 0x15b8)
    # region-2 corrected offset: the money key must reappear at 0x15f4 (NOT 0x1634)
    r2 = decode_money_record(b, R2_LB1)
    chk("region2 LB @0x15f4 = City Commandant", r2["name"], "City Commandant")
    chk("region2 LB money = 417935500", r2["money"], 417935500)
    chk("region2 delta = 0x13c4", R2_LB1 - R1_LB1, REGION_STRIDE)
    chk("0x1634 is NOT region2 LB start", decode_money_record(b, 0x1634)["money"] != 417935500, True)
    chk("0x100 header NOT verbatim mirror of 0x00", b[0:12] == b[0x100:0x10c], False)
    chk("eeprom game tag", ascii_name(e, 0x30, 21), "DERBY OWNERS CLUB AM3")
    return c, all(ok for _, ok, _, _ in c)


def main():
    os.makedirs(OUT, exist_ok=True)
    b  = open(SRAM, "rb").read()
    bm = open(SRAM_M, "rb").read()
    e  = open(EEPROM, "rb").read()

    checks, ok = verify(b, e)
    print("=== doc-core NVRAM decode — self-verify ===")
    for name, good, got, want in checks:
        print(f"  [{'PASS' if good else 'FAIL'}] {name}" + ("" if good else f"  (got {got!r}, want {want!r})"))
    print(f"  --> {'ALL PASS' if ok else 'FAILURES PRESENT'} ({sum(g for _,g,_,_ in checks)}/{len(checks)})")

    lastnz = len(b)
    while lastnz > 0 and b[lastnz - 1] == 0: lastnz -= 1

    data = {
        "_about": "doc-core canonical NVRAM (cabinet battery save) decode for Derby Owners Club. "
                  "Schema + byte-exact sample from demul07 derbyocw.sram (World Edition cabinet, satellite board). "
                  "Cabinet hall-of-fame only: money leaderboard + per-course track records + bookkeeping; "
                  "NO player-card stat blocks live here (those are read from the ROM 244-record table by horse name). "
                  "All offsets byte-verified; region-2 LB corrected to 0x15f4 per nvram_VERIFICATION.md.",
        "schema": {
            "files": {
                "eeprom": {"bytes": 128, "role": "JVS serial EEPROM (machine ID + dip settings); byte-identical master vs satellite"},
                "sram": {"bytes": 32768, "usedThrough": "~0x2998", "role": "BBSRAM battery save (bookkeeping + two redundant save regions)"},
            },
            "regionStride": hex(REGION_STRIDE),
            "moneyRecord": {
                "stride": LB_REC, "count": LB_COUNT,
                "fields": {
                    "flag0": "+0x00 u8 (0,1,2,3,7 attribute bitfield; semantics open)",
                    "flag1": "+0x01 u8 (0xc0-0xde grade/type/owner code; semantics open)",
                    "money": "+0x02 LE32 prize earnings (descending sort key)",
                    "sub":   "+0x08 u8 (copy-2 only; small per-row counter 0/1/2)",
                    "meta":  "+0x09 LE24 (copy-2 only; constant 0x1680=5760, season/date candidate)",
                    "name":  "+0x0c 20B ASCII (EN) / EUC-JP (JP), NUL-padded",
                },
            },
            "trackRecord": {
                "stride": TR_REC, "count": TR_COUNT,
                "fields": {
                    "holder": "+0x00 20B name (NUL-padded)",
                    "time":   "+0x14 LE16 in 1/40-second units; cs = raw*5//2 (x2.5). raw 3876 = 9690cs = 1.36.90. NOT LE32 centiseconds.",
                    "field16":"+0x16 2B separate field (marker 0x0762/flags) -- NOT part of the time",
                    "tail":   "+0x18 LE32 (date-stamp on real records; 0 in factory save)",
                },
            },
            "regionOffsets": {
                "region1": {"header": hex(R1_HEADER), "marker": hex(R1_MARKER), "moneyLB1": hex(R1_LB1),
                            "moneyLB2": hex(R1_LB2), "trackTable": hex(R1_TRACK), "trailer": hex(R1_TRAILER)},
                "region2": {"header": hex(R2_HEADER), "moneyLB1": hex(R2_LB1), "moneyLB2": hex(R2_LB2),
                            "trackTable": hex(R2_TRACK), "trailer": hex(R2_TRAILER),
                            "note": "region2 = redundant backup; moneyLB1 CORRECTED to 0x15f4 (doc said 0x1634)"},
            },
            "checksumLocations": {
                "region1": "LE16 @0x1f8 (doubled @0x208); trailer secondary @0x15c4+4",
                "region2": f"LE16 @{hex(R2_HEADER)} (doubled @{hex(R2_HEADER+0x10)}); trailer @{hex(R2_TRAILER+4)}",
                "note": "algorithm not yet reversed; dashboard is read-only so it never recomputes these",
            },
            "openFields": ["flag0", "flag1", "money copy-2 meta (0x1680)", "track tail", "header +0x08 runtime/section counter"],
        },
        "sample": {
            "source": "demul07_280418/nvram/derbyocw.sram (+ derbyocwm.sram, derbyocw.eeprom)",
            "board": "satellite (cw)",
            "sramBytes": len(b), "sramUsedThrough": hex(lastnz),
            "eeprom": decode_eeprom(e),
            "bookkeeping": decode_bookkeeping(b),
            "region1": decode_region(b, R1_HEADER, R1_LB1, R1_LB2, R1_TRACK, R1_TRAILER),
            "region2": decode_region(b, R2_HEADER, R2_LB1, R2_LB2, R2_TRACK, R2_TRAILER),
            "masterSatelliteDiff": master_satellite_diff(b, bm),
        },
        "_verify": {"pass": ok, "checks": [{"name": n, "ok": g, "got": str(gt), "want": str(w)} for n, g, gt, w in checks]},
    }
    path = f"{OUT}/doc_core_nvram.json"
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote {path} ({os.path.getsize(path):,} bytes)")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
