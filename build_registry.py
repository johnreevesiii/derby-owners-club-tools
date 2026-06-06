#!/usr/bin/env python3
"""doc-core: version registry. Extracts the edit-proof 0x8000 build signature + size +
verified table offsets for all 4 ROMs -> doc_core_versions.json (used by the fingerprinter)."""
import json, os, sys, hashlib
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
ONE = r"C:/Users/johnr/OneDrive - Indigenous Healthcare Advancements/Desktop/John and Pui/Derby Owners Club/DOC-Naomi Roms/Roms"
OUT = r"C:/DerbyOwnersClub/doc-core"

V = {
 "drbyocwc": {"label":"World Edition (Rev C)","tag":"Rev C","rom":f"{ONE}/drbyocwc/epr-22336c.ic22","epr":"epr-22336c.ic22","fmt":32,"stat":0x108E03,"names":0x10AD50,"sire":0x10BF1C,"dam":0x10D2CC,"g1":0x0C6CA0,"tracks":0x0C6940,"nameEnc":"ascii"},
 "derbyocw": {"label":"World Edition EX (Rev D)","tag":"Rev D","rom":f"{ONE}/derbyocw/epr-22336d.ic22","epr":"epr-22336d.ic22","fmt":32,"stat":0x10A14B,"names":0x10C098,"sire":0x10D264,"dam":0x10E614,"g1":0x0C65C0,"tracks":0x0C6260,"nameEnc":"ascii"},
 "derbyo2k": {"label":"DOC 2000 (JP)","tag":"DOC 2000","rom":f"{ONE}/derbyo2k/epr-22284a.ic22","epr":"epr-22284a.ic22","fmt":32,"stat":0x10AD1B,"names":0x10CC68,"sire":None,"dam":None,"g1":None,"tracks":None,"nameEnc":"euc-jp"},
 "derbyoc":  {"label":"DOC Original / '99 (JP)","tag":"DOC '99","rom":f"{ONE}/derbyoc/epr-22099b.ic22","epr":"epr-22099b.ic22","fmt":28,"stat":0x0F6902,"names":0xF8480,"sire":0xF96CC,"dam":None,"g1":None,"tracks":None,"nameEnc":"euc-jp"},
}
reg = {"_about":"doc-core version registry: 0x8000 build signature (edit-proof) + size + verified offsets", "sigOffset":"0x8000", "versions":{}}
for key,c in V.items():
    d = open(c["rom"],"rb").read()
    sig = d[0x8000:0x8010].hex()
    reg["versions"][key] = {
        "label":c["label"],"tag":c["tag"],"epr":c["epr"],"size":len(d),
        "sig8000": sig, "sig8: sha": hashlib.sha256(d).hexdigest()[:16],
        "recordFmt":c["fmt"], "nameEnc":c["nameEnc"],
        "offsets": {k:(hex(c[k]) if c[k] is not None else None) for k in ("stat","names","sire","dam","g1","tracks")},
    }
    print(f"  {key:9} {c['tag']:9} size={len(d)} sig@0x8000={sig[:16]}…")
path=f"{OUT}/doc_core_versions.json"
json.dump(reg, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {path}")
# collision check
sigs=[v["sig8000"][:16] for v in reg["versions"].values()]
print("all 8-byte sigs distinct:", len(set(sigs))==len(sigs))
