#!/usr/bin/env python3
"""doc-core tool #15: String Extractor / Importer + Bilingual Glossary + Profanity-list editor.

Builds string-tool.html:
  - Drop a .ic22 ROM -> fingerprint version (0x8000 sig) -> RE-EXTRACT every catalogued string
    from the dropped ROM bytes (so it reflects YOUR rom), shown in a searchable/filterable table
    by block + category (incl. the 'banned' profanity list).
  - Edit strings in place with a live BYTE-BUDGET meter (each string has a `cap` = safe span);
    edits over budget are flagged. Export a byte-exact patched .ic22 (EN/ASCII write-back).
  - Round-trip: export all strings to CSV or JSON (.po-style), edit externally, re-import to apply.
  - Bilingual glossary: align EN (Rev C) <-> JP (DOC 2000) by category+block+index, side-by-side.

Provenance: game-text.md (byte-exact catalog, verifyAllPass) + version sigs (architecture.md).
EN write-back is full (ASCII). JP is read/extract/glossary/CSV (EUC-JP encode-back not included).
"""
import json, io
OUT = r"C:/DerbyOwnersClub/doc-core"
S = json.load(io.open(f"{OUT}/doc_core_strings.json", encoding="utf-8"))
V = json.load(io.open(f"{OUT}/doc_core_versions.json", encoding="utf-8"))
sigOffset = int(V["sigOffset"], 16)
sigs = {k: vv for k, vv in V["versions"].items()}

data = {"sigOffset": sigOffset, "versions": {}}
for vk, vv in S["versions"].items():
    blocks = []
    for b in vv["blocks"]:
        blocks.append({
            "block": b["block"], "cat": b["category"],
            "start": int(b["start"], 16), "end": int(b["end"], 16),
            "s": [{"o": int(s["offset"], 16), "c": s.get("cap", len(s["text"])), "t": s["text"]} for s in b["strings"]],
        })
    data["versions"][vk] = {
        "tag": vv["tag"], "label": vv["label"], "lang": vv["lang"],
        "enc": "euc-jp" if vv["lang"] == "JP" else "ascii",
        "sig": sigs[vk]["sig8000"], "blocks": blocks,
    }
