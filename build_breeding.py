#!/usr/bin/env python3
"""doc-core: breeding-stock (sire/dam/mater) extractor for Derby Owners Club.
Reads the 60/56-byte breeding records straight from each ROM -> doc_core_breeding.json.
Layout per _core/areas/breeding-system.md (verified). Self-verifies known horses.

EN (Rev C/D, name-anchored, stride 60): name[24] st u32+24 sp+28 sh+32 ac(+36) composite+44(4B)
    externals+48(6B, 0-15 band) index u16+56.  Sires array + Dams array (separate bases).
JP merged (index-first): derbyo2k stride 60 -> idx u32+0, name EUC-JP+4, st+28 sp+32 sh+36 ac+40 comp+48 ext+52.
                         derbyoc  stride 56 -> idx u32+0, name EUC-JP+4, st+24 sp+28 sh+32 ac+36 comp+44 ext+48.
"""
import json, os, sys, struct
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
ONE = r"C:/Users/johnr/OneDrive - Indigenous Healthcare Advancements/Desktop/John and Pui/Derby Owners Club/DOC-Naomi Roms/Roms"
OUT = r"C:/DerbyOwnersClub/doc-core"

# romaji (same as build_roster)
_KR={'ア':'a','イ':'i','ウ':'u','エ':'e','オ':'o','カ':'ka','キ':'ki','ク':'ku','ケ':'ke','コ':'ko','サ':'sa','シ':'shi','ス':'su','セ':'se','ソ':'so','タ':'ta','チ':'chi','ツ':'tsu','テ':'te','ト':'to','ナ':'na','ニ':'ni','ヌ':'nu','ネ':'ne','ノ':'no','ハ':'ha','ヒ':'hi','フ':'fu','ヘ':'he','ホ':'ho','マ':'ma','ミ':'mi','ム':'mu','メ':'me','モ':'mo','ヤ':'ya','ユ':'yu','ヨ':'yo','ラ':'ra','リ':'ri','ル':'ru','レ':'re','ロ':'ro','ワ':'wa','ヲ':'wo','ン':'n','ガ':'ga','ギ':'gi','グ':'gu','ゲ':'ge','ゴ':'go','ザ':'za','ジ':'ji','ズ':'zu','ゼ':'ze','ゾ':'zo','ダ':'da','ヂ':'ji','ヅ':'zu','デ':'de','ド':'do','バ':'ba','ビ':'bi','ブ':'bu','ベ':'be','ボ':'bo','パ':'pa','ピ':'pi','プ':'pu','ペ':'pe','ポ':'po','ヴ':'vu'}
_SM={'ァ':'a','ィ':'i','ゥ':'u','ェ':'e','ォ':'o','ャ':'ya','ュ':'yu','ョ':'yo'}
def romaji(s):
    out,prev="",""; a=list(s)
    for i,ch in enumerate(a):
        if ch=='ー': out+=prev or "-"; continue
        if ch=='ッ':
            nx=_KR.get(a[i+1]) if i+1<len(a) else None
            if nx: out+=nx[0]
            continue
        if ch in _SM:
            sm=_SM[ch]
            if ch in 'ャュョ': out=out[:-1] if out and out[-1]=='i' else out
            elif out and out[-1] in 'aiueo': out=out[:-1]
            out+=sm; prev=sm[-1]; continue
        b=_KR.get(ch)
        if b: out+=b; prev=b[-1]
        else: out+=ch; prev=""
    return out

def band(v): return '◎' if v>=13 else '○' if v>=9 else '△' if v>=5 else '×' if v>=1 else '·'
def u32(d,o): return struct.unpack_from('<I', d, o)[0]

def rec_en(d, o):  # name-anchored EN record at absolute o
    raw=d[o:o+24].split(b'\x00')[0].replace(b'\xa1', b' ')  # 0xA1 = in-game fullwidth space
    name=raw.decode('latin1').strip()
    ext=[d[o+48+i] for i in range(6)]
    return {"name":name, "st":u32(d,o+24)&0xff, "sp":u32(d,o+28)&0xff, "sh":u32(d,o+32)&0xff,
            "ac":u32(d,o+36)&0xff, "composite":list(d[o+44:o+48]),
            "externals":dict(zip(["start","corner","oob","competing","tenacious","spurt"],ext)),
            "bands":"".join(band(x) for x in ext), "index":struct.unpack_from('<H',d,o+56)[0]}

