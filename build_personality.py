#!/usr/bin/env python3
"""doc-core PLAYER tool: Bond & Personality advisor.
Built on the DISASSEMBLED post-race interaction reader (0x0C027F80) + table (0x0E7D20):
  bond_gain = M * (100 - currentBond),  M = table6x5[row*5 + col]
  row = personality tier (>=1,>=5) x runtime flag (0..5); col = response (0..4)
Values + formula are byte-exact (_core/areas/personality-interaction.md). Row character is read from
the values; exact response names + the card-byte->row classifier are flagged inferred.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _loader_js import LOADER_JS
OUT = r"C:/DerbyOwnersClub/doc-core"
# 6x5 interaction multiplier table @file 0x0E7D20 (byte-exact)
TABLE = [
 [1.2,1.5,0.8,2.0,1.0],   # row0  tier0 (Imposing), flag a
 [1.5,1.5,1.2,2.0,1.2],   # row1  tier0, flag b
 [1.0,2.0,0.5,2.0,0.5],   # row2  tier1 (Honest/Rough/Coward/Sloppy), flag a
 [-1.5,-1.0,-0.5,2.0,2.0],# row3  tier1, flag b
 [2.0,2.0,1.0,2.0,1.0],   # row4  tier2 (Too soft), flag a
 [-2.0,-1.2,-1.0,-0.5,2.0],# row5 tier2 (Strict), flag b
]
# character summary derived from each row's values (honest read of the pattern)
ROWCHAR = [
 "Responsive — most responses build the bond",
 "Very responsive — everything works well",
 "Mostly responsive — a couple of weak responses",
 "Selective — affection backfires; only the last two responses help",
 "Loves attention — every response builds the bond",
 "Rejects affection — only the firm response (last) helps; the rest hurt",
]
COLS = ["Hug","Praise","Flatter","Comfort","Scold"]   # INFERRED names/order (flagged)
# 7 Check personalities -> tier (0/1/2). tier picks a pair of rows; flag (runtime) picks within.
PERS_TIER = {"Imposing":0,"Honest":1,"Rough":1,"Coward":1,"Sloppy":1,"Too soft":2,"Strict":2}
TIER_ROWS = {0:[0,1],1:[2,3],2:[4,5]}
# card byte6 -> 8-band -> nearest Check personality
BANDS = [[0,47,"Rough"],[48,63,"Imposing"],[64,111,"Calm"],[112,127,"Firm"],
         [128,175,"Sensitive"],[176,191,"Moody"],[192,239,"Gentle"],[240,255,"Proud"]]
BAND2CHECK = {"Rough":"Rough","Imposing":"Imposing","Calm":"Honest","Firm":"Strict",
              "Sensitive":"Coward","Moody":"Sloppy","Gentle":"Too soft","Proud":"Imposing"}
DATA = json.dumps({"table":TABLE,"rowchar":ROWCHAR,"cols":COLS,"persTier":PERS_TIER,
                   "tierRows":TIER_ROWS,"bands":BANDS,"band2check":BAND2CHECK,
                   "checks":list(PERS_TIER.keys())}, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC Bond & Personality Advisor</title>
<style>
 body{margin:0;font:14px/1.5 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:12px 20px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:19px;color:#eae8e2}.sub{color:#7fb0bd;font-size:13px;font-weight:400}
 .wrap{padding:16px 20px;max-width:900px}
 .card{background:#08202a;border:1px solid #143b48;border-radius:10px;padding:14px;margin:12px 0}
 .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
 select,button{font-size:14px;border-radius:6px;border:1px solid #2a5666;background:#06303a;color:#e8eef0;padding:6px 10px}
 .pill{display:inline-block;background:#014b50;color:#cfe;border-radius:11px;padding:4px 11px;cursor:pointer}
 table{border-collapse:collapse;width:100%;margin-top:6px}
 th,td{border:1px solid #143b48;padding:6px 8px;text-align:center;font-variant-numeric:tabular-nums}
 th{background:#0a242e;color:#9cc;font-size:12px}td.l,th.l{text-align:left}
 .good{background:#0d3a22;color:#7fdca0;font-weight:600}.mid{color:#cdd}.bad{background:#3a1414;color:#ff9a9a;font-weight:600}
 .hl{outline:2px solid #b75527}
 .big{font-size:16px;color:#eae8e2}.muted{color:#6f9aa6}.warn{color:#ffb27f}.ok{color:#7fdca0}
 .note{color:#7fb0bd;font-size:13px;margin:6px 0}
 .flag{background:#241a0a;border:1px solid #5a4420;border-radius:8px;padding:8px 12px;color:#ffd9a8;font-size:12.5px;margin:10px 0}
 code{background:#06303a;padding:1px 5px;border-radius:3px}
</style></head><body>
<header><h1>&#128149; DOC Bond &amp; Personality Advisor <span class="sub">post-race responses that build the bond &mdash; from the disassembled interaction formula</span></h1></header>
<div class="wrap">
 <div class="card">
  <div class="row">
   <label class="pill" style="cursor:pointer">&#128194; Load your horse's .card/.raw<input id="card" type="file" accept=".card,.raw,.bin" style="display:none"></label>
   <span>or pick a personality:</span>
   <select id="pers"></select>
  </div>
  <div id="who" class="note">Load a card to read its personality (byte 6), or pick one above.</div>
 </div>
 <div class="card">
  <div class="note">Bond gain per response = <code>M &times; (100 &minus; current bond)</code> &mdash; <b>M</b> is the table multiplier below (the formula is decoded byte-exact). Bigger M builds the bond faster toward 100; <b>negative M lowers it</b>.</div>
  <div id="advice" class="big muted">&mdash;</div>
  <div id="bars"></div>
 </div>
 <div class="card">
  <h3 style="margin:.2em 0">Full interaction table <span class="muted">(6 personality profiles &times; 5 responses; multiplier M)</span></h3>
  <div id="matrix"></div>
 </div>
 <div class="flag nerd">
  <b>Solid vs inferred:</b> the table <b>values</b>, the <b>6&times;5 shape</b>, and the <b>gain = M&times;(100&minus;bond)</b> formula are decoded byte-exact from the reader at <code>0x0C027F80</code> / table <code>0x0E7D20</code>. The <b>response names</b> (columns) and the <b>card-personality &rarr; profile-row</b> mapping are best-effort <b>inferred</b> (the row is chosen at runtime by a personality tier + a flag we haven't traced). Trust the <i>pattern</i> over the exact label.
 </div>
</div>
<script>__LOADER__</script>
<script>
const D=__DATA__;const $=s=>document.querySelector(s);
let curRow=0;
{const s=$('#pers');D.checks.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;s.appendChild(o);});}
function cls(v){return v>=1.5?'good':v<0?'bad':'mid';}
function setPersonality(check){
 const tier=D.persTier[check]; const rows=D.tierRows[tier];
 // pick the row in this tier whose label best fits (Too soft->row4, Strict->row5; else first)
 curRow = (check==='Strict')?rows[1] : rows[0];
 renderRowPick(check,rows);
 render();
}
function renderRowPick(check,rows){
 $('#who').innerHTML += '';
}
function render(){
 const row=D.table[curRow];
 let bi=0,wi=0;row.forEach((v,i)=>{if(v>row[bi])bi=i;if(v<row[wi])wi=i;});
 const worst=row[wi]<1.0?`avoid <b>${D.cols[wi]}</b> (M&times;${row[wi].toFixed(1)}${row[wi]<0?' — lowers the bond':''})`:'nothing really backfires';
 $('#advice').innerHTML=`<b>${D.rowchar[curRow]}.</b> Best response: <span class="ok">${D.cols[bi]} (M&times;${row[bi].toFixed(1)})</span>; ${worst}.`;
 let h='<table><thead><tr><th class=l>Response</th><th>M</th><th class=l></th></tr></thead><tbody>';
 row.map((v,i)=>[v,i]).sort((a,b)=>b[0]-a[0]).forEach(([v,i])=>{
  const w=Math.round(Math.abs(v)/2*100);
  h+=`<tr><td class="l ${cls(v)}">${D.cols[i]}</td><td class="${cls(v)}">&times;${v.toFixed(1)}</td><td class="l"><span style="display:inline-block;height:10px;width:${w}%;background:${v<0?'#b73':'#2a7'};border-radius:3px"></span></td></tr>`;
 });
 $('#bars').innerHTML=h+'</tbody></table>';
 let m='<table><thead><tr><th class=l>Profile</th>'+D.cols.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>';
 D.table.forEach((r,ri)=>{m+=`<tr class="${ri===curRow?'hl':''}"><td class="l" title="${D.rowchar[ri]}">${ri}</td>`+r.map(v=>`<td class="${cls(v)}">${v.toFixed(1)}</td>`).join('')+'</tr>';});
 $('#matrix').innerHTML=m+'</tbody></table>';
}
$('#pers').addEventListener('change',e=>setPersonality(e.target.value));
const T=69;function cg(c,t,k){return c[t*T+(T-k)];}
function band(v){for(const[a,b,n]of D.bands)if(v>=a&&v<=b)return n;return '?';}
$('#card').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{const raw=new Uint8Array(r.result),c=DOCcard.normalize(raw);
  if(!c){$('#who').innerHTML='<span class="warn">Couldn&rsquo;t read that file &mdash; expected a 207-byte .card or a .raw card export.</span>';return;}
  const kk=DOCcard.kind(c);
  if(kk==='jp'){$('#who').innerHTML='<span class="warn">Japanese (DOC 2000/&rsquo;99) card &mdash; personality lives in the cabinet save, not on the card, so it can&rsquo;t be read here. Pick the personality above to explore its table.</span>';return;}
  if(kk!=='us'){$('#who').innerHTML='<span class="warn">Unrecognized card (no SEGABEF0 / not a World-Edition card).</span>';return;}
  const b6=cg(c,0,6);const bd=band(b6);const chk=D.band2check[bd]||'Imposing';
  let nm='';for(let k=69;k>=51;k--){const x=cg(c,0,k)&0x7f;if(x>=32&&x<127)nm+=String.fromCharCode(x);}
  $('#pers').value=chk;setPersonality(chk);
  $('#who').innerHTML=`<span class="ok">${nm.trim()||'(card)'}</span> <span class="muted">(from ${raw.length===207?'.card':'.raw'})</span> &mdash; personality byte ${b6} = <b>${bd}</b> &rarr; <b>${chk}</b> profile <span class="muted">(band&rarr;profile inferred; runtime flag may pick the sibling profile)</span>.`;
 };r.readAsArrayBuffer(f);});
setPersonality(D.checks[0]);
</script>
<button id="nerdtog">&#129299; Nerd details</button>
<style>.nerd{display:none}body.shownerd .nerd{display:revert}#nerdtog{position:fixed;right:12px;bottom:12px;z-index:99;background:#0a242e;color:#7fb0bd;border:1px solid #2a5666;border-radius:20px;padding:6px 13px;cursor:pointer;font:12px system-ui}body.shownerd #nerdtog{background:#b75527;color:#fff}</style>
<script>document.getElementById('nerdtog').onclick=function(){var s=document.body.classList.toggle('shownerd');this.innerHTML=s?'&#129299; Nerd details: ON':'&#129299; Nerd details';};</script>
</body></html>"""
html = HTML.replace("__LOADER__", LOADER_JS).replace("__DATA__", DATA)
open(f"{OUT}/personality-advisor.html","w",encoding="utf-8").write(html)
print("wrote personality-advisor.html (%d bytes)" % len(html))
