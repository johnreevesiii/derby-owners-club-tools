#!/usr/bin/env python3
"""doc-core consumer #11: Breeding / Foal PREDICTOR (breeding-lab.html).

Upgrades the basic breeding-browser projector into a real predictor:
  - Monte-Carlo foal DISTRIBUTION (the inheritance rule has RNG noise, so a range is more
    honest than a single expected value): per-stat mean/min/max, sex %, running-style %.
  - The hidden name+44 COMPOSITE surfaced per parent (b0..b3; confirmed independent of all
    visible stats, so it is genuine hidden data: coat/personality/affinity/grade bytes).
  - BEST-MATE FINDER: pick one parent + a target, rank every opposite-kind partner by
    expected foal value.
  - CROSS-VERSION mater name map (same horse across the 4 versions, aligned by stat-tuple).

PROVENANCE: the inheritance engine is the community averaging model (breeding-system.md S6),
isolated in ONE JS function `breedFoal()`. The exact ROM breeding routine + whether name+44
feeds inheritance is the active SH-4 RE item (see _sh4/decode/breeding_routine.md); when that
lands, swap `breedFoal()` + the MODEL.provenance banner. Flagged clearly in the UI.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _loader_js import LOADER_JS
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
BREED = json.load(open(f"{OUT}/doc_core_breeding.json", encoding="utf-8"))

def I(x):
    try: return int(x)
    except Exception: return 0
EN = ['start','corner','oob','competing','tenacious','spurt']
def extvals(r):
    e = r['externals']
    return [I(e[k]) for k in EN] if isinstance(e, dict) else [I(x) for x in e]
def statkey(r):
    return (I(r['st']),I(r['sp']),I(r['sh']),I(r['ac']),tuple(extvals(r)))

# ---- cross-version name map: align records across the 4 versions by stat-tuple ----
# (EN RevC <-> JP 2000 align byte-for-byte e.g. Heart Lake = torottosandaa; Rev D / '99 use
#  partly different stock, so most matches are pairwise, which is itself the correct picture.)
keymap = {}
for vk, v in BREED['versions'].items():
    for r in v['pool']:
        keymap.setdefault(statkey(r), {})[vk] = (r.get('name') or r.get('romaji') or r.get('nameJP') or '?')
# attach an "altNames" list to every record (its name in other versions, if stats match)
for vk, v in BREED['versions'].items():
    for r in v['pool']:
        alt = keymap.get(statkey(r), {})
        r['altNames'] = {k: nm for k, nm in alt.items() if k != vk}

MODEL = {
  "provenance": "Inheritance = the GAME'S REAL formula, decoded byte-verified from the SH-4 foal-build routine FUN_0C052B0C (live-located via in-game breeding capture + static RE; see _sh4/decode/foal_average.md). NOT the old community heuristic. Per-field: internals st/sp/sh = floor((sire+dam)/2) with a +/-5 soft clamp at 45/10 (helper 0x053414); 6 externals = floor((sire+dam)/2); a pedigree bloodline bonus (+1..+3 to internals when enough parent externals clear the >=12 threshold), internals hard-capped at 45; aptitude-banded RNG noise pulls internals down ~5-12 in certain rating bands; sex = rand&1; aptitude/dirt is per-bit RNG-gated inheritance from the parents (NOT averaged). name+44 composite is DEFINITIVELY NOT read by breeding (the whole breeding subsystem never loads a catalog pointer). RNG noise uses the game's exact decoded LCG (see rng).",
  "confidence": "floor-average of internals & externals: 0.95; soft-clamp/cap-45: 0.95; sex=rand&1: 0.95; banded RNG noise: NOW BYTE-EXACT (decompiled FUN_0C052B0C) -- gate = rand&0xFF, two 8-wide bands [92,100) pull-down and [180,188) push-up, ~3.1% each; pedigree bonus: NOW BYTE-EXACT -- the '2nd-line row' is just the sire's own externals, so the count = per-external sire&dam consistency (both>=12 or both<4), cnt 4/5 -> st+1/sp+2/sh+2, 6 -> st+3/sp+2/sh+3, cap 45; fully computable from the two parents. aptitude inheritance: NOW byte-exact LOGIC -- the catalog name+44 COMPOSITE *is* the stored aptitude(+0x32=b2,b3)/style(+0x30=b0,b1) masks; the foal inherits them per-bit via FUN_0c05333e = sire's odd-position bits | dam's even-position bits with 50% neighbor jitter (ac the 0-255 byte is NOT inherited). breedFoal does this exactly on the parents' composites. Remaining gaps (low conf): the catalog-composite -> live-mask populator is unlocated (assumed identity, 0.6), and decoding the inherited mask into a human dirt/turf GRADE needs tables 0x10BE78 (so the shown 'ac' is the aptitude-mask high byte as a proxy). Net: internals/externals/soft-clamp/cap45/sex/noise/pedigree = byte-exact; aptitude inheritance logic byte-exact, only the mask->grade display decode is pending.",
  "rng": "DOC's actual RNG, byte-exact (RE 0.97): state = state*0x41C64E6D + 0x3039 (32-bit LCG, INC=12345); rand15 = (state>>16) & 0x7FFF -> 0..32767; rand_float = rand15/32768. This page's Monte-Carlo uses this exact generator.",
  "vsCommunity": "Corrections to the old community model: (1) aptitude/ac is per-bit RNG inheritance, NOT 'avg +/- 18 + dirt-dynasty'; (2) externals are EXACT floor-averages (no +/-2 at the average step); (3) the apparent '+/-18 on internals' is the cumulative pedigree bonus + banded down-noise, not one uniform draw; (4) internals cap at 45, not 60/65; (5) name+44 composite is unused (confirmed).",
  "addr": {"foalBuild":"0x0C052B0C","internalAvg":"0x0C053414","aptitudeBlend":"0x053154/0x05333E","candidateGen":"0x0C05EF3A","rngFloat":"0x0C091E80"}
}

payload = json.dumps(BREED, ensure_ascii=False)
model = json.dumps(MODEL, ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Breeding Lab (Foal Predictor) — doc-core</title>
<style>
 *{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527}header h1{margin:0;font-size:18px}.sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 select.big{min-width:220px}
 button{background:#b75527;color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600}button.sec{background:#125;border:1px solid #2a5}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0}.tab.active{background:#014b50;border-color:#b75527}
 .card{background:#0a2028;border:1px solid #143;border-radius:8px;margin:10px 12px;padding:12px 16px}
 .card.warn{border-color:#7a5a2a;background:#1a1408;color:#e8d9b0;font-size:12px}
 .grid{display:flex;gap:18px;flex-wrap:wrap}.col{flex:1;min-width:280px}
 h3{margin:0 0 8px;color:#9fe0b0}h4{margin:10px 0 4px;color:#9cc;font-size:12px;text-transform:uppercase}
 .stat{margin:2px 0}.stat b{color:#ffd27a;display:inline-block;min-width:34px}
 .barwrap{display:inline-block;width:150px;height:9px;background:#0a242e;border:1px solid #234;border-radius:5px;vertical-align:middle;overflow:hidden;margin:0 6px}
 .barwrap .bar{height:100%;background:linear-gradient(90deg,#0e6,#9fe0b0)}
 .rng{color:#9ab;font-size:11px}
 .comp{font-family:ui-monospace,Consolas,monospace;font-size:11px;color:#9cc}
 .pa{color:#7ad2ff}.pb{color:#f3a0c8}
 table{border-collapse:collapse;width:100%}th,td{padding:3px 7px;border-bottom:1px solid #143;white-space:nowrap;text-align:right}th.l,td.l{text-align:left}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;font-size:11px;text-transform:uppercase}
 td.name{text-align:left;font-weight:600}tr:hover td{background:#10323e}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
 .alt{color:#9ab;font-size:11px;font-style:italic}
 .wrap{max-height:42vh;overflow:auto;border:1px solid #143;border-radius:6px;margin-top:6px}
</style></head><body>
<header><h1>&#129516; DOC Breeding Lab <span class="sub">doc-core #11 &middot; foal predictor + Monte-Carlo + best-mate finder &middot; all 4 versions</span></h1></header>
<div class="bar">
 <span id="tabs"></span>
 <label>Sire/Parent&nbsp;A <select class="big" id="pa"></select></label>
 <label>Dam/Parent&nbsp;B <select class="big" id="pb"></select></label>
 <label>Rolls <select id="n"><option>200</option><option selected>1000</option><option>5000</option></select></label>
 <button id="run">&#129516; Predict foal</button>
 <label class="pill" style="cursor:pointer">&#128194; A from card<input id="cardA" type="file" accept=".card,.raw,.bin" style="display:none"></label>
 <label class="pill" style="cursor:pointer">&#128194; B from card<input id="cardB" type="file" accept=".card,.raw,.bin" style="display:none"></label>
 <button id="clrCard" style="display:none">&#10007; clear cards</button>
 <span class="sub" id="cardNote"></span>
</div>
<div class="card warn nerd" id="prov"></div>
<div class="card"><div class="grid">
 <div class="col" id="foal"><h3>&#128009; Predicted foal</h3><div id="foalBody" class="rng">Pick two parents and press Predict.</div></div>
 <div class="col" id="parents"><h3>Parents &amp; hidden composite (name+44)</h3><div id="parentBody"></div></div>
</div></div>
<div class="card">
 <h3>&#127942; Best-mate finder</h3>
 <div class="bar" style="padding:0;background:none">
  <label>For <select class="big" id="bmParent"></select></label>
  <label>maximize <select id="bmTarget"><option value="st">Stamina</option><option value="sp">Speed</option><option value="sh">Sharp</option><option value="ac">AC / dirt</option><option value="extT">External total</option><option value="bal">Balanced (st+sp+sh)</option></select></label>
  <button class="sec" id="bmRun">Rank partners</button>
 </div>
 <div class="wrap"><table id="bmTab"></table></div>
</div>
<script>__LOADER__</script>
<script>
const BREED=__PAYLOAD__, M=__MODEL__, $=s=>document.querySelector(s);
const VERS=Object.keys(BREED.versions); let cur=VERS[0];
const EXT=['start','corner','oob','competing','tenacious','spurt'];
const CL=M.clamps;
function pool(){return BREED.versions[cur].pool;}
function nameOf(h){return h.name||h.romaji||h.nameJP||('#'+h.index);}
function ev(h){const e=h.externals;return EXT.map(k=>Array.isArray(e)?e[EXT.indexOf(k)]:+e[k]);}
function clamp(v,lo,hi){return Math.max(lo,Math.min(hi,v));}
// DOC's ACTUAL decoded RNG (RE _sh4/decode/breeding_routine.md): 32-bit LCG, byte-exact.
// state = state*0x41C64E6D + 0x3039; rand15 = (state>>16)&0x7FFF (0..32767); /32768 -> [0,1).
function gameRng(seed){let s=seed>>>0;return function(){s=(Math.imul(s,0x41C64E6D)+0x3039)>>>0;return(((s>>>16)&0x7FFF)/32768);};}
function styleOf(e){ // e = [start,corner,oob,competing,tenacious,spurt]
 const v=[e[0],e[2],e[3],e[4],e[5]]; const range=Math.max(...v)-Math.min(...v);
 if(range<=3)return 'Almighty';
 const g=v.filter(x=>x>e[0]).length;
 return g===0?'Front-runner':g===1?'Start dash':g>=3?'Last spurt':'Stretch-runner';}
function band(v){return v>=13?'◎':v>=9?'○':v>=5?'△':v>=1?'×':'·';}

/* ===== INHERITANCE ENGINE (community averaging model, breeding-system.md S6) =====
   ISOLATED: swap this one function when the SH-4 breeding routine is decoded.
   rng() in [0,1). Returns one rolled foal {st,sp,sh,ac,ext[6],sex,style}. */
// ROM-DECODED (FUN_0C052B0C, byte-verified; see _sh4/decode/foal_average.md).
function soft(v){ if(v>45)v-=5; if(v<10)v+=5; return v; }          // +-5 pull at 45/10 (helper 0x053414)
// BYTE-EXACT pedigree count (FUN_0C052B0C): per external, sire & dam CONSISTENCY -- both >=12 or both <4.
// (The "2nd-line row" 0x21A564-569 is just sire+0x34, not a grandparent; so this needs only the 2 parents.)
function pedCnt(ae,be){ let c=0; for(let i=0;i<6;i++){ if(ae[i]>=12&&be[i]>=12)c++; if(ae[i]<4&&be[i]<4)c++; } return c; }
function applyPed(st,sp,sh,c){                                      // bloodline bonus then hard cap 45
 if(c>=6){ st+=3; sp+=2; sh+=3; } else if(c>=4){ st+=1; sp+=2; sh+=2; }
 return [Math.min(st,45),Math.min(sp,45),Math.min(sh,45)];
}
// Aptitude/style mask inheritance -- BYTE-EXACT logic from FUN_0c05333e: the foal's 16-bit mask =
// SIRE's odd-position bits | DAM's even-position bits, each with a 50% neighbor-shift jitter.
// The catalog name+44 composite IS the stored masks: low half (b0,b1)=style(+0x30), high half (b2,b3)=aptitude(+0x32).
function inheritMask(s,dm,rng){
 let out=0,p=0x8000; for(let k=0;k<8;k++){ let m=s;  if(rng()<0.5)m=(m<<1)&0xFFFF; out|=(m&p); p>>=2; } // sire odd bits
 p=0x4000;            for(let k=0;k<8;k++){ let m=dm; if(rng()<0.5)m=m>>1;          out|=(m&p); p>>=2; } // dam even bits
 return out&0xFFFF;
}
function inheritMaskDet(s,dm){ let out=0,p=0x8000; for(let k=0;k<8;k++){out|=(s&p);p>>=2;} p=0x4000; for(let k=0;k<8;k++){out|=(dm&p);p>>=2;} return out&0xFFFF; }
// gradeFromMask -- BYTE-EXACT decode of FUN_0c0534a4: mask -> aptitude grade index via the ROM
// tables at 0x10BE78 (tableA, idx 0-15) / 0x10BE88 (tableB, idx 16-31), gate-selected nibble.
// (Index is the game's internal grade value; the index->on-screen letter glyph is a further table.)
const GRADE_TBL=[1,3,3,3,2,6,6,5,2,6,6,5,2,4,4,4, 13,15,15,7,12,10,10,11,13,10,10,11,9,14,14,8];
function gradeFromMask(m){
 if((m&0xC000)===0) return GRADE_TBL[16+((m>>4)&0xF)];   // no gate -> tableB via 0x00F0 nibble
 if((m&0x3000)===0) return GRADE_TBL[(m>>8)&0xF];        // gated -> tableA via 0x0F00 nibble
 return 0;
}
function breedFoal(a,b,rng){
 const ae=ev(a),be=ev(b);
 let st=soft((a.st+b.st)>>1), sp=soft((a.sp+b.sp)>>1), sh=soft((a.sh+b.sh)>>1);  // internals = floor-avg + soft clamp
 const ext=ae.map((x,i)=>(x+be[i])>>1);                            // externals = exact floor-avg
 [st,sp,sh]=applyPed(st,sp,sh,pedCnt(ae,be));                      // pedigree bonus + cap 45
 // banded RNG noise -- BYTE-EXACT (FUN_0C052B0C): gate r=rand&0xFF; two 8-wide bands; selector picks a stat
 const r=Math.floor(rng()*256), sel=Math.floor(rng()*4);
 if(r>=92 && r<100){          // band [92,100) ~3.1%: pull DOWN (sel 0/1/2 -> -12 if >15; sel 3 -> all -5 if >15)
   const dn=(x,i)=> ((sel===i||sel===3)&&x>15) ? x-(sel===3?5:12) : x;
   st=dn(st,0); sp=dn(sp,1); sh=dn(sh,2);
 } else if(r>=180 && r<188){  // band [180,188) ~3.1%: push UP if <40 (sel 0/1/2 -> +12; sel 3 -> all +5)
   const up=(x,i)=> ((sel===i||sel===3)&&x<40) ? x+(sel===3?5:12) : x;
   st=up(st,0); sp=up(sp,1); sh=up(sh,2);
 }
 // aptitude/style = inherit the COMPOSITE bitfield per-bit (NOT an ac average -- ac isn't inherited)
 const ca=comp(a), cb=comp(b);
 const fApt=inheritMask((ca[3]<<8)|ca[2],(cb[3]<<8)|cb[2],rng);    // aptitude mask (helper 0x05333e, exact)
 const fSty=inheritMask((ca[1]<<8)|ca[0],(cb[1]<<8)|cb[0],rng);    // style mask (helper 0x053154; gate-clears approximated)
 const composite=[fSty&0xFF,(fSty>>8)&0xFF,fApt&0xFF,(fApt>>8)&0xFF];
 const ac=(fApt>>8)&0xFF;   // dirt-indicator proxy = aptitude-mask high byte; exact grade decode needs tables 0x10BE78
 return {st,sp,sh,ac,ext,composite,sex: rng()<0.5?'M':'F', style:styleOf(ext)};
}
/* deterministic EXPECTED foal (no RNG noise) -- for ranking in the best-mate finder */
function expectFoal(a,b){
 const ae=ev(a),be=ev(b);
 let st=soft((a.st+b.st)>>1), sp=soft((a.sp+b.sp)>>1), sh=soft((a.sh+b.sh)>>1);
 const ext=ae.map((x,i)=>(x+be[i])>>1);
 [st,sp,sh]=applyPed(st,sp,sh,pedCnt(ae,be));
 const ca=comp(a), cb=comp(b);                                     // deterministic (no jitter) aptitude proxy for ranking
 const ac=(inheritMaskDet((ca[3]<<8)|ca[2],(cb[3]<<8)|cb[2])>>8)&0xFF;
 return {st,sp,sh,ac,ext,extT:ext.reduce((p,q)=>p+q,0)};
}

function comp(h){const c=h.composite;return Array.isArray(c)?c:[(c)&255,(c>>8)&255,(c>>16)&255,(c>>24)&255];}
function compHtml(h){const c=comp(h);
 return `<span class="comp">name+44 = [${c.join(', ')}] &nbsp; b0=${c[0]} b1=0x${c[1].toString(16).toUpperCase()} b2=${c[2]} b3=0x${c[3].toString(16).toUpperCase()}</span>`;}
function altHtml(h){const a=h.altNames||{}; const ks=Object.keys(a);
 if(!ks.length)return ''; return `<div class="alt">also: ${ks.map(k=>`${BREED.versions[k].tag}: ${a[k]}`).join(' &middot; ')}</div>`;}

// ---- load a parent from a US .card (internals/externals/dirt; composite not on card -> neutral) ----
const cardP={a:null,b:null};
const _T=69;function _cg(c,t,k){return c[t*_T+(_T-k)];}
function cardParent(c,label){
 let us=c.length===207;if(us)for(let i=0;i<8;i++)if(c[0x8A+i]!=='SEGABEF0'.charCodeAt(i))us=false;
 if(!us)return null;
 let nm='';for(let k=69;k>=51;k--){const b=_cg(c,0,k)&0x7f;if(b>=32&&b<127)nm+=String.fromCharCode(b);}
 return {name:(nm.trim()||label),kind:'card',
  st:Math.min(_cg(c,1,69),60),sp:Math.min(_cg(c,1,65),60),sh:Math.min(_cg(c,1,61),60),ac:_cg(c,2,61),
  externals:{start:_cg(c,1,43)+1,corner:_cg(c,1,42)+1,oob:_cg(c,1,41)+1,competing:_cg(c,1,40)+1,tenacious:_cg(c,1,39)+1,spurt:_cg(c,1,38)+1},
  composite:[0,0,0,0]};
}
function wireCard(inputId,slot){$('#'+inputId).addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{const raw=new Uint8Array(r.result),c=DOCcard.normalize(raw);
  if(!c){$('#cardNote').innerHTML='<span style="color:#ff8a8a">couldn&rsquo;t read that file &mdash; expected a 207-byte .card or a .raw card export</span>';return;}
  const k=DOCcard.kind(c);
  if(k==='jp'){$('#cardNote').innerHTML='<span style="color:#f3c969">Japanese (DOC 2000/&rsquo;99) card &mdash; identity &amp; pedigree only; ability bytes live in the cabinet, not on the card, so it can&rsquo;t seed a parent here. Use a World-Edition card, or pick a horse from the pool.</span>';return;}
  const p=cardParent(c,slot==='a'?'YOUR HORSE A':'YOUR HORSE B');
  if(!p){$('#cardNote').innerHTML='<span style="color:#ff8a8a">unrecognized card (no SEGABEF0 / not a World-Edition card)</span>';return;}
  cardP[slot]=p;$('#clrCard').style.display='';
  $('#cardNote').innerHTML='<span style="color:#7fdca0">'+(slot==='a'?'A':'B')+' = '+p.name+' (from '+(raw.length===207?'.card':'.raw')+')</span> &middot; composite/aptitude approximate for cards';
  predict();};r.readAsArrayBuffer(f);});}
wireCard('cardA','a');wireCard('cardB','b');
$('#clrCard').onclick=()=>{cardP.a=null;cardP.b=null;$('#clrCard').style.display='none';$('#cardNote').textContent='';predict();};
function predict(){
 const A=cardP.a||pool()[+$('#pa').value], B=cardP.b||pool()[+$('#pb').value]; if(!A||!B)return;
 const N=+$('#n').value, rng=gameRng(0x9E3779B1);  // seeded with DOC's actual LCG
 const acc={st:[],sp:[],sh:[],ac:[]}, ext=[[],[],[],[],[],[]]; let male=0; const styles={};
 for(let i=0;i<N;i++){const f=breedFoal(A,B,rng);
  acc.st.push(f.st);acc.sp.push(f.sp);acc.sh.push(f.sh);acc.ac.push(f.ac);
  f.ext.forEach((x,j)=>ext[j].push(x)); if(f.sex==='M')male++; styles[f.style]=(styles[f.style]||0)+1;}
 const ag=a=>{const m=a.reduce((p,q)=>p+q,0)/a.length;return{m:m,lo:Math.min(...a),hi:Math.max(...a)};};
 const row=(lab,a,max)=>{const s=ag(a);return `<div class="stat"><b>${lab}</b> <span class="barwrap"><span class="bar" style="width:${Math.round(100*s.m/max)}%"></span></span> ${s.m.toFixed(1)} <span class="rng">(${s.lo}–${s.hi})</span></div>`;};
 let h=row('ST',acc.st,65)+row('SP',acc.sp,65)+row('SH',acc.sh,65)+row('Apt*',acc.ac,255);
 h+='<h4>Externals (mean band)</h4>';
 h+=EXT.map((e,j)=>{const m=ext[j].reduce((p,q)=>p+q,0)/N;return `${e[0].toUpperCase()}${e.slice(1,3)} ${m.toFixed(1)}${band(Math.round(m))}`;}).join(' &nbsp; ');
 const sl=Object.entries(styles).sort((x,y)=>y[1]-x[1]).map(([k,v])=>`${k} ${(100*v/N).toFixed(0)}%`).join(' &middot; ');
 h+=`<h4>Running style</h4>${sl}<h4>Sex</h4>M ${(100*male/N).toFixed(0)}% &middot; F ${(100*(N-male)/N).toFixed(0)}%`;
 // inherited aptitude/style bitfield (the catalog name+44 composite; per-bit sire-odd/dam-even, +-neighbor jitter)
 const cA=comp(A),cB=comp(B);
 const dApt=inheritMaskDet((cA[3]<<8)|cA[2],(cB[3]<<8)|cB[2]), dSty=inheritMaskDet((cA[1]<<8)|cA[0],(cB[1]<<8)|cB[0]);
 const gF=gradeFromMask(dApt), gS=gradeFromMask((cA[3]<<8)|cA[2]), gD=gradeFromMask((cB[3]<<8)|cB[2]);
 h+=`<div class="nerd"><h4>Aptitude / style (inherited name+44 bitfield)</h4><span class="comp">style 0x${dSty.toString(16).toUpperCase().padStart(4,'0')} &middot; aptitude 0x${dApt.toString(16).toUpperCase().padStart(4,'0')}</span>`
  +`<div class="stat">aptitude grade index — <b>foal ${gF}</b> <span class="rng">(sire ${gS}, dam ${gD}; decoded byte-exact via ROM tables 0x10BE78/88; higher = stronger. Index→on-screen letter glyph is one further table.)</span></div>`
  +`<span class="rng">Masks inherited per-bit: sire odd-bits / dam even-bits (±neighbor jitter). ac (catalog dirt byte) is NOT inherited by breeding.</span></div>`;
 h+=`<div class="rng" style="margin-top:8px">Monte-Carlo over ${N} foals. Bars = mean; (lo–hi) = full rolled range.</div>`;
 $('#foalBody').innerHTML=h;
 // parents panel
 const pp=(h2,cls)=>`<div class="stat ${cls}"><b>${nameOf(h2)}</b> ST${h2.st} SP${h2.sp} SH${h2.sh} AC${h2.ac} &nbsp;<span class="rng">${ev(h2).map((x,i)=>EXT[i][0].toUpperCase()+x+band(x)).join(' ')}</span></div>${compHtml(h2)}${altHtml(h2)}`;
 $('#parentBody').innerHTML=pp(A,'pa')+'<div style="height:8px"></div>'+pp(B,'pb');
}

function bestMate(){
 const P=pool()[+$('#bmParent').value]; if(!P)return; const tgt=$('#bmTarget').value;
 const wantDam = P.kind!=='dam'; // pair a sire with dams and vice versa; mater pool pairs with all others
 const cand=pool().map((h,i)=>[h,i]).filter(([h,i])=>i!==+$('#bmParent').value && (P.kind==='sire'?h.kind!=='sire':P.kind==='dam'?h.kind!=='dam':true));
 const val=f=> tgt==='extT'?f.extT : tgt==='bal'?(f.st+f.sp+f.sh) : f[tgt];
 const ranked=cand.map(([h,i])=>{const f=expectFoal(P,h);return {h,i,f,v:val(f)};}).sort((a,b)=>b.v-a.v).slice(0,15);
 let html='<thead><tr><th class=l>#</th><th class=l>Partner</th><th>foal ST</th><th>SP</th><th>SH</th><th>AC</th><th>extT</th><th class=l>style</th></tr></thead><tbody>';
 ranked.forEach((r,k)=>{const e=r.f.ext; html+=`<tr><td class=l>${k+1}</td><td class=name>${nameOf(r.h)} <span class=rng>(ac${r.h.ac})</span></td><td>${r.f.st}</td><td>${r.f.sp}</td><td>${r.f.sh}</td><td>${r.f.ac}</td><td>${r.f.extT}</td><td class=l>${styleOf(e)}</td></tr>`;});
 $('#bmTab').innerHTML=html+'</tbody>';
}

function fillPickers(){
 const p=pool();
 const opt=(h,i)=>`<option value="${i}">${nameOf(h)} (${h.kind||'mater'}, ac${h.ac})</option>`;
 const sires=p.map((h,i)=>[h,i]).filter(([h])=>h.kind!=='dam');
 const dams =p.map((h,i)=>[h,i]).filter(([h])=>h.kind!=='sire');
 $('#pa').innerHTML=sires.map(([h,i])=>opt(h,i)).join('');
 $('#pb').innerHTML=dams.map(([h,i])=>opt(h,i)).join('');
 $('#bmParent').innerHTML=p.map((h,i)=>opt(h,i)).join('');
}
$('#tabs').innerHTML=VERS.map(v=>`<span class="tab" data-v="${v}">${BREED.versions[v].tag}</span>`).join('');
$('#tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{cur=t.dataset.v;$('#tabs').querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t));fillPickers();predict();});
$('#tabs').firstChild.classList.add('active');
$('#prov').innerHTML='<b>&#9888; Model card.</b> '+M.provenance;
$('#run').onclick=predict; $('#bmRun').onclick=bestMate;
['pa','pb','n'].forEach(id=>$('#'+id).addEventListener('change',predict));
fillPickers(); predict(); bestMate();
</script>
<button id="nerdtog">&#129299; Nerd details</button>
<style>.nerd{display:none}body.shownerd .nerd{display:revert}#nerdtog{position:fixed;right:12px;bottom:12px;z-index:99;background:#0a242e;color:#7fb0bd;border:1px solid #2a5666;border-radius:20px;padding:6px 13px;cursor:pointer;font:12px system-ui}body.shownerd #nerdtog{background:#b75527;color:#fff}</style>
<script>document.getElementById('nerdtog').onclick=function(){var s=document.body.classList.toggle('shownerd');this.innerHTML=s?'&#129299; Nerd details: ON':'&#129299; Nerd details';};</script>
</body></html>"""
out = HTML.replace("__LOADER__", LOADER_JS).replace("__PAYLOAD__", payload).replace("__MODEL__", model)
open(f"{OUT}/breeding-lab.html", "w", encoding="utf-8").write(out)
print(f"wrote {OUT}/breeding-lab.html ({len(out):,} bytes)")
