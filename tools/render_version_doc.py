#!/usr/bin/env python3
"""Render per-version Markdown architecture masters from the JSON specs.

Source of truth is the JSON. These Markdown files are generated; do not edit
them by hand. Re-run after any spec change.

Usage:
    python tools/render_version_doc.py            # render all four
    python tools/render_version_doc.py rev-c      # render one
"""
import json
import sys
from datetime import date
from pathlib import Path

VERSIONS = Path(__file__).resolve().parent.parent / "versions"
OUT = VERSIONS / "_generated"
SPECS = ["rev-c", "rev-d", "doc-2000", "doc-99"]
TABLE_ORDER = ["roster", "names", "sire", "dam", "g1", "tracks",
               "foods", "strings", "racePace", "personality"]


def load(name):
    return json.loads((VERSIONS / name).read_text(encoding="utf-8"))


def hexint(s):
    return int(s, 16)


def fmt_addr(entry, runtime_base):
    off = entry.get("offset", {})
    val = off.get("value")
    frame = off.get("frame")
    if val is None:
        return "not located", ""
    if frame == "file":
        rt = f"0x{hexint(val) + runtime_base:08x}"
        return val, rt
    return f"{val} ({frame})", ""


def yn(b):
    return "yes" if b else "no"


def ynn(b):
    return "n/a" if b is None else ("yes" if b else "no")


def count_str(c):
    v = c.get("value")
    base = "unknown" if v is None else str(v)
    return base if c.get("verified") else f"{base} (unverified)"


