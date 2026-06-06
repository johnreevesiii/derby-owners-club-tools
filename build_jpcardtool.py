#!/usr/bin/env python3
"""doc-core tool #10: JP Kana Card Tooling (editor + EN twin cross-ref + trailer/lead-id probe).

Builds jp-card-tool.html: starts from a real captured JP (DOC 2000) identity card template,
lets you edit the kana name/sire/dam (byte-safe same-length rename, like doc_card.py), cross-
references the kana name to its EN stat-twin via the breeding pool, and GENERATES A PROBE PACK:
a .zip of candidate cards sweeping the unknown 0x43-0x44 trailer and/or 0x25-0x27 lead-id, so you
can load them on the cabinet to discover which it accepts (the open JP-create recipe).

Provenance: jp-card.md (kana table, identity/pedigree layout, 0x25-0x27 lead-id, 0x43-0x44 trailer),
doc_card.py JP codec, breeding-system.md JP<->EN twin map. JP card CREATE for a never-seen horse is
the unsolved frontier; this tool is the harness to crack it. HARDWARE-GATED (needs cabinet testing).
"""
import json, io
import sys
sys.path.insert(0, r"C:/DerbyOwnersClub/doc-core")
import doc_card

OUT = r"C:/DerbyOwnersClub/doc-core"
TEMPLATE = r"C:/DerbyOwnersClub/_jp_re/captures/frozen1/derbyo2k_sat1.card"
raw = open(TEMPLATE, "rb").read()
d = doc_card.decode(raw)
assert d["kind"] == "jp", d["kind"]
TPL_HEX = raw.hex()

# kana decode table (id-ordered, matches doc_card JP_TABLE) -> JS will invert it
JPT = {str(k): v for k, v in doc_card.JP_TABLE.items()}

# kana -> EN twin crossref via breeding pool
b = json.load(io.open(f"{OUT}/doc_core_breeding.json", encoding="utf-8"))
def tup(r): return "%d_%d_%d_%d" % (r["st"], r["sp"], r["sh"], r["ac"])
en = {}
for vk in ("drbyocwc", "derbyocw"):
    for r in b["versions"][vk]["pool"]:
        if r.get("name"):
            en.setdefault(tup(r), set()).add(r["name"])
xref = {}  # nameJP -> {romaji, en:[...], st,sp,sh,ac}
for vk in ("derbyo2k", "derbyoc"):
    for r in b["versions"][vk]["pool"]:
        nj = r.get("nameJP")
        if not nj:
            continue
        xref[nj] = {"romaji": r.get("romaji"), "st": r["st"], "sp": r["sp"], "sh": r["sh"],
                    "ac": r["ac"], "en": sorted(en.get(tup(r), []))}