def rec_jp(d, o, stride):  # index-first JP record
    nm_off=o+4
    name=d[nm_off:nm_off+(20 if stride==60 else 16)].split(b'\x00')[0]
    try: name=name.decode('euc-jp')
    except Exception: name=name.decode('euc-jp','replace')
    st_o = o+28 if stride==60 else o+24
    comp_o = o+48 if stride==60 else o+44
    ext_o  = o+52 if stride==60 else o+48
    ext=[d[ext_o+i] for i in range(6)]
    return {"name":None,"nameJP":name,"romaji":romaji(name),
            "st":u32(d,st_o)&0xff,"sp":u32(d,st_o+4)&0xff,"sh":u32(d,st_o+8)&0xff,"ac":d[st_o+12],
            "composite":list(d[comp_o:comp_o+4]),
            "externals":dict(zip(["start","corner","oob","competing","tenacious","spurt"],ext)),
            "bands":"".join(band(x) for x in ext), "index":u32(d,o)}

def read_en_pool(d, sire_base, dam_base, cap=300):
    """Sire array is immediately followed by the dam array; the +56 index runs 1..N continuously.
    Read while index==k+1 (self-bounding); split kind at dam_base."""
    out=[]
    for k in range(cap):
        o=sire_base+60*k; r=rec_en(d,o)
        if r["index"]!=k+1: break   # +56 index runs 1..N continuously; sole reliable bound
        r["kind"]="sire" if o < dam_base else "dam"
        out.append(r)
    sires=[r for r in out if r["kind"]=="sire"]; dams=[r for r in out if r["kind"]=="dam"]
    return sires, dams

def read_jp_array(d, base, stride, cap=200):
    out=[]
    for k in range(cap):
        o=base+stride*k; r=rec_jp(d,o,stride)
        if r["index"]==0 or r["index"]>500 or not r["nameJP"]: break
        out.append(r)
    return out

CFG={
 "drbyocwc":{"rom":f"{ONE}/drbyocwc/epr-22336c.ic22","en":True,"sire":0x10BF1C,"dam":0x10D2CC,"tag":"Rev C"},
 "derbyocw":{"rom":f"{ONE}/derbyocw/epr-22336d.ic22","en":True,"sire":0x10D264,"dam":0x10E614,"tag":"Rev D"},
 "derbyo2k":{"rom":f"{ONE}/derbyo2k/epr-22284a.ic22","en":False,"mater":0x11106C,"stride":60,"tag":"DOC 2000"},
 "derbyoc": {"rom":f"{ONE}/derbyoc/epr-22099b.ic22","en":False,"mater":0x0F9680,"stride":56,"tag":"DOC '99"},
}
def main():
    os.makedirs(OUT,exist_ok=True)
    data={"_about":"doc-core breeding-stock pool (sires/dams EN, merged mater JP); externals 0-15 band ×△○◎; ac=dirt/course aptitude 0-255","versions":{}}
    for key,c in CFG.items():
        d=open(c["rom"],"rb").read()
        if c["en"]:
            sires,dams=read_en_pool(d,c["sire"],c["dam"])
            pool=sires+dams
            data["versions"][key]={"tag":c["tag"],"kind":"EN-split","sires":len(sires),"dams":len(dams),"count":len(pool),"pool":pool}
            ex=pool[0]
            print(f"  {key:9} {c['tag']:9} {len(sires)} sires + {len(dams)} dams = {len(pool)} | #1 {ex['name']}: st{ex['st']} sp{ex['sp']} sh{ex['sh']} ac{ex['ac']} ext{list(ex['externals'].values())} idx{ex['index']}")
        else:
            pool=read_jp_array(d,c["mater"],c["stride"])
            data["versions"][key]={"tag":c["tag"],"kind":"JP-merged","count":len(pool),"pool":pool}
            ex=pool[0]
            print(f"  {key:9} {c['tag']:9} {len(pool)} mater | #1 {ex['nameJP']} ({ex['romaji']}): st{ex['st']} sp{ex['sp']} sh{ex['sh']} ac{ex['ac']} ext{list(ex['externals'].values())} idx{ex['index']}")
    path=f"{OUT}/doc_core_breeding.json"
    json.dump(data,open(path,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print(f"\nwrote {path} ({os.path.getsize(path):,} bytes)")
    # verify known horses
    print("=== verify ===")
    rc=data["versions"]["drbyocwc"]["pool"][0]
    ok1 = rc["name"]=="Maple Syrup" and rc["st"]==39 and rc["sp"]==19 and rc["sh"]==34 and rc["ac"]==240 and list(rc["externals"].values())==[15,3,6,10,4,12]
    print(f"  Rev C sire#1 Maple Syrup st39/sp19/sh34/ac240/ext[15,3,6,10,4,12]: {'PASS' if ok1 else 'FAIL -> '+json.dumps(rc,ensure_ascii=False)}")
    o2k=data["versions"]["derbyo2k"]["pool"][0]
    ok2 = o2k["nameJP"]=="トロットサンダー" and o2k["st"]==35 and o2k["ac"]==217
    print(f"  o2k mater#1 トロットサンダー st35/ac217: {'PASS' if ok2 else 'FAIL -> '+json.dumps(o2k,ensure_ascii=False)}")

if __name__=="__main__": main()
