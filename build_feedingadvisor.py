#!/usr/bin/env python3
"""doc-core PLAYER tool: Feeding Advisor. Plain-language "what should I feed?" built on the decoded
44-byte food table (doc_core_food.json). Pick the stat you want to raise -> foods ranked by gain;
or build a feeding plan and see total stat gains. No files, no jargon -> the player door.
"""
import json, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _loader_js import LOADER_JS
OUT = r"C:/DerbyOwnersClub/doc-core"
F = json.load(io.open(f"{OUT}/doc_core_food.json", encoding="utf-8"))
COLS = F["effectColumns"]  # [Speed,Stamina,Sharp,col3,col4,col5,col6]
versions = {}
for vk, vv in F["versions"].items():
    foods = []
    for r in vv["foods"]:
        if r.get("isBeer") and all(x == 0 for x in r["effect"]):
            continue  # hide disabled beer placeholders from the player advisor
        foods.append({"name": r["name"], "eff": r["effect"],
                      "cls": "Feed" if r.get("classFlag") == 1 else "Growth",
                      "rare": "Large" if r.get("rarityFlag") == 1 else "Small"})
    versions[vk] = {"tag": vv["tag"], "label": vv["label"], "foods": foods}
DATA = json.dumps({"cols": COLS, "versions": versions}, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC Feeding Advisor</title>
<style>
 body{margin:0;font:14px/1.5 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:12px 20px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:19px;color:#eae8e2}.sub{color:#7fb0bd;font-size:13px;font-weight:400}
 .wrap{padding:16px 20px;max-width:860px}
 .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}
 select,button{font-size:14px;border-radius:6px;border:1px solid #2a5666;background:#06303a;color:#e8eef0;padding:6px 10px}
 button{background:#014b50;color:#cfe;cursor:pointer;border:0}
 button.on{background:#b75527;color:#fff}
 .big{font-size:15px}
 .card{background:#08202a;border:1px solid #143b48;border-radius:10px;padding:14px;margin:12px 0}
 table{border-collapse:collapse;width:100%}
 th,td{border-bottom:1px solid #143b48;padding:6px 9px;text-align:left}
 th{color:#9cc;font-size:12px;text-transform:uppercase}
 td.n{text-align:center;font-variant-numeric:tabular-nums}
 .gain{color:#7fdca0;font-weight:600}.zero{color:#456}
 .pill{display:inline-block;background:#013;border:1px solid #2a5666;border-radius:12px;padding:1px 9px;font-size:12px;color:#9cc}
 .plus{background:#014b50;color:#cfe;border:0;border-radius:6px;width:26px;cursor:pointer}
 .note{color:#7fb0bd;font-size:13px;margin:6px 0}
 .muted{color:#6f9aa6}
 .planbar{position:sticky;bottom:0;background:#0a242e;border-top:1px solid #143b48;padding:10px 20px;display:flex;gap:16px;flex-wrap:wrap;align-items:center}
 .tot{font-size:15px}
</style></head><body>
<header><h1>&#127822; DOC Feeding Advisor <span class="sub">what to feed to raise your horse's stats</span></h1></header>
<div class="wrap">
 <div class="row big">
  <span>Game version:</span><select id="ver"></select>
  <span style="margin-left:14px">I want to raise:</span>
  <span id="goals"></span>
 </div>
 <div class="card" id="yhCard">
  <div class="row" style="margin:0">
   <label style="cursor:pointer"><span class="pill" style="padding:5px 11px">&#128194; Load your horse (.card / .raw)</span><input id="yhFile" type="file" accept=".card,.raw,.bin" style="display:none"></label>
   <button id="yhClear" style="display:none">&#10007; clear horse</button>
   <span id="yh" class="muted">Optional: load a horse to see its current Speed / Stamina / Sharp and a projected total after your feeding plan. Reads both the new <b>.card</b> and the old <b>.raw</b>.</span>
  </div>
 </div>
 <div class="card">
  <div class="note">Foods ranked by how much they raise your chosen stat. <b>Feed</b> = normal food (use anytime); <b>Growth</b> = special growth items. The three main stats (Speed / Stamina / Sharp) are confirmed; the extra columns are unconfirmed hidden effects and shown faintly.</div>
  <div id="ranked"></div>
 </div>
 <div class="card">
  <h3 style="margin:.2em 0">Feeding plan</h3>
  <div class="note">Tap &#10010; on any food to add it to a plan and see the total stat gain.</div>
  <div id="plan"><span class="muted">no foods added yet</span></div>
 </div>
</div>
<div class="planbar"><span class="tot" id="planTotals">Plan total: &mdash;</span><button id="clearPlan">Clear plan</button></div>
<script>__LOADER__</script>
<script>
const D=__DATA__;const COLS=D.cols;
const $=s=>document.querySelector(s);
let curVer='drbyocwc',goal=0,plan=[],yourHorse=null;
const MAIN=[0,1,2]; // Speed,Stamina,Sharp confirmed
function esc(s){return String(s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
{const v=$('#ver');for(const k in D.versions){const o=document.createElement('option');o.value=k;o.textContent=D.versions[k].tag;v.appendChild(o);}v.value=curVer;}
function goalBtns(){$('#goals').innerHTML=COLS.map((c,i)=>'<button class="g'+(i===goal?' on':'')+'" data-i="'+i+'"'+(i>2?' style="opacity:.6"':'')+'>'+esc(i<3?c:c)+'</button>').join(' ');
 $('#goals').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{goal=+b.dataset.i;goalBtns();renderRanked();}));}
function renderRanked(){
 const foods=D.versions[curVer].foods.slice().map((f,idx)=>({...f,idx})).filter(f=>f.eff[goal]>0).sort((a,b)=>b.eff[goal]-a.eff[goal]);
 if(!foods.length){$('#ranked').innerHTML='<span class="muted">No food in this version raises '+esc(COLS[goal])+'.</span>';return;}
 let h='<table><thead><tr><th></th><th>Food</th><th>Type</th><th class=n>'+esc(COLS[goal])+'</th><th class=n>Spd</th><th class=n>Sta</th><th class=n>Shp</th><th class=n>other</th></tr></thead><tbody>';
 foods.forEach(f=>{
  const other=f.eff.slice(3).map(x=>x).filter(x=>x).join('/')||'&middot;';
  h+='<tr><td><button class="plus" data-idx="'+f.idx+'">+</button></td><td>'+esc(f.name)+'</td><td><span class="pill">'+f.cls+' &middot; '+f.rare+'</span></td>'
   +'<td class="n gain">+'+f.eff[goal]+'</td>'
   +'<td class="n '+(f.eff[0]?'gain':'zero')+'">'+(f.eff[0]?'+'+f.eff[0]:'·')+'</td>'
   +'<td class="n '+(f.eff[1]?'gain':'zero')+'">'+(f.eff[1]?'+'+f.eff[1]:'·')+'</td>'
   +'<td class="n '+(f.eff[2]?'gain':'zero')+'">'+(f.eff[2]?'+'+f.eff[2]:'·')+'</td>'
   +'<td class="n muted">'+other+'</td></tr>';
 });
 $('#ranked').innerHTML=h+'</tbody></table>';
 $('#ranked').querySelectorAll('.plus').forEach(b=>b.addEventListener('click',()=>{plan.push(D.versions[curVer].foods[+b.dataset.idx]);renderPlan();}));
}
function renderPlan(){
 if(!plan.length){$('#plan').innerHTML='<span class="muted">no foods added yet</span>';$('#planTotals').innerHTML='Plan total: &mdash;';return;}
 const counts={};plan.forEach(f=>counts[f.name]=(counts[f.name]||0)+1);
 $('#plan').innerHTML=Object.entries(counts).map(([n,c])=>'<span class="pill" style="margin:2px">'+esc(n)+(c>1?' ×'+c:'')+'</span>').join(' ');
 const tot=[0,0,0,0,0,0,0];plan.forEach(f=>f.eff.forEach((v,i)=>tot[i]+=v));
 $('#planTotals').innerHTML='Plan total: '+MAIN.map(i=>'<b>'+COLS[i]+' +'+tot[i]+'</b>').join(' &nbsp; ')+(tot.slice(3).some(x=>x)?' <span class="muted">(+ other '+tot.slice(3).filter(x=>x).join('/')+')</span>':'');
 if(yourHorse)renderYH();
}
// ---- your horse (load from .card or .raw; show current internals + projected after plan) ----
const _T=69;function _cg(c,t,k){return c[t*_T+(_T-k)];}
const INT_CAP=60; // on-card internal display cap (matches the Stable Management System)
function renderYH(){
 if(!yourHorse){return;}
 const h=yourHorse;
 const tot=[0,0,0,0,0,0,0];plan.forEach(f=>f.eff.forEach((v,i)=>tot[i]+=v));
 const cur={Spd:h.spd,Sta:h.sta,Shp:h.shp};
 // food columns: 0=Speed,1=Stamina,2=Sharp -> map onto the horse's internals
 const add={Spd:tot[0],Sta:tot[1],Shp:tot[2]};
 const cell=(lab,c,a)=>{const proj=Math.min(c+a,INT_CAP);const cap=(c+a)>INT_CAP;
  return '<b>'+lab+'</b> '+c+(a?(' <span class="gain">+'+a+'</span> &rarr; <b>'+proj+'</b>'+(cap?' <span class="muted">(cap '+INT_CAP+')</span>':'')):'');};
 $('#yh').innerHTML='<b style="color:#e8eef0">'+esc(h.name||'(unnamed)')+'</b> <span class="muted">('+h.src+')</span> &nbsp; '
  +cell('Spd',cur.Spd,add.Spd)+' &nbsp; '+cell('Sta',cur.Sta,add.Sta)+' &nbsp; '+cell('Shp',cur.Shp,add.Shp)
  +' &nbsp; <span class="muted">dirt '+h.dirt+'</span>'
  +(plan.length?'':' <span class="muted">&middot; add foods to see the projected total</span>');
}
$('#yhFile').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{const raw=new Uint8Array(r.result),c=DOCcard.normalize(raw);
  if(!c){$('#yh').innerHTML='<span style="color:#f3a">Couldn&rsquo;t read that file &mdash; expected a 207-byte .card or a .raw card export.</span>';return;}
  const k=DOCcard.kind(c);
  if(k==='jp'){$('#yh').innerHTML='<span class="muted">Japanese (DOC 2000/&rsquo;99) card &mdash; identity &amp; pedigree only; stats live in the cabinet, not on the card, so there&rsquo;s nothing to project here. The food rankings above still apply.</span>';yourHorse=null;$('#yhClear').style.display='none';return;}
  if(k!=='us'){$('#yh').innerHTML='<span style="color:#f3a">Unrecognized card (no SEGABEF0 / not a World-Edition card).</span>';return;}
  let nm='';for(let kk=69;kk>=51;kk--){const b=_cg(c,0,kk)&0x7f;if(b>=32&&b<127)nm+=String.fromCharCode(b);}
  yourHorse={name:nm.trim(),spd:Math.min(_cg(c,1,65),INT_CAP),sta:Math.min(_cg(c,1,69),INT_CAP),shp:Math.min(_cg(c,1,61),INT_CAP),dirt:_cg(c,2,61),src:raw.length===207?'.card':'.raw'};
  $('#yhClear').style.display='';renderYH();
 };r.readAsArrayBuffer(f);});
$('#yhClear').addEventListener('click',()=>{yourHorse=null;$('#yhClear').style.display='none';$('#yh').innerHTML='Optional: load a horse to see its current Speed / Stamina / Sharp and a projected total after your feeding plan. Reads both the new <b>.card</b> and the old <b>.raw</b>.';$('#yh').className='muted';});
$('#ver').addEventListener('change',e=>{curVer=e.target.value;plan=[];renderRanked();renderPlan();});
$('#clearPlan').addEventListener('click',()=>{plan=[];renderPlan();});
goalBtns();renderRanked();renderPlan();
</script></body></html>"""
html = HTML.replace("__LOADER__", LOADER_JS).replace("__DATA__", DATA)
open(f"{OUT}/feeding-advisor.html", "w", encoding="utf-8").write(html)
nf = sum(len(v["foods"]) for v in versions.values())
print("wrote feeding-advisor.html (%d bytes), foods=%d across %d versions" % (len(html), nf, len(versions)))
