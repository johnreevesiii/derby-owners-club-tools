#!/usr/bin/env python3
"""doc-core consumer: generate the NVRAM Hall-of-Fame Dashboard (read-only).

Drop a Derby Owners Club cabinet `.sram` (32 KB BBSRAM) and/or `.eeprom` (128 B) and the
page decodes it live in the browser (FileReader, byte-exact, no upload) and renders:
  - the Top-50 money leaderboard (region 1, with copy-2 metadata),
  - the 57 per-course track records,
  - the bookkeeping header (coin/play counters + dip flags) and the EEPROM machine ID,
  - both redundant regions + the checksum locations (noted, not recomputed).

Read-only this pass: NO save-editor. The name->grade/coat join table is extracted from
doc_core_roster.json (derbyocw / Rev D = the World Edition cabinet these saves come from).
Regenerate: python3 build_nvram_dashboard.py
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OUT = r"C:/DerbyOwnersClub/doc-core"

# name -> {id, grade, coat, style} join, from the Rev D (World Edition) roster
roster = json.load(open(f"{OUT}/doc_core_roster.json", encoding="utf-8"))
NAMEDB = {h["name"]: {"id": h["id"], "grade": h["grade"], "coat": h["coat"], "style": h["style"]}
          for h in roster["versions"]["derbyocw"]["horses"] if h.get("name")}
NAMEDB_JSON = json.dumps(NAMEDB, ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC NVRAM Hall of Fame — doc-core</title>
<style>
 :root{--teal:#014b50;--orange:#b75527;--sand:#eae8e2;--blue:#0e2f3c;--gold:#d8a630}
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527}
 header h1{margin:0;font-size:18px} header .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 input,select{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 input.search{width:220px}
 button{background:#b75527;color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600}
 button.sec{background:#123;border:1px solid #2a5560;color:#eae8e2}
 button:disabled{opacity:.4;cursor:not-allowed}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0}
 .tab.active{background:#014b50;border-color:#b75527}
 #drop{border:2px dashed #2a5560;border-radius:10px;padding:46px;text-align:center;color:#9ab;margin:34px auto;max-width:640px}
 #drop.hot{border-color:#b75527;background:#0a242e;color:#eae8e2}
 #drop code{color:#9fe0b0}
 .wrap{max-height:74vh;overflow:auto;margin:0 12px 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 8px;border-bottom:1px solid #143;white-space:nowrap;text-align:right}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase;z-index:1}
 th.l,td.l{text-align:left} td.name{text-align:left;font-weight:600}
 tr:hover td{background:#10323e} .rank{color:#d8a630;font-weight:700;text-align:right}
 .g1{color:#ffd27a}.g2{color:#caa6ff}.g3{color:#7ad2ff}
 .money{color:#9fe0b0;font-weight:700}
 .mono{font-family:ui-monospace,Consolas,monospace;color:#9cc}
 .hint{color:#9ab;font-size:12px;padding:0 18px 6px}
 .cards{display:flex;gap:14px;flex-wrap:wrap;padding:12px 18px}
 .card{background:#0a242e;border:1px solid #143;border-radius:8px;padding:12px 16px;min-width:200px}
 .card h3{margin:0 0 8px;font-size:12px;color:#9cc;text-transform:uppercase}
 .kv{display:flex;justify-content:space-between;gap:18px;padding:2px 0} .kv b{color:#eae8e2}
 .warn{color:#e0b06a;font-size:12px;padding:0 18px 8px}
 .pill{background:#123;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
 .ok{color:#9fe0b0}.bad{color:#e08a8a}
 #panel{display:none}
</style></head><body>
<header><h1>🏆 DOC NVRAM Hall of Fame <span class="sub">doc-core · cabinet career dashboard · read-only · byte-verified offsets</span></h1></header>

<div id="dropwrap">
 <div id="drop">Drop a Derby Owners Club cabinet save here, or click to choose.<br>
   <span class="hint"><code>.sram</code> (32 KB BBSRAM — leaderboards, track records, bookkeeping) and/or <code>.eeprom</code> (128 B — machine ID + dips).</span><br>
   <span class="hint">Everything is decoded locally in your browser. Nothing is uploaded. Read-only — no save is written.</span><br><br>
   <button id="pick">Choose file…</button>
 </div>
 <input type="file" id="file" accept=".sram,.eeprom,.bin,.nvmem" multiple style="display:none">
</div>

<div id="panel">
 <div class="bar">
  <span id="tabs"></span>
  <input class="search" id="q" placeholder="Search horse / holder…">
  <span id="region"></span>
  <button class="sec" id="csv">⬇ CSV</button>
  <button class="sec" id="json">⬇ JSON</button>
  <button class="sec" id="reset">↺ Load another</button>
  <span class="pill" id="count"></span>
 </div>
 <div class="warn" id="warn"></div>
 <div id="view"></div>
</div>

<script>
const NAMEDB = __NAMEDB__;
// ---- canonical byte-verified geometry (from doc_core_nvram.json) ----
const STRIDE=0x13c4, LB_REC=32, LB_N=50, TR_REC=28, TR_N=57;
const R1={hdr:0x01f8, marker:0x0218, lb1:0x0230, lb2:0x0870, track:0x0f7c, trailer:0x15c4};
const R2={hdr:R1.hdr+STRIDE, lb1:R1.lb1+STRIDE, lb2:R1.lb2+STRIDE, track:R1.track+STRIDE, trailer:R1.trailer+STRIDE}; // lb1=0x15f4
const $=s=>document.querySelector(s);
let SRAM=null, EE=null, dv=null, evd=null, fnames={};
let tab='money', region='r1', sortKey='money', sortDir=-1;

function ascii(o,n){let s='';for(let i=0;i<n;i++){const c=dv.getUint8(o+i)&0x7f;if(c===0)break;s+=String.fromCharCode(c);}return s.trim();}
function u16(o){return dv.getUint16(o,true);}
function u32(o){return dv.getUint32(o,true);}
function fmtMoney(n){return n.toLocaleString('en-US');}

function decodeMoney(base,copy2){
 const out=[];
 for(let i=0;i<LB_N;i++){const o=base+i*LB_REC;
   const r={rank:i+1,flag0:dv.getUint8(o),flag1:dv.getUint8(o+1),money:u32(o+2),name:ascii(o+0xc,20)};
   if(copy2){r.sub=dv.getUint8(o+8); r.meta=(u32(o+9)&0xffffff);}
   const j=NAMEDB[r.name]; r.id=j?j.id:''; r.grade=j?j.grade:''; r.coat=j?j.coat:''; r.style=j?j.style:'';
   out.push(r);} return out;
}
function decodeTrack(base){
 const out=[];
 for(let i=0;i<TR_N;i++){const o=base+i*TR_REC; const cs=u32(o+0x14);
   out.push({race:i,holder:ascii(o,20),timeCs:cs,timeSec:(cs/100).toFixed(2),tail:u32(o+0x18)});}
 return out;
}
function regBase(){return region==='r1'?R1:R2;}

function decodeAll(){
 if(!SRAM)return;
 dv=new DataView(SRAM.buffer,SRAM.byteOffset,SRAM.byteLength);
 const r=regBase();
 window._money=decodeMoney(r.lb1,false);
 window._money2=decodeMoney(r.lb2,true);
 window._track=decodeTrack(r.track);
 // bookkeeping (header always region-independent, lives at 0x00)
 window._book={
   playA:u32(0x00),playB:u32(0x04),runtime:u32(0x08),
   flags:[0x10,0x20,0x30,0x40,0x44,0x4c].map(o=>({off:o,v:dv.getUint8(o)})),
   markerVal:u32(r.marker),markerName:ascii(r.marker+4,20),
   chk:u16(r.hdr),lenWord:u32(r.hdr+4),
   trailerChk:u16(r.trailer+4),
   header100Lead:u32(0x100),
   verbatimMirror:(()=>{for(let i=0;i<12;i++)if(dv.getUint8(i)!==dv.getUint8(0x100+i))return false;return true;})(),
 };
 // integrity: region header doubled?
 window._book.hdrDoubled=(()=>{for(let i=0;i<16;i++)if(dv.getUint8(r.hdr+i)!==dv.getUint8(r.hdr+0x10+i))return false;return true;})();
 // last nonzero
 let ln=SRAM.length; while(ln>0&&dv.getUint8(ln-1)===0)ln--; window._lastnz=ln;
}
function decodeEE(){
 if(!EE)return; evd=new DataView(EE.buffer,EE.byteOffset,EE.byteLength);
 const a=(o,n)=>{let s='';for(let i=0;i<n;i++){const c=evd.getUint8(o+i)&0x7f;if(c===0)break;s+=String.fromCharCode(c);}return s.trim();};
 let mir=true; for(let i=0;i<0x12;i++)if(evd.getUint8(i)!==evd.getUint8(0x12+i))mir=false;
 window._ee={sysCrc:evd.getUint16(0,true),gameTag:a(0x30,21),gameCrc:evd.getUint32(0x2c,false),mirrored:mir};
}

function gradeCls(g){return g==='G1'?'g1':g==='G2'?'g2':g==='G3'?'g3':'';}

function renderMoney(){
 const q=$('#q').value.toLowerCase().trim();
 const meta={}; window._money2.forEach(m=>meta[m.rank]=m);
 let rows=window._money.map(r=>({...r, sub:meta[r.rank]?.sub, recMeta:meta[r.rank]?.meta}));
 if(q)rows=rows.filter(r=>(r.name+' '+r.id+' '+r.grade).toLowerCase().includes(q));
 const get=r=>({rank:r.rank,money:r.money,name:r.name,grade:r.grade,id:r.id,flag0:r.flag0,flag1:r.flag1,coat:r.coat,style:r.style}[sortKey]);
 rows.sort((a,b)=>{const x=get(a),y=get(b);return(x<y?-1:x>y?1:0)*sortDir;});
 const cols=[['rank','#'],['name','Horse'],['money','Prize ($)'],['grade','Gr'],['style','Style'],['coat','Coat'],['id','ROM#'],['flag0','f0'],['flag1','f1'],['sub','c2.sub'],['recMeta','c2.meta']];
 let h='<div class="wrap"><table><thead><tr>'+cols.map(([k,l])=>`<th class="${k==='name'?'l':''}" data-k="${k}">${l}</th>`).join('')+'</tr></thead><tbody>';
 for(const r of rows){
   h+=`<tr><td class="rank">${r.rank}</td><td class="name">${r.name||'<i>—</i>'}</td><td class="money">${fmtMoney(r.money)}</td>`
    +`<td class="${gradeCls(r.grade)}">${r.grade||''}</td><td class="l">${r.style||''}</td><td class="l">${r.coat||''}</td>`
    +`<td>${r.id||''}</td><td>${r.flag0}</td><td class="mono">0x${r.flag1.toString(16)}</td>`
    +`<td>${r.sub??''}</td><td class="mono">${r.recMeta!=null?'0x'+r.recMeta.toString(16):''}</td></tr>`;
 }
 $('#view').innerHTML=h+'</tbody></table></div>';
 $('#count').textContent=`${rows.length} horses`;
 bindSort();
}
function renderTrack(){
 const q=$('#q').value.toLowerCase().trim();
 let rows=window._track.slice();
 if(q)rows=rows.filter(r=>(r.holder+' '+r.race).toLowerCase().includes(q));
 const get=r=>({race:r.race,holder:r.holder,timeCs:r.timeCs}[sortKey]??r.timeCs);
 if(['race','holder','timeCs','timeSec'].includes(sortKey)) rows.sort((a,b)=>{const x=get(a),y=get(b);return(x<y?-1:x>y?1:0)*sortDir;});
 const cols=[['race','Race #'],['holder','Record Holder'],['timeSec','Time (s)'],['timeCs','cs'],['tail','tail']];
 let h='<div class="wrap"><table><thead><tr>'+cols.map(([k,l])=>`<th class="${k==='holder'?'l':''}" data-k="${k}">${l}</th>`).join('')+'</tr></thead><tbody>';
 for(const r of rows) h+=`<tr><td class="rank">${r.race}</td><td class="name">${r.holder||'<i>—</i>'}</td><td class="money">${r.timeSec}</td><td>${r.timeCs}</td><td>${r.tail}</td></tr>`;
 $('#view').innerHTML=h+'</tbody></table></div>';
 $('#count').textContent=`${rows.length} courses`;
 bindSort();
}
function renderBook(){
 const b=window._book, ee=window._ee;
 const flag=o=>b.flags.find(f=>f.off===o)?.v;
 let h='<div class="cards">';
 h+=`<div class="card"><h3>Bookkeeping header (0x00)</h3>
   <div class="kv">Play counter A <b>${b.playA.toLocaleString()}</b></div>
   <div class="kv">Play counter B <b>${b.playB.toLocaleString()}</b></div>
   <div class="kv">Runtime / section counter <b>${b.runtime.toLocaleString()}</b></div>
   <div class="kv">0x100 header lead <b class="mono">0x${b.header100Lead.toString(16)}</b></div>
   <div class="kv">0x00≡0x100 verbatim? <b class="${b.verbatimMirror?'bad':'ok'}">${b.verbatimMirror?'yes':'no (distinct hdr)'}</b></div></div>`;
 h+=`<div class="card"><h3>Dip / setting flags</h3>`+
   [0x10,0x20,0x30,0x40,0x44,0x4c].map(o=>`<div class="kv">flag @0x${o.toString(16)} <b>${flag(o)}</b></div>`).join('')+`</div>`;
 h+=`<div class="card"><h3>Active region (${region.toUpperCase()})</h3>
   <div class="kv">Marker rank-0 <b>${b.markerName||'—'}</b></div>
   <div class="kv">Marker value <b>${b.markerVal.toLocaleString()}</b></div>
   <div class="kv">Region checksum <b class="mono">0x${b.chk.toString(16)}</b></div>
   <div class="kv">Header doubled? <b class="${b.hdrDoubled?'ok':'bad'}">${b.hdrDoubled?'yes':'no'}</b></div>
   <div class="kv">Length word <b class="mono">0x${b.lenWord.toString(16)}</b></div>
   <div class="kv">Trailer 2nd checksum <b class="mono">0x${b.trailerChk.toString(16)}</b></div>
   <div class="kv">SRAM used through <b class="mono">0x${window._lastnz.toString(16)}</b> / 32768</div></div>`;
 if(ee) h+=`<div class="card"><h3>EEPROM machine ID</h3>
   <div class="kv">Game tag <b>${ee.gameTag}</b></div>
   <div class="kv">System CRC16 <b class="mono">0x${ee.sysCrc.toString(16)}</b></div>
   <div class="kv">Game CRC (BE) <b class="mono">0x${(ee.gameCrc>>>0).toString(16)}</b></div>
   <div class="kv">Two mirrored halves <b class="${ee.mirrored?'ok':'bad'}">${ee.mirrored?'yes':'no'}</b></div></div>`;
 else h+=`<div class="card"><h3>EEPROM</h3><div class="kv">No .eeprom loaded <b>—</b></div><div class="hint">Drop the 128-byte .eeprom alongside the .sram for machine ID.</div></div>`;
 h+='</div>';
 h+=`<div class="warn">Checksum locations (read-only — not recomputed): region-1 LE16 @0x1f8 (doubled @0x208) + trailer @0x15c8; region-2 LE16 @0x15bc (doubled @0x15cc) + trailer @0x298c. The two save regions are redundant backups (region 2 = region 1 + 0x13c4). flag0/flag1 and the copy-2 meta (0x1680) are not yet semantically decoded.</div>`;
 $('#view').innerHTML=h;
 $('#count').textContent='';
}
function bindSort(){
 $('#view').querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;
   if(sortKey===k)sortDir*=-1; else{sortKey=k; sortDir=(k==='name'||k==='holder'||k==='race'||k==='rank')?1:-1;} render();});
}
function render(){
 $('#warn').textContent = SRAM ? '' : 'Load a .sram to see leaderboards and track records.';
 if(tab==='money'){if(sortKey==='timeCs')sortKey='money'; renderMoney();}
 else if(tab==='track'){if(['money','rank'].includes(sortKey))sortKey='race'; renderTrack();}
 else renderBook();
}

// ---- export ----
function exp(fmt){
 let rows, name;
 if(tab==='money'){const meta={};window._money2.forEach(m=>meta[m.rank]=m);
   rows=window._money.map(r=>({rank:r.rank,name:r.name,money:r.money,grade:r.grade,style:r.style,coat:r.coat,romId:r.id,flag0:r.flag0,flag1:r.flag1,c2sub:meta[r.rank]?.sub,c2meta:meta[r.rank]?.meta})); name='doc-nvram-money-'+region;}
 else if(tab==='track'){rows=window._track.map(r=>({race:r.race,holder:r.holder,timeSec:r.timeSec,timeCs:r.timeCs,tail:r.tail})); name='doc-nvram-track-'+region;}
 else {rows=[window._book]; name='doc-nvram-bookkeeping';}
 let blob;
 if(fmt==='json'){blob=new Blob([JSON.stringify(rows,null,1)],{type:'application/json'}); name+='.json';}
 else{const cols=Object.keys(rows[0]); const esc=x=>`"${String(x==null?'':x).replace(/"/g,'""')}"`;
   const lines=[cols.join(',')].concat(rows.map(r=>cols.map(c=>esc(r[c])).join(',')));
   blob=new Blob(['﻿'+lines.join('\n')],{type:'text/csv;charset=utf-8'}); name+='.csv';}
 const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; a.click();
}

// ---- file loading (FileReader, byte-exact, no upload) ----
function handleFiles(files){
 [...files].forEach(f=>{
   const fr=new FileReader();
   fr.onload=()=>{const u=new Uint8Array(fr.result);
     if(u.length===32768){SRAM=u; fnames.sram=f.name; decodeAll();}
     else if(u.length===128){EE=u; fnames.ee=f.name; decodeEE();}
     else if(u.length===65536){ // some emus pad BBSRAM to 64K; use first 32K
       SRAM=u.subarray(0,32768); fnames.sram=f.name+' (64K, using first 32K)'; decodeAll();}
     else {$('#warn').textContent=`Unrecognized size ${u.length} for ${f.name} (expect 32768 .sram or 128 .eeprom).`;}
     afterLoad();
   };
   fr.readAsArrayBuffer(f);
 });
}
function afterLoad(){
 if(!SRAM&&!EE)return;
 $('#dropwrap').style.display='none'; $('#panel').style.display='block';
 const parts=[]; if(fnames.sram)parts.push('SRAM: '+fnames.sram); if(fnames.ee)parts.push('EEPROM: '+fnames.ee);
 $('#region').innerHTML = SRAM ? `<label>Region <select id="rsel"><option value="r1">1 (primary)</option><option value="r2">2 (backup)</option></select></label>` : '';
 const rs=$('#rsel'); if(rs)rs.onchange=e=>{region=e.target.value; decodeAll(); render();};
 $('#count').title=parts.join('  ·  ');
 $('#csv').disabled=$('#json').disabled=!SRAM&&tab!=='book';
 render();
}
const TABS=[['money','💰 Money Leaderboard'],['track','🏁 Track Records'],['book','🛠 Bookkeeping / EEPROM']];
$('#tabs').innerHTML=TABS.map(([k,l],i)=>`<span class="tab${i===0?' active':''}" data-t="${k}">${l}</span>`).join('');
$('#tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  tab=t.dataset.t; $('#tabs').querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t)); render();});
$('#q').addEventListener('input',render);
$('#csv').onclick=()=>exp('csv'); $('#json').onclick=()=>exp('json');
$('#reset').onclick=()=>{SRAM=EE=null;fnames={};$('#panel').style.display='none';$('#dropwrap').style.display='block';$('#file').value='';};
$('#pick').onclick=()=>$('#file').click();
$('#drop').onclick=()=>$('#file').click();
$('#file').onchange=e=>{if(e.target.files.length)handleFiles(e.target.files);};
const dz=$('#drop');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('hot');});
dz.addEventListener('dragleave',()=>dz.classList.remove('hot'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('hot');if(e.dataTransfer.files.length)handleFiles(e.dataTransfer.files);});
</script></body></html>"""

out = HTML.replace("__NAMEDB__", NAMEDB_JSON)
path = f"{OUT}/nvram-dashboard.html"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote {path} ({len(out):,} bytes; name DB {len(NAMEDB)} horses embedded)")
