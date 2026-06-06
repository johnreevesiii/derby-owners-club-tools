#!/usr/bin/env python3
"""doc-core consumer: generate a standalone CPU Roster Browser + Power-Ranking.
Embeds doc_core_roster.json so the HTML runs offline from file://.
Tier-1 tools #1 (roster browser/power-rank) + #2 (CSV/JSON exporter) in one page."""
import json, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
data = json.load(open(f"{OUT}/doc_core_roster.json", encoding="utf-8"))
payload = json.dumps(data, ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC CPU Roster Browser — doc-core</title>
<style>
 :root{--teal:#014b50;--orange:#b75527;--sand:#eae8e2;--blue:#0e2f3c;--gold:#d8a630}
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527}
 header h1{margin:0;font-size:18px} header .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 input.search{width:220px}
 button{background:#b75527;color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600}
 button.sec{background:#125;border:1px solid #2a5}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0}
 .tab.active{background:#014b50;border-color:#b75527}
 .wrap{max-height:78vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 7px;border-bottom:1px solid #143;white-space:nowrap;text-align:right}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase;z-index:1}
 th.l,td.l{text-align:left} td.name{text-align:left;font-weight:600}
 tr:hover td{background:#10323e} .rank{color:#d8a630;font-weight:700}
 .g1{color:#ffd27a}.g2{color:#caa6ff}.g3{color:#7ad2ff}
 .pow{color:#9fe0b0;font-weight:700}
 .romaji{color:#9cc;font-style:italic;font-size:11px}
 .hint{color:#9ab;font-size:12px;padding:0 18px 6px}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
</style></head><body>
<header><h1>🏇 DOC CPU Roster Browser <span class="sub">doc-core · 244 opponents · all 4 versions · byte-verified</span></h1></header>
<div class="bar">
 <span id="tabs"></span>
 <input class="search" id="q" placeholder="Search name / romaji / #…">
 <label>Grade <select id="fg"><option value="">all</option><option>G1</option><option>G2</option><option>G3</option><option>Ungraded</option></select></label>
 <label>Style <select id="fs"><option value="">all</option></select></label>
 <label title="Formula-derived rating (race formula now decoded). Internal-emphasis weight ×">Pow wt
   <input id="wt" type="range" min="0.5" max="4" step="0.5" value="2.5" style="vertical-align:middle"> <span id="wtv">2.5</span>×</label>
 <button class="sec" onclick="exp('csv')">⬇ CSV</button>
 <button class="sec" onclick="exp('json')">⬇ JSON</button>
 <span class="pill" id="count"></span>
</div>
<div class="hint">Click a column to sort. <b>Power</b> = <b>formula-derived</b> (per <code>RACE_FORMULA_FINDINGS</code>): per-phase external total + role-weighted internals (speed=ceiling, stamina=sustain, sharp=accel; emphasis ×<span id="wth">2.5</span>) × best-surface affinity from the decoded dirt curve. For full tick-by-tick race odds, see <b>race-lab.html</b>. JP versions show カタカナ (romaji).</div>
<div class="wrap"><table id="t"></table></div>
<script>
const DATA = __PAYLOAD__;
const VERS = Object.keys(DATA.versions);
let cur = VERS[0], sortKey='power', sortDir=-1, wt=2.5;
const $=s=>document.querySelector(s);
function dirtBand(b){return b>=128?0.0042:b>=121?0.0052:b>=116?0.0035:0.003;} // recovered dirt 4-band curve
function pow(h){ // FORMULA-DERIVED rating (RACE_FORMULA_FINDINGS): per-phase externals + role-weighted internals x best-surface affinity
 const it=h.internals;
 const internal=(it.speed*1.0 + it.stamina*0.8 + it.sharp*0.6)*(wt/2.5); // roles: speed=ceiling, stamina=sustain, sharp=accel
 const c=dirtBand(h.dirt)*h.dirt, turf=0.80+(0.0042*255-c)*0.5, dirt=0.80+c; // dirt-band surface factor
 const surf=Math.max(turf,dirt);                                            // rate each horse on its best surface
 return (h.extTotal + internal) * (0.85+0.15*surf);
}
function rows(){
 const q=$('#q').value.toLowerCase().trim(), fg=$('#fg').value, fs=$('#fs').value;
 let hs=DATA.versions[cur].horses.map(h=>({...h, power:Math.round(pow(h))}));
 hs=hs.filter(h=>{
   const nm=((h.name||'')+' '+(h.nameJP||'')+' '+(h.romaji||'')+' '+h.id).toLowerCase();
   return (!q||nm.includes(q)) && (!fg||h.grade===fg) && (!fs||h.style===fs);
 });
 const get=h=>{switch(sortKey){case 'power':return h.power;case 'id':return h.id;case 'name':return (h.name||h.romaji||'');case 'grade':return h.grade;case 'style':return h.style;case 'coat':return h.coat;case 'dirt':return h.dirt;case 'extTotal':return h.extTotal;case 'stamina':case 'speed':case 'sharp':return h.internals[sortKey];default:return h.externals[sortKey];}};
 hs.sort((a,b)=>{const x=get(a),y=get(b);return (x<y?-1:x>y?1:0)*sortDir;});
 return hs;
}
const COLS=[['id','#'],['name','Horse'],['grade','Gr'],['style','Style'],['coat','Coat'],['dirt','Dirt'],
  ['start','St'],['corner','Co'],['oob','OOB'],['competing','Cmp'],['tenacious','Tn'],['spurt','Sp'],
  ['extTotal','ΣExt'],['stamina','Stam'],['speed','Spd'],['sharp','Shrp'],['power','Power']];
function render(){
 const hs=rows();
 let h='<thead><tr>'+COLS.map(([k,l])=>`<th class="${k==='name'?'l':''}" data-k="${k}">${l}</th>`).join('')+'</tr></thead><tbody>';
 for(const r of hs){
   const nm = r.name ? r.name : `${r.nameJP||''} <span class="romaji">${r.romaji||''}</span>`;
   const gc = r.grade==='G1'?'g1':r.grade==='G2'?'g2':r.grade==='G3'?'g3':'';
   h+=`<tr><td>${r.id}</td><td class="name">${nm}</td><td class="${gc}">${r.grade}</td><td class="l">${r.style}</td><td class="l">${r.coat}</td><td>${r.dirt}</td>`
    +`<td>${r.externals.start}</td><td>${r.externals.corner}</td><td>${r.externals.oob}</td><td>${r.externals.competing}</td><td>${r.externals.tenacious}</td><td>${r.externals.spurt}</td>`
    +`<td>${r.extTotal}</td><td>${r.internals.stamina}</td><td>${r.internals.speed}</td><td>${r.internals.sharp}</td><td class="pow">${r.power}</td></tr>`;
 }
 $('#t').innerHTML=h+'</tbody>';
 $('#count').textContent=`${hs.length} horses`;
 $('#t').querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k; if(sortKey===k)sortDir*=-1; else{sortKey=k;sortDir=(k==='name'||k==='id')?1:-1;} render();});
}
function exp(fmt){
 const hs=rows(); const v=DATA.versions[cur];
 let blob, name;
 if(fmt==='json'){ blob=new Blob([JSON.stringify(hs,null,1)],{type:'application/json'}); name=`doc-roster-${cur}.json`; }
 else{
   const cols=['id','name','nameJP','romaji','grade','style','coat','dirt','start','corner','oob','competing','tenacious','spurt','extTotal','stamina','speed','sharp','power'];
   const esc=x=>`"${String(x==null?'':x).replace(/"/g,'""')}"`;
   const lines=[cols.join(',')].concat(hs.map(h=>cols.map(c=>esc(c in h?h[c]:(h.externals[c]??h.internals[c]))).join(',')));
   blob=new Blob(['﻿'+lines.join('\n')],{type:'text/csv;charset=utf-8'}); name=`doc-roster-${cur}.csv`;
 }
 const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; a.click();
}
// version tabs
$('#tabs').innerHTML=VERS.map(v=>`<span class="tab" data-v="${v}">${DATA.versions[v].tag}</span>`).join('');
$('#tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{cur=t.dataset.v; $('#tabs').querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t)); render();});
$('#tabs').firstChild.classList.add('active');
// style filter options (union)
const styles=[...new Set(VERS.flatMap(v=>DATA.versions[v].horses.map(h=>h.style)))];
$('#fs').innerHTML='<option value="">all</option>'+styles.map(s=>`<option>${s}</option>`).join('');
['q','fg','fs'].forEach(id=>$('#'+id).addEventListener('input',render));
$('#wt').addEventListener('input',e=>{wt=+e.target.value; $('#wtv').textContent=wt; $('#wth').textContent=wt; render();});
render();
</script></body></html>"""

out = HTML.replace("__PAYLOAD__", payload)
open(f"{OUT}/roster-browser.html", "w", encoding="utf-8").write(out)
print(f"wrote {OUT}/roster-browser.html ({len(out):,} bytes, data embedded)")
