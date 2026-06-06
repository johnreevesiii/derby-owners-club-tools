#!/usr/bin/env python3
"""doc-core consumer: Breeding-Stock Browser + Foal Projector.
Embeds doc_core_breeding.json. Browse sires/dams/mater (all 4 versions, sort/filter/search/export)
and project a foal from any two parents using the community averaging model (heuristic; the exact
ROM breeding routine awaits the SH-4 session)."""
import json, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
payload = json.dumps(json.load(open(f"{OUT}/doc_core_breeding.json", encoding="utf-8")), ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Breeding Stock + Foal Projector — doc-core</title>
<style>
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527} header h1{margin:0;font-size:18px} .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px} input.search{width:200px}
 button{background:#b75527;color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600} button.sec{background:#125;border:1px solid #2a5}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0} .tab.active{background:#014b50;border-color:#b75527}
 .wrap{max-height:62vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 7px;border-bottom:1px solid #143;white-space:nowrap;text-align:right} th.l,td.l{text-align:left}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase;z-index:1}
 td.name{text-align:left;font-weight:600} tr:hover td{background:#10323e}
 .sire{color:#7ad2ff}.dam{color:#f3a0c8} .band{letter-spacing:1px;color:#ffd27a} .romaji{color:#9cc;font-style:italic;font-size:11px}
 .foal{background:#0a2028;border:1px solid #2a5560;border-radius:8px;margin:10px 12px;padding:12px 16px}
 .foal h3{margin:0 0 8px;color:#9fe0b0} .foal .stat{display:inline-block;margin:0 14px 6px 0} .foal b{color:#ffd27a}
 .hint{color:#9ab;font-size:12px;padding:4px 18px} .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
</style></head><body>
<header><h1>🧬 DOC Breeding Stock + Foal Projector <span class="sub">doc-core · sires/dams/mater · all 4 versions · ac = dirt aptitude 0-255 · externals ×△○◎</span></h1></header>
<div class="bar">
 <span id="tabs"></span>
 <input class="search" id="q" placeholder="Search name / romaji…">
 <label>Show <select id="fk"><option value="">all</option><option value="sire">sires</option><option value="dam">dams</option></select></label>
 <button class="sec" onclick="exp('csv')">⬇ CSV</button><button class="sec" onclick="exp('json')">⬇ JSON</button>
 <span class="pill" id="count"></span>
</div>
<div class="foal">
 <h3>🐎 Foal Projector <span style="font-weight:400;color:#9ab;font-size:12px">— community averaging model (heuristic; exact ROM rule pending SH-4)</span></h3>
 Parent A <select id="pa"></select> × Parent B <select id="pb"></select>
 <span id="foalOut" style="margin-left:14px"></span>
</div>
<div class="hint">Click a column to sort. Externals are the 1-16 aptitude bands (× 1-4 · △ 5-8 · ○ 9-12 · ◎ 13-16). EN splits sires/dams; JP is one merged 167-mater pool.</div>
<div class="wrap"><table id="t"></table></div>
<script>
const BREED=__PAYLOAD__, VERS=Object.keys(BREED.versions);
let cur=VERS[0], sortKey='index', sortDir=1;
const $=s=>document.querySelector(s);
const EXT=['start','corner','oob','competing','tenacious','spurt'];
function pool(){return BREED.versions[cur].pool;}
function rows(){
 const q=$('#q').value.toLowerCase().trim(), fk=$('#fk').value;
 let p=pool().filter(h=>{
   const nm=((h.name||'')+' '+(h.nameJP||'')+' '+(h.romaji||'')).toLowerCase();
   return (!q||nm.includes(q)) && (!fk||h.kind===fk);
 });
 const get=h=>{switch(sortKey){case 'index':return h.index;case 'name':return (h.name||h.romaji||'');case 'kind':return h.kind||'';case 'st':case 'sp':case 'sh':case 'ac':return h[sortKey];default:return h.externals[sortKey];}};
 p.sort((a,b)=>{const x=get(a),y=get(b);return (x<y?-1:x>y?1:0)*sortDir;});
 return p;
}
const COLS=[['index','#'],['name','Name'],['kind','Type'],['st','ST'],['sp','SP'],['sh','SH'],['ac','AC(dirt)'],
 ['start','St'],['corner','Co'],['oob','OOB'],['competing','Cmp'],['tenacious','Tn'],['spurt','Sp'],['bands','Bands']];
function nm(h){return h.name?h.name:`${h.nameJP||''} <span class="romaji">${h.romaji||''}</span>`;}
function render(){
 const p=rows();
 let h='<thead><tr>'+COLS.map(([k,l])=>`<th class="${k==='name'||k==='kind'||k==='bands'?'l':''}" data-k="${k==='bands'?'index':k}">${l}</th>`).join('')+'</tr></thead><tbody>';
 for(const r of p){
   const kc=r.kind==='sire'?'sire':r.kind==='dam'?'dam':'';
   h+=`<tr><td>${r.index}</td><td class="name">${nm(r)}</td><td class="l ${kc}">${r.kind||'mater'}</td>`
    +`<td>${r.st}</td><td>${r.sp}</td><td>${r.sh}</td><td>${r.ac}</td>`
    +EXT.map(e=>`<td>${r.externals[e]}</td>`).join('')+`<td class="l band">${r.bands}</td></tr>`;
 }
 $('#t').innerHTML=h+'</tbody>'; $('#count').textContent=`${p.length}`;
 $('#t').querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k; if(sortKey===k)sortDir*=-1; else{sortKey=k;sortDir=(k==='name'||k==='index')?1:-1;} render();});
}
// ---- foal projector (community averaging model, §6) ----
function band(v){return v>=13?'◎':v>=9?'○':v>=5?'△':v>=1?'×':'·';}
function clamp(v,lo,hi){return Math.max(lo,Math.min(hi,v));}
function style(ext){const vals=[ext.start,ext.oob,ext.competing,ext.tenacious,ext.spurt];
 const range=Math.max(...vals)-Math.min(...vals); if(range<=3)return 'Almighty';
 const greater=vals.filter(v=>v>ext.start).length; return greater===0?'Front-runner':greater===1?'Start dash':greater>=3?'Last spurt':'Stretch-runner';}
function foal(a,b){
 const f={st:Math.floor((a.st+b.st)/2),sp:Math.floor((a.sp+b.sp)/2),sh:Math.floor((a.sh+b.sh)/2),ac:Math.floor((a.ac+b.ac)/2)};
 if(a.st>=45&&b.st>=40)f.st+=2; if(a.sp>=45&&b.sp>=40)f.sp+=2; if(a.ac>220&&b.ac>220)f.ac+=20;
 f.st=clamp(f.st,10,60);f.sp=clamp(f.sp,10,65);f.sh=clamp(f.sh,10,60);f.ac=clamp(f.ac,0,255);
 const ext={}; for(const e of EXT) ext[e]=clamp(Math.floor((a.externals[e]+b.externals[e])/2),1,16);
 return {...f,externals:ext,style:style(ext)};
}
function renderFoal(){
 const p=pool(); const A=p[+$('#pa').value], B=p[+$('#pb').value];
 if(!A||!B){$('#foalOut').textContent='';return;}
 const f=foal(A,B);
 const eb=EXT.map(e=>`${e[0].toUpperCase()}${f.externals[e]}${band(f.externals[e])}`).join(' ');
 $('#foalOut').innerHTML=`→ foal ≈ <b>ST ${f.st}</b> · <b>SP ${f.sp}</b> · <b>SH ${f.sh}</b> · <b>AC ${f.ac}</b> · style <b>${f.style}</b> &nbsp; <span class="romaji">externals ${eb}</span> <span style="color:#9ab">(expected; ±noise in game)</span>`;
}
function exp(fmt){const p=rows(); let blob,name;
 if(fmt==='json'){blob=new Blob([JSON.stringify(p,null,1)],{type:'application/json'});name=`doc-breeding-${cur}.json`;}
 else{const cols=['index','name','nameJP','romaji','kind','st','sp','sh','ac',...EXT,'bands'];
   const esc=x=>`"${String(x==null?'':x).replace(/"/g,'""')}"`;
   const lines=[cols.join(',')].concat(p.map(h=>cols.map(c=>esc(c in h?h[c]:h.externals[c])).join(',')));
   blob=new Blob(['﻿'+lines.join('\n')],{type:'text/csv;charset=utf-8'});name=`doc-breeding-${cur}.csv`;}
 const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();}
function fillParents(){
 const p=pool();
 const opt=(h,i)=>`<option value="${i}">${(h.name||h.romaji||h.nameJP)} (ac${h.ac})</option>`;
 const sires=p.map((h,i)=>[h,i]).filter(([h])=>h.kind!=='dam'); const dams=p.map((h,i)=>[h,i]).filter(([h])=>h.kind!=='sire');
 $('#pa').innerHTML=sires.map(([h,i])=>opt(h,i)).join(''); $('#pb').innerHTML=dams.map(([h,i])=>opt(h,i)).join('');
 renderFoal();
}
$('#tabs').innerHTML=VERS.map(v=>`<span class="tab" data-v="${v}">${BREED.versions[v].tag}</span>`).join('');
$('#tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{cur=t.dataset.v;$('#tabs').querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t));fillParents();render();});
$('#tabs').firstChild.classList.add('active');
['q','fk'].forEach(id=>$('#'+id).addEventListener('input',render));
['pa','pb'].forEach(id=>$('#'+id).addEventListener('change',renderFoal));
fillParents(); render();
</script></body></html>"""
out = HTML.replace("__PAYLOAD__", payload)
open(f"{OUT}/breeding-browser.html","w",encoding="utf-8").write(out)
print(f"wrote {OUT}/breeding-browser.html ({len(out):,} bytes)")
