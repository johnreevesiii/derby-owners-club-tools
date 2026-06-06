#!/usr/bin/env python3
"""doc-core consumer: ROM Fingerprinter (Tier-1 #4). Embeds the version registry; the HTML
takes a dropped .ic22, matches the 0x8000 build signature, reports the version + offsets, and
PROVES it by decoding horse #1 (name + stats) live from the dropped bytes."""
import json, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
reg = json.dumps(json.load(open(f"{OUT}/doc_core_versions.json", encoding="utf-8")), ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC ROM Fingerprinter — doc-core</title>
<style>
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:14px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527} header h1{margin:0;font-size:18px} .sub{color:#bcd;font-size:12px}
 .wrap{max-width:760px;margin:24px auto;padding:0 18px}
 #drop{border:2px dashed #2a5560;border-radius:12px;padding:42px;text-align:center;color:#9ab;cursor:pointer}
 #drop.hot{border-color:#b75527;background:#10323e}
 .card{background:#0a242e;border:1px solid #143;border-radius:10px;padding:16px 18px;margin-top:18px}
 .ok{color:#9fe0b0;font-weight:700;font-size:20px} .bad{color:#f39;font-weight:700;font-size:18px}
 table{border-collapse:collapse;width:100%;margin-top:8px} td{padding:5px 8px;border-bottom:1px solid #143}
 td.k{color:#9cc;white-space:nowrap;width:170px} code{background:#0e2f3c;padding:1px 6px;border-radius:4px}
 .romaji{color:#9cc;font-style:italic} .hint{color:#9ab;font-size:12px;margin-top:6px}
</style></head><body>
<header><h1>🔎 DOC ROM Fingerprinter <span class="sub">doc-core · identify any DOC program ROM, then prove it by decoding horse #1</span></h1></header>
<div class="wrap">
 <div id="drop">Drop a DOC program <code>.ic22</code> here, or click to choose.<br>
   <span class="hint">Reads only the build signature at 0x8000 + horse #1. Nothing leaves your browser.</span></div>
 <input type="file" id="f" accept=".ic22,.bin" style="display:none">
 <div id="out"></div>
</div>
<script>
const REG=__REG__;
const FIELDS={32:{hiddenA:1,id:2,dirt:5,grade:8,start:9,corner:10,oob:11,comp:12,tenac:13,spurt:14,hiddenB:16,style:21,coat:22,stam:29,speed:30,sharp:31},
              28:{hiddenA:0,id:1,dirt:4,grade:7,start:9,corner:10,oob:11,comp:12,tenac:13,spurt:14,hiddenB:17,style:18,coat:19,stam:24,speed:25,sharp:26}};
const COAT={0:"Default",192:"Chestnut",193:"Black",199:"Brown",202:"Bay",204:"Dark Gray",207:"Light Gray",222:"Special"};
const GRADE={0:"Ungraded",1:"G3",2:"G2",3:"G1"}, STYLE={0:"Front-runner",1:"Start dash",2:"Last spurt",3:"Stretch-runner",7:"Almighty"};
const $=s=>document.querySelector(s);
const hexAt=(u8,o,n)=>[...u8.slice(o,o+n)].map(b=>b.toString(16).padStart(2,'0')).join('');
function readName(u8,base,enc){ const slot=u8.slice(base,base+18); let end=slot.indexOf(0); if(end<0)end=18;
  const raw=slot.slice(0,end);
  if(enc==='ascii') return String.fromCharCode(...[...raw].map(b=>b&0x7f)).trim();
  try{return new TextDecoder('euc-jp').decode(raw);}catch(e){return '(euc-jp)';} }
function identify(u8){
  const sig=hexAt(u8,0x8000,8);
  for(const [key,v] of Object.entries(REG.versions)){ if(v.sig8000.slice(0,16)===sig) return {key,v,sig}; }
  return {key:null,sig};
}
function decodeHorse1(u8,v){
  const fmt=v.recordFmt, F=FIELDS[fmt], r=parseInt(v.offsets.stat,16), g=f=>u8[r+F[f]];
  const name=v.offsets.names?readName(u8,parseInt(v.offsets.names,16),v.nameEnc):'';
  return {name, grade:GRADE[g('grade')], dirt:g('dirt'),
    ext:[g('start'),g('corner'),g('oob'),g('comp'),g('tenac'),g('spurt')],
    int:[g('stam'),g('speed'),g('sharp')], style:STYLE[g('style')], coat:COAT[g('coat')]||('0x'+g('coat').toString(16))};
}
function show(u8){
  const o=$('#out');
  if(u8.length!==4194304){ o.innerHTML=`<div class="card"><div class="bad">Not a DOC program ROM</div>Size is ${u8.length.toLocaleString()} bytes; a DOC program ROM is exactly 4,194,304.</div>`; return; }
  const {key,v,sig}=identify(u8);
  if(!key){ o.innerHTML=`<div class="card"><div class="bad">Unknown DOC ROM</div>4 MB, but the 0x8000 signature <code>${sig}</code> matches none of the known builds (Rev C/D, DOC 2000, DOC '99). Could be a hack or an unlisted region.</div>`; return; }
  const h=decodeHorse1(u8,v);
  const off=Object.entries(v.offsets).filter(([k,x])=>x).map(([k,x])=>`${k} <code>${x}</code>`).join(' · ');
  o.innerHTML=`<div class="card"><div class="ok">✓ ${v.label}</div>
    <table>
     <tr><td class="k">ROM</td><td><code>${v.epr}</code> · ${(u8.length).toLocaleString()} bytes · ${v.recordFmt}-byte records</td></tr>
     <tr><td class="k">0x8000 signature</td><td><code>${sig}</code> (matched)</td></tr>
     <tr><td class="k">table offsets</td><td>${off}</td></tr>
     <tr><td class="k">proof — horse #1</td><td><b>${h.name||'(JP name)'}</b> · ${h.grade} · ${h.style} · ${h.coat} · dirt ${h.dirt}<br>
        externals [${h.ext.join(', ')}] · internals [${h.int.join(', ')}]</td></tr>
    </table>
    <div class="hint">If horse #1's stats look right, the offsets are valid for this ROM.</div></div>`;
}
function load(file){ const r=new FileReader(); r.onload=e=>show(new Uint8Array(e.target.result)); r.readAsArrayBuffer(file); }
const drop=$('#drop'); drop.onclick=()=>$('#f').click();
$('#f').onchange=e=>{ if(e.target.files[0]) load(e.target.files[0]); };
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('hot');});
drop.addEventListener('dragleave',()=>drop.classList.remove('hot'));
drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('hot'); if(e.dataTransfer.files[0])load(e.dataTransfer.files[0]);});
</script></body></html>"""
out = HTML.replace("__REG__", reg)
open(f"{OUT}/fingerprinter.html","w",encoding="utf-8").write(out)
print(f"wrote {OUT}/fingerprinter.html ({len(out):,} bytes)")