def render(spec, shared):
    rb = hexint(shared["addressRule"]["runtimeBase"])
    i = spec["identity"]
    L = []
    L.append(f"# {i['label']} ({i['tag']})")
    L.append("")
    L.append(f"> GENERATED FILE, do not edit. Source: `{spec['id']}.json`. "
             f"Regenerate with `python tools/render_version_doc.py {spec['id']}`.")
    L.append("")

    L.append("## Identity")
    L.append("")
    L.append("| Field | Value |")
    L.append("|---|---|")
    L.append(f"| Region | {i['region']} |")
    L.append(f"| MAME set | `{i['mameSetname']}` |")
    L.append(f"| Program ROM | `{i['programRom']}` |")
    L.append(f"| ROM size | {i['romSize']:,} bytes (0x{i['romSize']:x}) |")
    L.append(f"| SHA-256 | `{i['sha256']}` |")
    L.append(f"| Signature @ {i['signature']['offset']} | `{i['signature']['bytes']}` |")
    L.append(f"| NAOMI build date | {i['naomiHeader']['buildDate']} |")
    L.append(f"| NAOMI game code | {i['naomiHeader']['gameCode']} |")
    derived = i["derivedFrom"] or "none (original mask ROM)"
    L.append(f"| Derived from | {derived} |")
    L.append("")

    L.append("## Confirm your ROM")
    L.append("")
    L.append("Before trusting any offset below, confirm your dump matches:")
    L.append("")
    L.append("```python")
    L.append("import zipfile, hashlib")
    L.append(f'z = zipfile.ZipFile("{i["mameSetname"]}.zip")')
    L.append('d = next(z.read(n) for n in z.namelist()')
    L.append('         if n.lower().endswith(".ic22") and z.getinfo(n).file_size == 4194304)')
    L.append('print(hashlib.sha256(d).hexdigest())   # expect identity.sha256')
    L.append('print(d[0x8000:0x8010].hex())          # expect identity.signature.bytes')
    L.append("```")
    L.append("")

    e = spec["encoding"]
    L.append("## Encoding")
    L.append("")
    sep = e.get("lineSeparator") or "n/a"
    L.append(f"Names: `{e['names']}`. Strings: `{e['strings']}`. Line separator: {sep}.")
    L.append("")

    rf = spec["recordFormats"]
    L.append("## Record formats")
    L.append("")
    L.append("| Structure | Width | Count |")
    L.append("|---|---|---|")
    L.append(f"| Roster record | {rf['roster']['width']} bytes | {count_str(rf['roster']['count'])} |")
    L.append(f"| Name entry | stride {rf['nameTable']['stride']} | aligns to roster index |")
    bw = rf['breeding']['width']
    L.append(f"| Breeding mater | {bw if bw is not None else 'unknown'} bytes | {count_str(rf['breeding']['count'])} |")
    fw = rf['food']['width']
    L.append(f"| Food record | {fw if fw is not None else 'unknown'} bytes | {count_str(rf['food']['count'])} |")
    L.append("")

    L.append("## Data tables")
    L.append("")
    L.append("File offsets are raw ROM positions. Runtime is where the byte lands once "
             "the cart is DMAed into RAM (file + "
             f"{shared['addressRule']['runtimeBase']}).")
    L.append("")
    L.append("| Table | File offset | Runtime | Access | Verified |")
    L.append("|---|---|---|---|---|")
    notes = []
    for key in TABLE_ORDER:
        t = spec["tables"][key]
        f_addr, rt_addr = fmt_addr(t, rb)
        L.append(f"| {key} | {f_addr} | {rt_addr or '-'} | {t.get('access', '-')} | {yn(t['verified'])} |")
        if t.get("note"):
            notes.append(f"- **{key}:** {t['note']} (source: {t['source']})")
    L.append("")
    if notes:
        L.append("Notes:")
        L.append("")
        L.extend(notes)
        L.append("")

    c = spec["courses"] if "courses" in spec else None
    if c:
        L.append("## Courses")
        L.append("")
        L.append(f"Total courses: {count_str(c['total'])}. G1 races: {count_str(c['g1'])}.")
        L.append("")

    cd = spec["cards"]
    L.append("## Player card")
    L.append("")
    marker = cd["marker"] or "none"
    pb = cd["payloadBytes"]
    pb_s = f"{pb} bytes" if pb is not None else "see JP card spec"
    L.append(f"Type: {cd['type']}. Marker: {marker}. Payload: {pb_s}.")
    if cd.get("note"):
        L.append("")
        L.append(cd["note"])
    L.append("")

    dv = spec["divergence"]
    L.append("## Divergence and patch safety")
    L.append("")
    rid = dv["rosterIdenticalTo"]
    L.append(f"Roster stat records identical to: {rid if rid else 'none'}.")
    L.append(f"Roster renamed vs World Edition baseline: {yn(dv['renamedRoster'])}.")
    fm = dv["foodMeta"]
    L.append(f"Food meta: beer {ynn(fm['beer'])}, banana {ynn(fm['banana'])}.")
    if dv.get("note"):
        L.append("")
        L.append(f"> {dv['note']}")
    L.append("")

    ar = shared["addressRule"]
    L.append("## Appendix: shared constants")
    L.append("")
    L.append(f"- Platform: {shared['platform']['system']}, "
             f"{shared['platform']['cpu']}, {shared['platform']['endianness']}-endian, "
             f"{shared['platform']['cabinet']}.")
    L.append(f"- Address rule: {ar['fileToRuntime']}; {ar['runtimeToFile']}; {ar['fileToGhidra']}.")
    L.append(f"- {ar['warning']}")
    L.append(f"- Literal-pool access: {shared['pointerConventions']['literalPool']}")
    L.append(f"- Computed access: {shared['pointerConventions']['computed']}")
    L.append(f"- Card: {shared['card']['payloadBytes']}-byte payload, "
             f"{shared['card']['layout']}. Whole-card checksum: {yn(shared['card']['wholeCardChecksum'])}.")
    L.append(f"- NVRAM ({shared['nvram']['type']}): stores {shared['nvram']['stores']}; "
             f"does not store {shared['nvram']['doesNotStore']}.")
    L.append("")
    L.append(f"_Generated {date.today().isoformat()} from `{spec['id']}.json` and `_shared.json`._")
    L.append("")
    return "\n".join(L)


def main():
    shared = load("_shared.json")
    OUT.mkdir(exist_ok=True)
    targets = sys.argv[1:] or SPECS
    for t in targets:
        t = t.replace(".json", "")
        if t not in SPECS:
            print(f"skip: unknown version '{t}' (known: {', '.join(SPECS)})")
            continue
        spec = load(f"{t}.json")
        md = render(spec, shared)
        (OUT / f"{t}.md").write_text(md, encoding="utf-8")
        print(f"wrote versions/_generated/{t}.md ({len(md):,} chars)")


if __name__ == "__main__":
    main()
