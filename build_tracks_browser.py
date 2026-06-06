#!/usr/bin/env python3
"""doc-core consumer: generate a standalone Tracks / Courses / G1-Calendar Browser.
Embeds doc_core_tracks.json so the HTML runs offline from file://.
Mirrors roster-browser.html house style (dark theme, sticky header, searchable/sortable,
CSV/JSON export). Shows courses + G1 races + special/handicap per version, plus the
EN<->JP venue localization map."""
import json, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
data = json.load(open(f"{OUT}/doc_core_tracks.json", encoding="utf-8"))
payload = json.dumps(data, ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Tracks &amp; G1 Calendar — doc-core</title>
<style>
 :root{--teal:#014b50;--orange:#b75527;--sand:#eae8e2;--blue:#0e2f3c;--gold:#d8a630}
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--blue);color:var(--sand);font-size:13px}
 header{background:var(--teal);padding:12px 18px;border-bottom:3px solid var(--orange)}
 header h1{margin:0;font-size:18px} header .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:var(--sand);border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 input.search{width:220px}
 button{background:var(--orange);color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600}
 button.sec{background:#125;border:1px solid #2a5560}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0}
 .tab.active{background:var(--teal);border-color:var(--orange)}
 .sub-tabs{display:flex;gap:6px;padding:6px 18px 0;flex-wrap:wrap}
 .stab{padding:5px 11px;border-radius:6px;background:#102b35;cursor:pointer;border:1px solid #1d4450;font-size:12px}
 .stab.active{background:var(--orange);border-color:var(--orange);color:#fff;font-weight:600}
 .wrap{max-height:70vh;overflow:auto;margin:8px 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 8px;border-bottom:1px solid #143;white-space:nowrap;text-align:left}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase;z-index:1}
 td.r,th.r{text-align:right}
 tr:hover td{background:#10323e}
 .turf{color:#9fe0b0;font-weight:600}.dirt{color:#d8a06a;font-weight:600}
 .off{color:#789;font-family:ui-monospace,Consolas,monospace;font-size:11px}
 .jp{font-size:14px}
 .hint{color:#9ab;font-size:12px;padding:0 18px 4px}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
 .meta{display:flex;gap:14px;flex-wrap:wrap;padding:6px 18px;color:#bcd;font-size:12px}
 .meta b{color:var(--sand)}
 .map{margin:8px 18px;border:1px solid #143;border-radius:6px;overflow:hidden;display:none}
 .map.show{display:block}
 .nomark{color:#c88;font-style:italic}
</style></head><body>
<header><h1>🏁 DOC Tracks &amp; G1 Calendar <span class="sub">doc-core · courses + G1 races · all 4 versions · byte-verified display tables</span></h1></header>
<div class="bar">
 <span id="tabs"></span>
 <input class="search" id="q" placeholder="Search venue / race / distance…">
 <label>Surface <select id="fsurf"><option value="">all</option><option>TURF</option><option>DIRT</option></select></label>
 <button class="sec" onclick="toggleMap()">🗺 Venue Map</button>
 <button class="sec" onclick="exp('csv')">⬇ CSV</button>
 <button class="sec" onclick="exp('json')">⬇ JSON</button>
 <span class="pill" id="count"></span>
</div>
<div class="meta" id="meta"></div>
<div class="sub-tabs" id="subtabs"></div>
<div class="hint" id="hint"></div>
<div class="map" id="mapbox"></div>
<div class="wrap"><table id="t"></table></div>
<script>
const DATA = __PAYLOAD__;
const VERS = Object.keys(DATA.versions);
const SECTION_LABELS = {course:'Course List',display:'Display Names',g1:'G1 Races',special:'Special',handicap:'Handicap'};
let cur = VERS[0], curSec = 'course', sortKey='offset', sortDir=1;
const $=s=>document.querySelector(s);

function curSections(){ return DATA.versions[cur].sections; }
function isCourse(sec){ return sec==='course'||sec==='display'; }

function entries(){
 const sec = curSections()[curSec];
 if(!sec) return [];
 const q=$('#q').value.toLowerCase().trim(), fsurf=$('#fsurf').value;
 let rows = sec.entries.map((e,i)=>({idx:i, ...e}));
 rows = rows.filter(e=>{
   const hay=((e.text||'')+' '+(e.venue||'')+' '+(e.surface||'')+' '+(e.distanceM||'')).toLowerCase();
   const okq = !q || hay.includes(q);
   const oks = !fsurf || (isCourse(curSec) ? e.surface===fsurf : (e.text||'').toUpperCase().includes(fsurf));
   return okq && oks;
 });
 const get=e=>{switch(sortKey){
   case 'offset': return parseInt(e.offset,16);
   case 'idx': return e.idx;
   case 'text': return e.text||'';
   case 'venue': return e.venue||'';
   case 'surface': return e.surface||'';
   case 'distanceM': return e.distanceM||0;
   default: return e.idx;}};
 rows.sort((a,b)=>{const x=get(a),y=get(b);return (x<y?-1:x>y?1:0)*sortDir;});
 return rows;
}

function render(){
 const rows=entries(), course=isCourse(curSec);
 const COLS = course
   ? [['idx','#'],['venue','Venue'],['surface','Surf'],['distanceM','Dist (m)'],['text','Display text'],['offset','Offset']]
   : [['idx','#'],['text','Race / label'],['offset','Offset']];
 let h='<thead><tr>'+COLS.map(([k,l])=>`<th class="${(k==='distanceM'||k==='idx')?'r':''}" data-k="${k}">${l}</th>`).join('')+'</tr></thead><tbody>';
 for(const e of rows){
   const sc = e.surface==='TURF'?'turf':e.surface==='DIRT'?'dirt':'';
   const noName = (e.text==='NO NAME');
   const txt = noName ? `<span class="nomark">NO NAME (placeholder slot)</span>` : esc(e.text);
   if(course){
     h+=`<tr><td class="r">${e.idx+1}</td><td>${e.venue?esc(e.venue):'<span class=off>?</span>'}</td>`
      +`<td class="${sc}">${e.surface||''}</td><td class="r">${e.distanceM||''}</td>`
      +`<td class="jp">${txt}</td><td class="off">${e.offset}</td></tr>`;
   } else {
     h+=`<tr><td class="r">${e.idx+1}</td><td class="jp">${txt}</td><td class="off">${e.offset}</td></tr>`;
   }
 }
 $('#t').innerHTML=h+'</tbody>';
 $('#count').textContent=`${rows.length} of ${curSections()[curSec]?curSections()[curSec].count:0}`;
 $('#t').querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k; if(sortKey===k)sortDir*=-1; else{sortKey=k;sortDir=1;} render();});
}
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function renderMeta(){
 const v=DATA.versions[cur];
 const bd=v.venueBreakdown;
 const venues=Object.entries(bd.byVenue).filter(([k])=>k!=='?').map(([k,n])=>`${k} ${n}`).join(' · ');
 const surf=Object.entries(bd.bySurface).filter(([k])=>k!=='?').map(([k,n])=>`${k} ${n}`).join(' / ');
 $('#meta').innerHTML =
   `<span><b>${esc(v.label)}</b></span>`
  +`<span>encoding: <b>${v.encoding}</b></span>`
  +`<span>sig@0x8000: <b class=off>${v.sig8000}</b></span>`
  +`<span>courses <b>${v.counts.course}</b></span>`
  +`<span>G1 <b>${v.counts.g1}</b></span>`
  +`<span>special <b>${v.counts.special||0}</b></span>`
  +`<span>handicap <b>${v.hasHandicap?v.counts.handicap:'none'}</b></span>`
  +`<span>venues: ${venues}</span>`
  +`<span>surfaces: ${surf}</span>`;
}
function renderSubtabs(){
 const secs=curSections();
 const order=['course','display','g1','special','handicap'].filter(s=>secs[s]);
 if(!secs[curSec]) curSec=order[0];
 $('#subtabs').innerHTML=order.map(s=>`<span class="stab ${s===curSec?'active':''}" data-s="${s}">${SECTION_LABELS[s]} (${secs[s].count})</span>`).join('');
 $('#subtabs').querySelectorAll('.stab').forEach(t=>t.onclick=()=>{curSec=t.dataset.s; sortKey='offset'; sortDir=1; renderSubtabs(); renderHint(); render();});
}
function renderHint(){
 const tips={
   course:'Compact course list. Surface (TURF/DIRT) and distance are encoded inside the display string itself — there is no per-entry binary attribute byte.',
   display:'Aligned (column-padded) course display names. WE Rev C/D intentionally OMIT NORTHERN PARK & SOUTHERN PARK here; JP ROMs include all venues.',
   g1:'G1 race-name list (display strings only). The per-race grade/purse/month/course binding lives in a separate, not-yet-decoded binary schedule table. WE has a live "NO NAME" placeholder slot.',
   special:'Special-race labels: venues × 2 surfaces.',
   handicap:'Handicap-race labels: venues × 2 surfaces. Added in DOC 2000 — absent in DOC \'99.'
 };
 $('#hint').textContent=tips[curSec]||'';
}

function buildMap(){
 let h='<table><thead><tr><th>WE venue (EN)</th><th>JP venue</th><th>Reading</th><th>Real-world track</th></tr></thead><tbody>';
 for(const v of DATA.venueMap){
   h+=`<tr><td>${esc(v.en)}</td><td class="jp">${esc(v.jp)}</td><td>${esc(v.reading)}</td><td>${esc(v.realTrack)}</td></tr>`;
 }
 $('#mapbox').innerHTML=h+'</tbody></table>';
}
function toggleMap(){ $('#mapbox').classList.toggle('show'); }

function exp(fmt){
 const rows=entries(), v=DATA.versions[cur];
 let blob,name;
 if(fmt==='json'){ blob=new Blob([JSON.stringify(rows,null,1)],{type:'application/json'}); name=`doc-tracks-${cur}-${curSec}.json`; }
 else{
   const course=isCourse(curSec);
   const cols=course?['idx','venue','surface','distanceM','text','offset']:['idx','text','offset'];
   const esc2=x=>`"${String(x==null?'':x).replace(/"/g,'""')}"`;
   const lines=[cols.join(',')].concat(rows.map(r=>cols.map(c=>esc2(c==='idx'?r.idx+1:r[c])).join(',')));
   blob=new Blob(['﻿'+lines.join('\n')],{type:'text/csv;charset=utf-8'}); name=`doc-tracks-${cur}-${curSec}.csv`;
 }
 const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; a.click();
}

// version tabs
$('#tabs').innerHTML=VERS.map(v=>`<span class="tab" data-v="${v}">${esc(DATA.versions[v].tag)}</span>`).join('');
$('#tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  cur=t.dataset.v; $('#tabs').querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t));
  curSec='course'; renderMeta(); renderSubtabs(); renderHint(); render();
});
$('#tabs').firstChild.classList.add('active');
['q','fsurf'].forEach(id=>$('#'+id).addEventListener('input',render));
buildMap(); renderMeta(); renderSubtabs(); renderHint(); render();
</script></body></html>"""

out = HTML.replace("__PAYLOAD__", payload)
open(f"{OUT}/tracks-browser.html", "w", encoding="utf-8").write(out)
print(f"wrote {OUT}/tracks-browser.html ({len(out):,} bytes, data embedded)")