DATA = json.dumps({"tpl": TPL_HEX, "jpt": JPT, "xref": xref,
                   "tplName": d["name"], "tplSire": d["sire"], "tplDam": d["dam"],
                   "leadId": d["leadId"], "trailer": d["trailer"]}, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC JP Kana Card Tool</title>
<style>
 body{margin:0;font:13px/1.45 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:10px 18px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:18px;color:#eae8e2}.sub{color:#7fb0bd;font-size:12px;font-weight:400}
 .wrap{padding:14px 18px;max-width:980px}
 .card{background:#08202a;border:1px solid #143b48;border-radius:8px;padding:12px;margin:10px 0}
 .card h3{margin:.2em 0;color:#eae8e2;font-size:14px}
 label{color:#9cc;font-size:12px}
 input,select{background:#06303a;color:#fff;border:1px solid #2a5666;border-radius:5px;padding:4px 8px;font-size:14px}
 input.kana{width:260px;font-size:18px}
 button{background:#014b50;color:#cfe;border:0;border-radius:5px;padding:6px 12px;cursor:pointer;margin:2px}
 button.act{background:#b75527;color:#fff}button:disabled{opacity:.4;cursor:not-allowed}
 .pal button{font-size:18px;min-width:34px;padding:3px 0;margin:1px;background:#06303a}
 .pal{max-width:560px;line-height:1.1}
 .ok{color:#7fdca0}.warn{color:#ffb27f}.bad{color:#ff8a8a}.muted{color:#6f9aa6}
 .note{color:#7fb0bd;font-size:12px;margin:6px 0}
 .mono{font-family:Consolas,monospace}
 table{border-collapse:collapse;margin-top:6px}th,td{border:1px solid #143b48;padding:3px 9px;font-size:12px;text-align:left}th{background:#0a242e;color:#9cc}
 .hex{font-family:Consolas,monospace;font-size:11px;color:#9fb4bb;white-space:pre-wrap;word-break:break-all;background:#06181f;padding:6px;border-radius:5px}
</style></head><body>
<header><h1>&#127183; DOC JP Kana Card Tool <span class="sub">tool #10 &middot; kana editor + EN twin + trailer/lead-id probe</span></h1></header>
<div class="wrap">
 <div class="note">Starts from a real captured DOC&nbsp;2000 identity card. Edit the kana name/sire/dam (<b>same length</b> = byte-safe; different length shifts the PAD/trailer and is flagged). JP cards carry identity + pedigree only &mdash; stats live cabinet-side. The <b>0x25-0x27 lead-id</b> and <b>0x43-0x44 trailer</b> recipe for a brand-new horse is unsolved; use the <b>Probe Pack</b> to generate candidate cards and test them on the cabinet.</div>

 <div class="card"><h3>Identity</h3>
  <div><label>Horse name (kana)</label><br><input class="kana" id="name"></div>
  <div style="margin-top:6px"><label>Sire (kana)</label> <input class="kana" id="sire" style="width:200px"> <label>Dam (kana)</label> <input class="kana" id="dam" style="width:200px"></div>
  <div id="nameStatus" class="note"></div>
  <div class="pal" id="pal"></div>
  <div class="note">Palette inserts into the focused field. Backspace/typing also work if your IME outputs katakana.</div>
 </div>

 <div class="card"><h3>EN stat-twin cross-reference</h3><div id="xref" class="muted">type a known mater kana name to see its English equivalent + stats</div></div>

 <div class="card"><h3>Export edited card</h3>
  <button id="expCard" class="act">&#128190; Download .card</button>
  <span id="expStat" class="muted"></span>
  <div class="hex" id="hexout" style="margin-top:8px"></div>
 </div>

 <div class="card"><h3>&#128270; Probe Pack &mdash; crack the create recipe</h3>
  <div class="note">Generates a ZIP of candidate cards (your current identity) with the unknown bytes swept. Load each on the cabinet; the one it accepts reveals the scheme. Original card values: lead-id <span class="mono" id="origLead"></span>, trailer <span class="mono" id="origTrail"></span>.</div>
  <div>
   <label><input type="checkbox" id="sweepTrail" checked> Sweep trailer 0x43/0x44</label>
   &nbsp; <label>step <select id="trailStep"><option>64</option><option selected>32</option><option>16</option><option>8</option></select></label>
   &nbsp;&nbsp; <label><input type="checkbox" id="sweepLead"> Sweep lead-id 0x25-0x27 (low byte)</label>
  </div>
  <div style="margin-top:6px"><button id="genPack" class="act">Generate probe pack (.zip)</button> <span id="packStat" class="muted"></span></div>
  <div class="note">Always includes the key candidates: zeroed, 0xFF, and the original. Keep the count sane (a full 65k sweep is not useful for hand-testing).</div>
 </div>
</div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s);
const TPL=Uint8Array.from(D.tpl.match(/../g).map(b=>parseInt(b,16)));
const JPT={};for(const k in D.jpt)JPT[+k]=D.jpt[k];
const JREV={};for(const k in JPT)JREV[JPT[k]]=+k;
const PAD=0x7d, NAMEOFF=0x28;
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}

// decode the 3 kana fields from a card (walk 0x28.., PAD-separated)
function readFields(c){let i=NAMEOFF,f=[];for(let n=0;n<3;n++){let s='',st=i;while(i<0x45&&c[i]!==PAD){s+=(JPT[c[i]]||'');i++;}f.push({text:s,start:st,len:i-st});while(i<0x45&&c[i]===PAD)i++;}return f;}
function encName(str){const out=[];for(const ch of str){if(!(ch in JREV))return null;out.push(JREV[ch]);}return out;}

let cur=TPL.slice();
function loadFromCard(c){const f=readFields(c);$('#name').value=f[0].text;$('#sire').value=f[1].text;$('#dam').value=f[2].text;}
loadFromCard(cur);
$('#origLead').textContent=D.leadId.map(x=>x.toString(16).padStart(2,'0')).join(' ');
$('#origTrail').textContent=D.trailer.map(x=>x.toString(16).padStart(2,'0')).join(' ');

// build current card bytes from template + edited fields (same-length overlay; flag mismatches)
function buildCard(){
 const out=TPL.slice();const f=readFields(TPL);
 const want=[$('#name').value,$('#sire').value,$('#dam').value];
 let warn=[];
 for(let idx=0;idx<3;idx++){
  if(want[idx]===f[idx].text)continue;
  const enc=encName(want[idx]);
  if(enc===null){warn.push(['name','sire','dam'][idx]+': unmapped kana');continue;}
  if(enc.length!==f[idx].len){warn.push(['name','sire','dam'][idx]+': length '+enc.length+'≠ original '+f[idx].len+' (shifts layout — not byte-safe)');}
  for(let j=0;j<enc.length&&f[idx].start+j<0x45;j++)out[f[idx].start+j]=enc[j];
 }
 return {bytes:out,warn};
}
function refresh(){
 const {bytes,warn}=buildCard();cur=bytes;
 $('#nameStatus').innerHTML=warn.length?'<span class="warn">'+warn.map(esc).join('; ')+'</span>':'<span class="ok">byte-safe (all fields same length as template)</span>';
 $('#hexout').textContent=[...bytes].map(b=>b.toString(16).padStart(2,'0')).join(' ');
 // xref on name
 const nm=$('#name').value;const x=D.xref[nm];
 $('#xref').innerHTML = x ? ('<b>'+esc(nm)+'</b> '+(x.romaji?'('+esc(x.romaji)+')':'')+' &mdash; <span class="mono">ST '+x.st+' / SP '+x.sp+' / SH '+x.sh+' / dirt '+x.ac+'</span>'+(x.en.length?' &#8596; EN: <span class="ok">'+x.en.map(esc).join(', ')+'</span>':' <span class="muted">(no EN twin)</span>'))
   : '<span class="muted">"'+esc(nm)+'" not a known breeding-pool mater (custom name)</span>';
}
['name','sire','dam'].forEach(id=>$('#'+id).addEventListener('input',refresh));
// palette
let focusEl=$('#name');['name','sire','dam'].forEach(id=>$('#'+id).addEventListener('focus',e=>focusEl=e.target));
const order=[];for(let k=0;k<256;k++)if(JPT[k])order.push(JPT[k]);
$('#pal').innerHTML=order.map(ch=>'<button data-ch="'+ch+'">'+ch+'</button>').join('');
$('#pal').querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{const el=focusEl;el.value+=btn.dataset.ch;el.focus();refresh();}));

function dl(data,name){const b=new Blob([data],{type:'application/octet-stream'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;a.click();}
$('#expCard').addEventListener('click',()=>{const {bytes,warn}=buildCard();dl(bytes,'jp_card.card');$('#expStat').innerHTML=warn.length?'<span class="warn">exported (with layout warnings)</span>':'<span class="ok">exported (byte-safe)</span>';});

// ---- minimal store-only ZIP (with CRC32) for the probe pack ----
const CRCT=(()=>{const t=[];for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=(c&1)?(0xEDB88320^(c>>>1)):(c>>>1);t[n]=c>>>0;}return t;})();
function crc32(buf){let c=0xFFFFFFFF;for(let i=0;i<buf.length;i++)c=CRCT[(c^buf[i])&0xFF]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
function zip(files){ // files=[{name,data(Uint8Array)}]
 let parts=[],central=[],off=0;const enc=new TextEncoder();
 function u16(v){return [v&0xFF,(v>>>8)&0xFF];}function u32(v){return [v&0xFF,(v>>>8)&0xFF,(v>>>16)&0xFF,(v>>>24)&0xFF];}
 files.forEach(f=>{const nm=enc.encode(f.name);const crc=crc32(f.data);
  const lh=[].concat(u32(0x04034b50),u16(20),u16(0),u16(0),u16(0),u16(0),u32(crc),u32(f.data.length),u32(f.data.length),u16(nm.length),u16(0));
  parts.push(Uint8Array.from(lh),nm,f.data);
  const ch=[].concat(u32(0x02014b50),u16(20),u16(20),u16(0),u16(0),u16(0),u16(0),u32(crc),u32(f.data.length),u32(f.data.length),u16(nm.length),u16(0),u16(0),u16(0),u16(0),u32(0),u32(off));
  central.push(Uint8Array.from(ch),nm);
  off+=lh.length+nm.length+f.data.length;
 });
 const cstart=off;let clen=0;central.forEach(p=>clen+=p.length);
 const eocd=Uint8Array.from([].concat(u32(0x06054b50),u16(0),u16(0),u16(files.length),u16(files.length),u32(clen),u32(cstart),u16(0)));
 const all=[...parts,...central,eocd];let total=0;all.forEach(p=>total+=p.length);
 const out=new Uint8Array(total);let p=0;all.forEach(x=>{out.set(x,p);p+=x.length;});return out;
}
$('#genPack').addEventListener('click',()=>{
 const base=buildCard().bytes;const files=[];const seen=new Set();
 function add(name,mut){const c=base.slice();mut(c);const key=name;if(seen.has(key))return;seen.add(key);files.push({name,data:c});}
 // key candidates
 add('trailer_original.card',c=>{});
 add('trailer_0000.card',c=>{c[0x43]=0;c[0x44]=0;});
 add('trailer_ffff.card',c=>{c[0x43]=0xff;c[0x44]=0xff;});
 if($('#sweepTrail').checked){const step=+$('#trailStep').value;for(let lo=0;lo<256;lo+=step){add('trail_'+D.trailer[1].toString(16).padStart(2,'0')+lo.toString(16).padStart(2,'0')+'.card',c=>{c[0x43]=lo;c[0x44]=D.trailer[1];});}}
 if($('#sweepLead').checked){const step=+$('#trailStep').value;for(let lo=0;lo<256;lo+=step){add('lead_'+lo.toString(16).padStart(2,'0')+'.card',c=>{c[0x25]=lo;});}}
 const z=zip(files);dl(z,'jp_probe_pack.zip');
 $('#packStat').innerHTML='<span class="ok">'+files.length+' candidate cards in jp_probe_pack.zip</span>';
});
refresh();
</script></body></html>"""
html = HTML.replace("__DATA__", DATA)
open(f"{OUT}/jp-card-tool.html", "w", encoding="utf-8").write(html)
print("wrote jp-card-tool.html (%d bytes), xref names=%d" % (len(html), len(xref)))