DATA = json.dumps(data, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC String Tool</title>
<style>
 body{margin:0;font:13px/1.45 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:10px 18px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:18px;color:#eae8e2}.sub{color:#7fb0bd;font-size:12px;font-weight:400}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:9px 18px;background:#0a242e;position:sticky;top:0;z-index:5;border-bottom:1px solid #143b48}
 .bar input[type=text],.bar select{background:#06303a;color:#e8eef0;border:1px solid #2a5666;border-radius:5px;padding:4px 8px;font-size:13px}
 button{background:#014b50;color:#cfe;border:0;border-radius:5px;padding:5px 11px;cursor:pointer;font-size:12px}
 button.act{background:#b75527;color:#fff}
 button:disabled{opacity:.4;cursor:not-allowed}
 .wrap{padding:8px 18px 40px}
 .tabs{display:flex;gap:6px;margin:8px 0}
 .tabs button{background:#0a242e;color:#9cc;border:1px solid #143b48}
 .tabs button.on{background:#014b50;color:#fff}
 table{border-collapse:collapse;width:100%;background:#08202a}
 th,td{border:1px solid #143b48;padding:3px 7px;text-align:left;font-size:12px;vertical-align:top}
 th{background:#0a242e;color:#9cc;position:sticky;top:48px}
 td.mono,.mono{font-family:Consolas,monospace}
 input.edit{width:100%;box-sizing:border-box;background:#06303a;color:#fff;border:1px solid #2a5666;border-radius:4px;padding:2px 5px;font-size:12px}
 input.edit.over{border-color:#ff6a6a;background:#3a1414}
 input.edit.changed{border-color:#d8a630}
 .budget{font-size:11px;color:#7fb0bd}.budget.over{color:#ff8a8a}
 .pill{display:inline-block;background:#014b50;color:#cfe;border-radius:9px;padding:0 7px;font-size:11px}
 .cat{color:#9cc;font-size:11px}
 .muted{color:#6f9aa6}.ok{color:#7fdca0}.warn{color:#ffb27f}
 .note{color:#7fb0bd;font-size:12px;margin:6px 0}
 #status{margin-left:auto;font-size:12px}
</style></head><body>
<header><h1>&#128172; DOC String Tool <span class="sub">tool #15 &middot; extract / edit / re-import strings + bilingual glossary</span></h1></header>
<div class="bar">
 <label class="pill" style="cursor:pointer">Drop / pick ROM (.ic22)<input id="rom" type="file" accept=".ic22,.bin,.zip" style="display:none"></label>
 <select id="ver"></select>
 <input id="q" type="text" placeholder="search text/block..." size="22">
 <select id="cat"><option value="">all categories</option></select>
 <span id="status" class="muted">no ROM loaded &mdash; browsing catalog text</span>
</div>
<div class="wrap">
 <div class="tabs">
  <button id="tabEdit" class="on">Extract &amp; Edit</button>
  <button id="tabGloss">Bilingual Glossary</button>
 </div>
 <div id="editPane">
  <div class="bar" style="position:static;padding:6px 0;background:none;border:0">
   <button id="expRom" class="act" disabled>&#128190; Export patched .ic22</button>
   <button id="expCsv">Export CSV</button>
   <button id="expJson">Export JSON (.po-style)</button>
   <label class="pill" style="cursor:pointer">Import edits (CSV/JSON)<input id="impFile" type="file" accept=".csv,.json" style="display:none"></label>
   <span id="editstat" class="muted"></span>
  </div>
  <div id="tbl"></div>
 </div>
 <div id="glossPane" style="display:none">
  <div class="note">Aligns English (Rev C) and Japanese (DOC 2000) by category + block name + index. Alignment is positional within matched blocks; treat as a translation aid, not a guaranteed 1:1.</div>
  <div id="gloss"></div>
 </div>
</div>
<script>
const DATA=__DATA__;
let rom=null, curVer='drbyocwc', extracted=[], edits={};
const $=s=>document.querySelector(s);
const hx=n=>'0x'+n.toString(16).toUpperCase();
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}

// version dropdown
{const vs=$('#ver');for(const k in DATA.versions){const o=document.createElement('option');o.value=k;o.textContent=DATA.versions[k].tag+' ('+DATA.versions[k].lang+')';vs.appendChild(o);}vs.value=curVer;}
// category dropdown
function fillCats(){const set=new Set();DATA.versions[curVer].blocks.forEach(b=>set.add(b.cat));const c=$('#cat');c.innerHTML='<option value="">all categories</option>';[...set].sort().forEach(x=>{const o=document.createElement('option');o.value=x;o.textContent=x;c.appendChild(o);});}

function decodeAt(bytes,off,cap,enc){
 // read up to first NUL within cap, decode
 let end=off;const lim=Math.min(off+cap,bytes.length);
 while(end<lim&&bytes[end]!==0)end++;
 const slice=bytes.slice(off,end);
 try{return new TextDecoder(enc).decode(slice);}catch(e){return new TextDecoder('ascii').decode(slice);}
}
function build(){
 const ver=DATA.versions[curVer];
 extracted=[];
 ver.blocks.forEach(b=>{b.s.forEach(s=>{
  const text = rom ? decodeAt(rom,s.o,s.c,ver.enc) : s.t;
  extracted.push({block:b.block,cat:b.cat,off:s.o,cap:s.c,orig:text});
 });});
 render();
}
function byteLen(str,enc){
 if(enc==='ascii')return str.length;
 // euc-jp byte length: ASCII=1, else 2 (kana/kanji) — approximation for budget
 let n=0;for(const ch of str){n+= (ch.charCodeAt(0)<128)?1:2;}return n;
}
function render(){
 const q=$('#q').value.toLowerCase(),cf=$('#cat').value,ver=DATA.versions[curVer],enc=ver.enc;
 const rows=extracted.filter(r=>(!cf||r.cat===cf)&&(!q||r.orig.toLowerCase().includes(q)||r.block.toLowerCase().includes(q)));
 let h='<table><thead><tr><th>Block</th><th>Cat</th><th>Offset</th><th>Original</th><th>New text (editable)</th><th>Bytes</th></tr></thead><tbody>';
 rows.forEach(r=>{
  const ed=edits[r.off], cur=ed!=null?ed:r.orig;
  const bl=byteLen(cur,enc), over=bl>r.cap, chg=cur!==r.orig;
  const dis = enc!=='ascii' ? 'disabled title="JP edit/write-back not supported in this build (read+glossary+CSV only)"' : '';
  h+='<tr><td>'+esc(r.block)+'</td><td class="cat">'+r.cat+'</td><td class="mono">'+hx(r.off)+'</td>'
   +'<td>'+esc(r.orig)+'</td>'
   +'<td><input class="edit'+(over?' over':'')+(chg?' changed':'')+'" data-off="'+r.off+'" value="'+esc(cur)+'" '+dis+'></td>'
   +'<td class="budget'+(over?' over':'')+'">'+bl+'/'+r.cap+'</td></tr>';
 });
 h+='</tbody></table>';
 $('#tbl').innerHTML=h;
 $('#tbl').querySelectorAll('input.edit').forEach(inp=>{
  inp.addEventListener('input',e=>{
   const off=+e.target.dataset.off;const r=extracted.find(x=>x.off===off);
   edits[off]=e.target.value;
   const bl=byteLen(e.target.value,enc),over=bl>r.cap;
   e.target.classList.toggle('over',over);e.target.classList.toggle('changed',e.target.value!==r.orig);
   const td=e.target.closest('tr').lastElementChild;td.textContent=bl+'/'+r.cap;td.classList.toggle('over',over);
   updEditStat();
  });
 });
 updEditStat();
}
function updEditStat(){
 const ver=DATA.versions[curVer],enc=ver.enc;
 const ch=Object.keys(edits).filter(o=>{const r=extracted.find(x=>x.off===+o);return r&&edits[o]!==r.orig;});
 const over=ch.filter(o=>{const r=extracted.find(x=>x.off===+o);return byteLen(edits[o],enc)>r.cap;});
 $('#editstat').innerHTML=ch.length?('<span class="'+(over.length?'warn':'ok')+'">'+ch.length+' edited'+(over.length?', '+over.length+' OVER budget':'')+'</span>'):'';
 $('#expRom').disabled=!(rom&&enc==='ascii'&&ch.length&&!over.length);
}
// ROM load + fingerprint
$('#rom').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{rom=new Uint8Array(r.result);const sig=[...rom.slice(DATA.sigOffset,DATA.sigOffset+16)].map(b=>b.toString(16).padStart(2,'0')).join('');
  let match=null;for(const k in DATA.versions)if(DATA.versions[k].sig===sig)match=k;
  if(match){curVer=match;$('#ver').value=match;fillCats();$('#status').innerHTML='<span class="ok">&#9679; '+f.name+' &mdash; '+DATA.versions[match].tag+' ('+DATA.versions[match].lang+')</span>';}
  else $('#status').innerHTML='<span class="warn">&#9679; '+f.name+' &mdash; unknown ROM (sig '+sig.slice(0,12)+'...); using selected version, offsets may not match</span>';
  edits={};build();
 };r.readAsArrayBuffer(f);});
$('#ver').addEventListener('change',e=>{curVer=e.target.value;fillCats();edits={};build();});
$('#q').addEventListener('input',render);$('#cat').addEventListener('change',render);

// export patched ROM (ASCII write-back, byte-safe within cap)
$('#expRom').addEventListener('click',()=>{
 if(!rom)return;const out=rom.slice();const ver=DATA.versions[curVer];
 let n=0;
 extracted.forEach(r=>{const ed=edits[r.off];if(ed==null||ed===r.orig)return;
  if(ed.length>r.cap)return; // skip over-budget
  for(let i=0;i<r.cap;i++)out[r.off+i]=(i<ed.length)?(ed.charCodeAt(i)&0x7f):0; // write + NUL-pad within cap
  n++;});
 dl(out,(ver.tag.replace(/\s/g,''))+'_patched.ic22','application/octet-stream');
 $('#editstat').innerHTML='<span class="ok">wrote '+n+' edits to patched ROM</span>';
});
function dl(data,name,type){const b=new Blob([data],{type});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;a.click();}
function csvCell(s){s=String(s==null?'':s);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;}
$('#expCsv').addEventListener('click',()=>{let c='offset,block,category,cap,original,new\n';
 extracted.forEach(r=>{const ed=edits[r.off];c+=[hx(r.off),csvCell(r.block),r.cat,r.cap,csvCell(r.orig),csvCell(ed!=null?ed:r.orig)].join(',')+'\n';});
 dl(c,DATA.versions[curVer].tag.replace(/\s/g,'')+'_strings.csv','text/csv');});
$('#expJson').addEventListener('click',()=>{const o=extracted.map(r=>({offset:hx(r.off),block:r.block,category:r.cat,cap:r.cap,original:r.orig,new:(edits[r.off]!=null?edits[r.off]:r.orig)}));
 dl(JSON.stringify({version:curVer,tag:DATA.versions[curVer].tag,strings:o},null,1),DATA.versions[curVer].tag.replace(/\s/g,'')+'_strings.json','application/json');});
$('#impFile').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{let applied=0;const txt=r.result;
  try{
   if(f.name.endsWith('.json')){const j=JSON.parse(txt);(j.strings||j).forEach(row=>{const off=parseInt(row.offset,16);const nv=row.new;const rec=extracted.find(x=>x.off===off);if(rec&&nv!=null&&nv!==rec.orig){edits[off]=nv;applied++;}});}
   else{const lines=txt.split(/\r?\n/);const hdr=lines.shift();lines.forEach(ln=>{if(!ln.trim())return;const c=parseCsv(ln);if(c.length<6)return;const off=parseInt(c[0],16);const nv=c[5];const rec=extracted.find(x=>x.off===off);if(rec&&nv!=null&&nv!==rec.orig){edits[off]=nv;applied++;}});}
  }catch(err){$('#editstat').innerHTML='<span class="warn">import failed: '+esc(err.message)+'</span>';return;}
  render();$('#editstat').innerHTML='<span class="ok">imported '+applied+' edits</span>';
 };r.readAsText(f);});
function parseCsv(line){const out=[];let cur='',q=false;for(let i=0;i<line.length;i++){const ch=line[i];if(q){if(ch==='"'){if(line[i+1]==='"'){cur+='"';i++;}else q=false;}else cur+=ch;}else{if(ch===','){out.push(cur);cur='';}else if(ch==='"')q=true;else cur+=ch;}}out.push(cur);return out;}

// tabs
$('#tabEdit').addEventListener('click',()=>{$('#tabEdit').classList.add('on');$('#tabGloss').classList.remove('on');$('#editPane').style.display='';$('#glossPane').style.display='none';});
$('#tabGloss').addEventListener('click',()=>{$('#tabGloss').classList.add('on');$('#tabEdit').classList.remove('on');$('#editPane').style.display='none';$('#glossPane').style.display='';renderGloss();});
function renderGloss(){
 const en=DATA.versions['drbyocwc'],jp=DATA.versions['derbyo2k'];
 // align blocks by (cat+block name); then by index within block
 let h='<table><thead><tr><th>Category</th><th>Block</th><th>#</th><th>English (Rev C)</th><th>Japanese (DOC 2000)</th></tr></thead><tbody>';
 jp.blocks.forEach(jb=>{
  // find EN block with same category & similar name, else same category
  let eb=en.blocks.find(b=>b.cat===jb.cat&&b.block===jb.block)||en.blocks.find(b=>b.cat===jb.cat);
  const n=Math.max(jb.s.length, eb?eb.s.length:0);
  for(let i=0;i<n;i++){
   const e=eb&&eb.s[i]?eb.s[i].t:'';const j=jb.s[i]?jb.s[i].t:'';
   if(!e&&!j)continue;
   h+='<tr><td class="cat">'+jb.cat+'</td><td>'+esc(jb.block)+'</td><td class="mono">'+i+'</td><td>'+esc(e)+'</td><td>'+esc(j)+'</td></tr>';
  }
 });
 h+='</tbody></table>';$('#gloss').innerHTML=h;
}
// drag-drop on whole page for ROM
document.addEventListener('dragover',e=>e.preventDefault());
document.addEventListener('drop',e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f){$('#rom').files=e.dataTransfer.files;$('#rom').dispatchEvent(new Event('change'));}});
fillCats();build();
</script></body></html>"""

html = HTML.replace("__DATA__", DATA)
open(f"{OUT}/string-tool.html", "w", encoding="utf-8").write(html)
nstr = sum(len(b["s"]) for v in data["versions"].values() for b in v["blocks"])
print("wrote string-tool.html (%d bytes), versions=%d, strings=%d" % (len(html), len(data["versions"]), nstr))
