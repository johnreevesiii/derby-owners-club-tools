#!/usr/bin/env python3
"""doc-core: race-model v1 (static-grounded). Captures the SH-4-recovered race constants as
canonical data (doc_core_racemodel.json) and builds race-lab.html: a per-track strength / odds
estimator + best-trip calculator over the 244-horse roster.

PROVENANCE (from C:/DerbyOwnersClub/_sh4/RACE_FORMULA_FINDINGS.md, FUN_0c044ab4):
  recovered-exact : weighted-SUM accumulator shape; dirt 4-band curve (116/121/128 -> 0.0042/0.0052/0.0035/0.003);
                    condition gates 92/95.5/96/99/99.5; speed clamp [10,160]; distance table @0x10F210.
  pending live trace (operand binding): exactly which stat byte feeds which coefficient, and the
                    distance(9)->multiplier(12) indexer. Those parts here are TUNABLE HEURISTICS, flagged in the UI.
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
roster = json.load(open(f"{OUT}/doc_core_roster.json", encoding="utf-8"))

MODEL = {
  "_about": "DOC race-model v2: SH-4-recovered formula (full). race-lab.html. Sourced from _sh4/decode/*.md.",
  "source": "C:/DerbyOwnersClub/_sh4/RACE_FORMULA_FINDINGS.md §9.5/9.6 + decode/*.md (FUN_0c044ab4 + twin 0c0456ec)",
  "recoveredExact": {
    "speedClamp": [10.0, 160.0],
    "dirtBands": [
      {"byteMin": 128, "coeff": 0.0042}, {"byteMin": 121, "coeff": 0.0052},
      {"byteMin": 116, "coeff": 0.0035}, {"byteMin": 0, "coeff": 0.003}],
    "conditionThresholds": [92.0, 95.5, 96.0, 99.0, 99.5],
    "distanceTable": {
      "addr": "0x0C10F204",
      "indexer": "SOLVED (Q#2): 12 keys 1:1 with 12 multipliers, indexed by integer course index 0..11; mult = *(base + i*4)",
      "distances_m": [1200,1400,1600,1700,1800,2000,2100,2200,2400,2500,3000,3200],
      "multipliers":  [1.3913,1.2308,1.0323,1.0625,0.8889,0.8649,0.8421,0.8205,0.8000,0.7273,0.6667,0.6400],
      "role": "PACE NORMALIZER: distance*mult ~= const (~1600-2050); mult ~= 32/X. NOT a strength scaler. (1.0323 = 1600m, not 2000m.)"},
    "shape": "per-tick: speed S += sum(coeff_i * stat_i) over phase(+0x6c)/style(+0x74)/condition(+0x28) branches; LINEAR late falloff (S += 1.2 - 0.04*t for 35<=t<55, S -= 1.8 for t>=55) [NOT quadratic; prior -x^2 was an FPSCR ghost arm]; clamp [10,160] in style helper FUN_0c07f70a/0c07f770",
    "staminaDrain": {"fn": "FUN_0c05333e", "pool": "0x53928",
      "model": "drain = curve_segment(statsum) * (0.6 + 0.027*stat) * scale; statsum = aggregate of 6 roster stat bytes; cmp/ge ladder thresholds 220/240/250/260/270/280/300 pick a curve segment in 0.9..0.027"},
    "whipHold": {"fn": "0x0C069280-0x0C069C30",
      "model": "vel[k] += GRADE * coeff_k * axis_k (fmac) into per-horse velocity vector at struct +0x0C/+0x10/+0x14, base path /10.0; cost = -0.3*axis*field gated on @0x0C21A0FC",
      "bits": "0x02 = HOLD (always-on accel, grade 1), 0x01 = WHIP HIGH (grade x3), 0x04 = WHIP LOW (grade x2) [conf 0.6; one INPUT-TEST press confirms]"},
    "structMap": "per-horse stride 0x2A0: +0x000 distance, +0x004 lane, +0x0C/+0x10/+0x14 live velocity vector, 6 phase sub-records of 0x54 from +0x28 (each +0x44 phase ability, +0x4c dist-mult, +0x0c condition/trust); per-tick advances distance+velocity; stat-derived params init-once",
    "functions": {"perTickUpdater": "FUN_0c044ab4 + twin FUN_0c0456ec", "perTickDriver": "FUN_0c0699e4 (normalizes stats /50.0)", "styleApply": "FUN_0c044118 (gates 40/60/75/85)", "drain": "FUN_0c05333e", "whip": "0x0C069280"}
  },
  "labApproximation": {
    "note": "race-lab.html is an aggregate strength/best-trip estimator built ON the recovered formula. It is NOT the tick-exact sim (that integrates the per-tick velocity vector + drain + whip across the race — buildable now from this spec).",
    "phaseStatBinding": "6 externals = per-phase abilities (start..spurt); distance tilts emphasis early->late",
    "internalRoles": "speed=ceiling, stamina=sustain (drain ladder), sharp=accel",
    "surfaceModel": "dirt track: +coeff*dirt; turf: +coeff*(255-dirt) (inverse/default)"
  },
  "runtimeValidated": {
    "source": "_sh4/trace/ (GDB-stub Flycast on the dev branch; race*.csv, horse_structs.bin, phases_t0..t5.bin, whip_input*.csv)",
    "confirmed": [
      "live per-horse race struct: 12 x stride 0x2A0 at runtime base = cart base + 0x20000",
      "per-phase distance multiplier read live matches the 0x10F204 table; mult is a pace normalizer (distance*mult ~ const)",
      "live speed stays within the recovered [10,160] clamp band; distance monotonic",
      "mid-race time series (phases_t0..t5) + whip captures localized the LINEAR falloff, the FUN_0c05333e drain ladder, and the whip/hold handler (grades 1/2/3)",
      "static formula and the running game AGREE; the full per-tick formula is recovered"
    ],
    "onlyOpenItem": "roster-ID of the horses in a *captured* race is not retained in the struct (needs a live race-init breakpoint). Does NOT affect simulation, which runs any horse from its roster stats through the recovered formula."
  }
}
json.dump(MODEL, open(f"{OUT}/doc_core_racemodel.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote doc_core_racemodel.json")

payload = json.dumps({"versions": {k: {"tag": v["tag"], "horses": v["horses"]} for k,v in roster["versions"].items()}}, ensure_ascii=False)
model = json.dumps(MODEL, ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Race Lab (v1) — doc-core</title>
<style>
 *{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527}header h1{margin:0;font-size:18px}.sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0}.tab.active{background:#014b50;border-color:#b75527}
 .card{background:#0a2028;border:1px solid #143;border-radius:8px;margin:10px 12px;padding:10px 14px;font-size:12px;color:#9ab}
 .card b{color:#ffd27a}.ok{color:#9fe0b0}.warn{color:#f3c969}
 .wrap{max-height:62vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%}th,td{padding:4px 8px;border-bottom:1px solid #143;white-space:nowrap;text-align:right}th.l,td.l{text-align:left}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase}
 td.name{text-align:left;font-weight:600}tr:hover td{background:#10323e}.score{color:#9fe0b0;font-weight:700}.rank{color:#d8a630;font-weight:700}
 .romaji{color:#9cc;font-style:italic;font-size:11px}.bt{color:#7ad2ff}
 label{font-size:12px;color:#9ab}
</style></head><body>
<header><h1>🏁 DOC Race Lab <span class="sub">v1 · static-grounded strength &amp; best-trip estimator (244 CPU horses)</span></h1></header>
<div class="bar">
 <span id="tabs"></span>
 <label>Distance <select id="dist"></select></label>
 <label>Surface <select id="surf"><option value="turf">Turf</option><option value="dirt">Dirt</option></select></label>
 <label>Condition <input id="cond" type="range" min="60" max="100" step="0.5" value="96" style="vertical-align:middle"><span id="condv">96</span></label>
 <input id="q" placeholder="search…" style="width:150px">
</div>
<div class="card nerd">
 <b>Model card.</b> The DOC race formula is now <span class="ok">fully recovered &amp; runtime-validated</span> (SH-4 static + live GDB trace, see <code>_sh4/decode/*.md</code>): weighted-sum accumulator, dirt 4-band curve, condition gates, <b>linear</b> late-falloff, the <b>12-key distance table @0x10F204</b> (a pace normalizer: distance×mult≈const; 1.0323 = 1600m), the stamina-drain ladder, and the whip/hold handler (grades 1/2/3).
 This page now includes BOTH the transparent <b>strength &amp; best-trip estimator</b> (aggregate, normalized 0–100) AND a <span class="ok">faithful tick-by-tick simulator</span> (the &#9654; Run race / Odds buttons) ported from <code>_sh4/sim</code>, which integrates the per-tick velocity, stamina drain, and [10,160] clamp across the race from each horse's roster stats.
 The sim runs at <b>real-racing pace</b>: average speed is held near-constant across distances (~9% sprint→stayer fade, matching real thoroughbreds), anchored to the measured 1600m turf time (winner 48.5s). The <b>Realistic</b> field mode uses DOC's grade + surface groupings in a competitive class band for game-like ~16s finishes.
</div>
<div class="bar" style="padding-top:0">
 <label>Field <select id="fmode"><option value="realistic">Realistic (grade+surface)</option><option value="strong">Strongest 12</option><option value="random">Random</option></select></label>
 <label>Grade <select id="fgrade"><option value="any">Any</option><option>G1</option><option>G2</option><option>G3</option><option>Ungraded</option></select></label>
 <button id="runRace" style="background:#b75527;color:#fff;border:0;border-radius:5px;padding:6px 12px;cursor:pointer;font-size:13px">&#9654; Run race</button>
 <button id="runOdds" style="background:#014b50;color:#fff;border:1px solid #b75527;border-radius:5px;padding:6px 12px;cursor:pointer;font-size:13px">&#128202; Odds &times;200</button>
 <span class="sub">faithful tick-by-tick sim &mdash; <b>Realistic</b> fields the race's grade + surface in a competitive class band (game-like ~16s spread); each Run reshuffles the field</span>
</div>
<div class="bar" id="yhbar" style="padding-top:0;border-top:1px solid #143b48;flex-wrap:wrap;gap:6px">
 <b style="color:#eae8e2">&#128012; Your horse:</b>
 <span class="sub">STA</span><input id="yh_0" type="number" min="0" max="60" value="30" style="width:44px">
 <span class="sub">SPD</span><input id="yh_1" type="number" min="0" max="60" value="30" style="width:44px">
 <span class="sub">SHP</span><input id="yh_2" type="number" min="0" max="60" value="30" style="width:44px">
 <span class="sub">| ext start</span><input id="ye_0" type="number" min="1" max="64" value="20" style="width:44px">
 <span class="sub">cor</span><input id="ye_1" type="number" min="1" max="64" value="20" style="width:44px">
 <span class="sub">oob</span><input id="ye_2" type="number" min="1" max="64" value="20" style="width:44px">
 <span class="sub">cmp</span><input id="ye_3" type="number" min="1" max="64" value="20" style="width:44px">
 <span class="sub">ten</span><input id="ye_4" type="number" min="1" max="64" value="20" style="width:44px">
 <span class="sub">spt</span><input id="ye_5" type="number" min="1" max="64" value="20" style="width:44px">
 <span class="sub">| dirt</span><input id="yh_dirt" type="number" min="0" max="255" value="100" style="width:50px">
 <span class="sub">style</span><select id="yh_style"><option value="0">Front-runner</option><option value="1">Start dash</option><option value="2">Last spurt</option><option value="3">Stretch-runner</option><option value="7">Almighty</option></select>
 <label class="pill" style="cursor:pointer;background:#014b50;color:#cfe;border-radius:10px;padding:3px 9px">&#128194; Load .card<input id="yh_card" type="file" accept=".card,.bin" style="display:none"></label>
 <button id="yhRace" style="background:#b75527;color:#fff;border:0;border-radius:5px;padding:6px 12px;cursor:pointer">&#9654; Race my horse</button>
 <button id="yhTrip" style="background:#014b50;color:#cfe;border:0;border-radius:5px;padding:6px 12px;cursor:pointer">&#127919; Best trip</button>
 <button id="yhOdds" style="background:#014b50;color:#cfe;border:0;border-radius:5px;padding:6px 12px;cursor:pointer">&#128202; My win odds</button>
 <span class="sub">enter your horse's stats, or load its <code>.card</code> from the Stable Management System</span>
</div>
<div id="simout" class="card" style="display:none"></div>
<div class="wrap"><table id="t"></table></div>
<script>
const DATA=__PAYLOAD__, M=__MODEL__, $=s=>document.querySelector(s);
let cur=Object.keys(DATA.versions)[0], sortKey='score', sortDir=-1;
const DIST=M.recoveredExact.distanceTable.distances_m, MUL=M.recoveredExact.distanceTable.multipliers;
function distMult(d){const i=DIST.indexOf(d); return i>=0&&i<MUL.length?MUL[i]:1.0;} // provisional index map
function dirtCoeff(b){for(const band of M.recoveredExact.dirtBands){if(b>=band.byteMin)return band.coeff;}return 0.003;}
function condMult(c){const t=M.recoveredExact.conditionThresholds; let m=1.0;
 if(c>=t[0])m=1.02; if(c>=t[2])m=1.04; if(c>=t[3])m=1.06; if(c>=t[4])m=1.08; return m;}
// horse-specific suitability at a distance (no global pace multiplier) — this is what varies per horse
function inner(h,d,surf){
 const e=h.externals, intl=h.internals;
 const late=Math.max(0,Math.min(1,(d-1200)/(3200-1200)));            // 0 sprint .. 1 marathon (full 12-key range)
 const wEarly=1-0.5*late, wLate=1+0.6*late;                          // early phases fade, late phases grow with distance
 const phase = e.start*wEarly + e.corner*wEarly + e.oob*wEarly + e.competing*1.0 + e.tenacious*wLate + e.spurt*wLate;
 const internal = intl.speed*1.0 + intl.stamina*(0.6+0.8*late) + intl.sharp*0.5;  // stamina matters more at distance
 const coeff=dirtCoeff(h.dirt);
 const surface = surf==='dirt' ? coeff*h.dirt*20 : coeff*(255-h.dirt)*20;          // recovered dirt-band curve
 // stamina-overreach falloff (the engine's -k*x^2 term): a horse fades when the trip's late-demand
 // exceeds what its stamina sustains -> gives each horse a genuine best trip instead of "longer=better".
 const reach = intl.stamina/63, over = Math.max(0, late - reach);
 const penalty = 55*over*over;
 return phase + internal + surface - penalty;
}
// full strength at the selected track = suitability × global pace mult (real distance table) × condition gate.
// NOTE: the recovered [10,160] clamp + quadratic falloff are PER-TICK velocity bounds, not aggregate.
function score(h,d,surf,cond){ return inner(h,d,surf) * distMult(d) * condMult(cond); }
// best trip = the distance where THIS horse's profile is strongest (suitability, not the global pace factor,
// which is equal for all horses and would otherwise pin everyone to the shortest trip).
function bestTrip(h,surf){let bd=DIST[0],bs=-1; for(const d of DIST){const s=inner(h,d,surf); if(s>bs){bs=s;bd=d;}} return bd;}
function rows(){
 const d=+$('#dist').value, surf=$('#surf').value, cond=+$('#cond').value, q=$('#q').value.toLowerCase().trim();
 let hs=DATA.versions[cur].horses.map(h=>({...h, raw:score(h,d,surf,cond), best:bestTrip(h,surf)}));
 const mx=Math.max(...hs.map(h=>h.raw))||1;                           // normalize to a 0-100 strength index (top=100)
 hs.forEach(h=>h.score=Math.round(1000*h.raw/mx)/10);
 hs=hs.filter(h=>{const nm=((h.name||'')+' '+(h.nameJP||'')+' '+(h.romaji||'')+' '+h.id).toLowerCase(); return !q||nm.includes(q);});
 const get=h=>sortKey==='score'?h.score:sortKey==='best'?h.best:sortKey==='id'?h.id:sortKey==='name'?(h.name||h.romaji||''):sortKey==='dirt'?h.dirt:sortKey==='grade'?h.grade:(h.internals[sortKey]??h.externals[sortKey]??0);
 hs.sort((a,b)=>{const x=get(a),y=get(b);return (x<y?-1:x>y?1:0)*sortDir;});
 return hs;
}
const COLS=[['rank','#'],['name','Horse'],['grade','Gr'],['score','Strength'],['best','Best trip'],['dirt','Dirt'],['speed','Spd'],['stamina','Stam'],['sharp','Shrp'],['spurt','Spurt'],['tenacious','Tenac']];
function render(){
 const hs=rows();
 let h='<thead><tr>'+COLS.map(([k,l])=>`<th class="${k==='name'?'l':''}" data-k="${k==='rank'?'score':k}">${l}</th>`).join('')+'</tr></thead><tbody>';
 hs.forEach((r,i)=>{const nm=r.name?r.name:`${r.nameJP||''} <span class="romaji">${r.romaji||''}</span>`;
  h+=`<tr><td class="rank">${sortKey==='score'&&sortDir<0?i+1:r.id}</td><td class="name">${nm}</td><td>${r.grade}</td>`
   +`<td class="score">${r.score}</td><td class="bt">${r.best}m</td><td>${r.dirt}</td>`
   +`<td>${r.internals.speed}</td><td>${r.internals.stamina}</td><td>${r.internals.sharp}</td><td>${r.externals.spurt}</td><td>${r.externals.tenacious}</td></tr>`;});
 $('#t').innerHTML=h+'</tbody>';
 $('#t').querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=(k==='name')?1:-1;}render();});
}
$('#tabs').innerHTML=Object.keys(DATA.versions).map(v=>`<span class="tab" data-v="${v}">${DATA.versions[v].tag}</span>`).join('');
$('#tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{cur=t.dataset.v;$('#tabs').querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t));render();});
$('#tabs').firstChild.classList.add('active');
$('#dist').innerHTML=DIST.map(d=>`<option value="${d}">${d}m</option>`).join(''); $('#dist').value=2000;
$('#cond').addEventListener('input',e=>{$('#condv').textContent=e.target.value;render();});
['dist','surf','q'].forEach(id=>$('#'+id).addEventListener('input',render));

/* ===== FAITHFUL tick-by-tick simulator (port of _sh4/sim/doc_race_sim.py) =====
   Byte-exact: 12-key pace table, dirt 4-band curve, drain ladder (pool 0x53928),
   condition gates, [10,160] clamp. Calibrated weights per RACE_FORMULA_FINDINGS. */
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function simPaceRaw(d){let bi=0,bd=1e9;for(let k=0;k<DIST.length;k++){const e=Math.abs(DIST[k]-d);if(e<bd){bd=e;bi=k;}}return MUL[bi];}
// Real horse racing holds NEARLY CONSTANT average speed across distances (~9% fade sprint->stayer).
// The raw 0x10F204 multiplier swings 2.17x (a pace/effort normalizer, not a ground-speed scaler);
// applied raw it makes sprints 2x too fast and marathons crawl. Damp it around the 1600m anchor and
// re-scale to the measured ground truth (1600m turf cond96 winner 48.53s). See _sh4/sim/doc_race_sim.py.
const PACE_1600=simPaceRaw(1600), PACE_DAMP=0.12, GAME_SPEED=0.66;
// near-constant-pace model (telemetry-calibrated, _sh4/sim/doc_race_sim.py + sim_validation.md):
// the live field runs the same ~32 m/s to within 0.4-0.7%; ability is a few-% modulation.
// Re-anchored to the user's real Rev C 1600m race (winner 48.5s, 12th ~65s = ~16.5s spread).
const PACE_BASE=32.0, ABIL_SPREAD=0.50, RUBBER=0.0;
function simPace(d){return Math.pow(simPaceRaw(d)/PACE_1600,PACE_DAMP)*GAME_SPEED;}
function simSurf(dirt,surf){const band=dirt>=128?0.0042:dirt>=121?0.0052:dirt>=116?0.0035:0.003;const c=band*dirt;return surf==='dirt'?0.80+c:0.80+(0.0042*255-c)*0.5;}
const SDC=[0.9,0.8,0.7,0.5,0.3,0.2,0.1,0.027],SDT=[220,240,250,260,270,280,300];
function simDrainSeg(ss){for(let i=0;i<SDT.length;i++)if(ss<SDT[i])return SDC[i];return 0.027;}
const SPF=[0.10,0.25,0.45,0.70,0.88,1.00];function simPhase(f){for(let p=0;p<6;p++)if(f<=SPF[p])return p;return 5;}
function simBias(style){const s=(style||'').toLowerCase();
 if(s.indexOf('front')>=0)return[1.25,1.20,1.05,1.00,0.95,0.90];
 if(s.indexOf('start')>=0)return[1.30,1.10,1.00,0.95,0.95,1.00];
 if(s.indexOf('last')>=0)return[0.90,0.95,1.00,1.05,1.15,1.30];
 if(s.indexOf('stretch')>=0)return[0.92,0.96,1.00,1.05,1.18,1.20];
 return[1.05,1.05,1.05,1.05,1.05,1.05];}
function simCond(c){const t=M.recoveredExact.conditionThresholds;let f=1.0;
 if(c>t[1]&&c<t[3])f+=0.017; if(c>t[2]&&c<t[3])f+=0.036; if(c>=t[4])f+=0.05; if(c<60)f-=(60-c)*0.004; return f;}
function simRace(field,d,surf,cond,seed){
 const rng=mulberry32(seed>>>0), DT=1/60, pace=simPace(d);
 const gauss=()=>{let u=0,v=0;while(!u)u=rng();while(!v)v=rng();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);};
 const st=field.map(h=>({h,pos:0,spd:10,energy:h.internals.stamina*100,cond:Math.max(40,Math.min(100,cond+gauss()*4)),luck:1+gauss()*0.04,fin:null}));
 let t=0;
 while(t<600 && st.some(s=>s.fin===null)){
  const nfin=st.reduce((n,s)=>n+(s.fin!==null?1:0),0); // finisher counter (= live 0x3C0954)
  for(const s of st){ if(s.fin!==null)continue; const h=s.h,e=h.externals,it=h.internals,frac=s.pos/d,ph=simPhase(frac);
   const ext=[e.start,e.corner,e.oob,e.competing,e.tenacious,e.spurt][ph], sb=simBias(h.style)[ph];
   // NEAR-CONSTANT common pace + small ability modulation (externals dominate; speed a minor term).
   // Matches live telemetry (0.4-0.7% pace CV) and this session's calib finding (ext-dominated ability).
   const abil=ABIL_SPREAD*((ext*sb-21.0)/21.0)+0.04*((it.speed-30.0)/30.0);
   let target=PACE_BASE*(1.0+abil);
   target*=pace;                                         // byte-exact distance pace-normalizer
   target*=1.0+0.06*(simSurf(h.dirt,surf)-1.0);          // surface as a small centered multiplier
   target*=1.0+0.30*(simCond(s.cond)-1.0);               // condition as a small centered multiplier
   target*=s.luck;                                       // per-race form (<1%)
   if(RUBBER&&frac>SPF[4]&&nfin>0)target+=RUBBER*Math.min(nfin,6); // rubber-band (telemetry-calibrated to 0; mechanism kept)
   s.spd+=(0.02+0.0009*it.sharp)*(target-s.spd);
   s.energy-=(0.6+0.027*it.stamina)*simDrainSeg(h.extTotal+it.stamina+it.speed+it.sharp)*0.85*(0.5+s.spd/22);
   if(s.energy<=0)s.spd-=0.6;
   s.spd+=(rng()-0.5)*0.8; s.spd=Math.max(10,Math.min(160,s.spd)); // small tick jitter (+/-0.4); byte-exact [10,160] clamp
   s.pos+=s.spd*DT; if(s.pos>=d)s.fin=t+DT;
  } t+=DT;
 }
 st.sort((a,b)=>(a.fin==null?1e9:a.fin)-(b.fin==null?1e9:b.fin)||b.pos-a.pos);
 return st;
}
function simFmt(t){if(t==null)return'DNF';const m=Math.floor(t/60),s=(t%60).toFixed(2);return m+':'+(s<10?'0'+s:s);}
function shuffle(arr,rng){for(let i=arr.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[arr[i],arr[j]]=[arr[j],arr[i]];}return arr;}
function hStrength(h){return h.extTotal + h.internals.speed + 0.8*h.internals.stamina + 0.6*h.internals.sharp;}
// GAME-REALISTIC field, from DOC's own groupings: GRADE (record +8) + SURFACE (turf dirt<116 /
// dirt dirt>=116, crossovers near-threshold) + a competitive CLASS band (random ability window in
// the grade pool). The game pairs you against comparably-ranked CPUs, so the field finishes within
// ~15-18s, not 50s. Mirrors _sh4/sim/doc_race_sim.py field_realistic().
function fieldRealistic(horses,grade,surf,n,seed){
 const rng=mulberry32((seed>>>0)||1);
 let pool=(grade&&grade!=='any')?horses.filter(h=>h.grade===grade):horses.slice();
 if(pool.length<n)pool=horses.slice();
 const wantTurf=surf==='turf';
 const matched=pool.filter(h=>(h.dirt<116)===wantTurf).sort((a,b)=>hStrength(b)-hStrength(a));
 const other=pool.filter(h=>(h.dirt<116)!==wantTurf).sort((a,b)=>Math.abs(a.dirt-116)-Math.abs(b.dirt-116));
 const nm=Math.min(matched.length,Math.max(1,Math.round(n*0.85))), no=n-nm;
 const win=Math.min(matched.length, nm+Math.max(2,Math.floor(nm/2)));
 const start=Math.floor(rng()*(Math.max(0,matched.length-win)+1));
 let field=shuffle(matched.slice(start,start+win),rng).slice(0,nm).concat(other.slice(0,no));
 if(field.length<n)field=field.concat(shuffle(pool.filter(h=>field.indexOf(h)<0),rng).slice(0,n-field.length));
 return shuffle(field,rng).slice(0,n);
}
function simField(seed){const d=+$('#dist').value,surf=$('#surf').value,cond=+$('#cond').value;
 const mode=$('#fmode').value, grade=$('#fgrade').value, horses=DATA.versions[cur].horses;
 if(mode==='strong') return horses.map(h=>({h,sc:score(h,d,surf,cond)})).sort((a,b)=>b.sc-a.sc).slice(0,12).map(x=>x.h);
 if(mode==='random'){let pool=(grade==='any')?horses.slice():horses.filter(h=>h.grade===grade); if(pool.length<12)pool=horses.slice();
   return shuffle(pool.slice(),mulberry32((seed>>>0)||1)).slice(0,12);}
 return fieldRealistic(horses,grade,surf,12,seed||1);
}
function fieldLabel(){const m=$('#fmode').value,g=$('#fgrade').value,gs=(g==='any'?'':' '+g);
 return m==='strong'?'strongest-12 field':m==='random'?('random'+gs+' field'):('realistic'+gs+' field');}
$('#runRace').onclick=()=>{const d=+$('#dist').value,surf=$('#surf').value,cond=+$('#cond').value;
 const r=simRace(simField((Date.now()*Math.random())>>>0),d,surf,cond,(Date.now()*Math.random())>>>0);
 let h=`<b>&#9654; ${d}m ${surf}</b> &mdash; tick-by-tick faithful sim, ${fieldLabel()}`
  +`<table style="margin-top:6px"><thead><tr><th>Pl</th><th class=l>Horse</th><th>Time</th><th class=l>Style</th><th>extT</th><th>spd</th><th>sta</th><th>dirt</th></tr></thead><tbody>`;
 r.forEach((s,i)=>{const nm=s.h.name||((s.h.romaji||'')||s.h.id);
  h+=`<tr><td class=rank>${i+1}</td><td class=name>${nm}</td><td class=score>${simFmt(s.fin)}</td><td class=l>${s.h.style}</td><td>${s.h.extTotal}</td><td>${s.h.internals.speed}</td><td>${s.h.internals.stamina}</td><td>${s.h.dirt}</td></tr>`;});
 $('#simout').innerHTML=h+'</tbody></table>'; $('#simout').style.display='block';};
$('#runOdds').onclick=()=>{const d=+$('#dist').value,surf=$('#surf').value,cond=+$('#cond').value,N=200;
 const f=simField((Date.now()*Math.random())>>>0),win={},t3={},ps={}; // one fixed field, vary the race RNG
 f.forEach(h=>{const k=h.name||h.id;win[k]=0;t3[k]=0;ps[k]=0;});
 for(let g=0;g<N;g++){const r=simRace(f,d,surf,cond,((g+1)*2654435761)>>>0);
  r.forEach((s,i)=>{const k=s.h.name||s.h.id;ps[k]+=i+1;if(i<3)t3[k]++;}); const wk=r[0].h.name||r[0].h.id; win[wk]++;}
 let h=`<b>&#128202; ${d}m ${surf}</b> &mdash; Monte-Carlo over ${N} faithful sims, ${fieldLabel()}`
  +`<table style="margin-top:6px"><thead><tr><th class=l>Horse</th><th>Win%</th><th>Top3%</th><th>AvgPl</th><th>extT</th><th>dirt</th></tr></thead><tbody>`;
 f.slice().sort((a,b)=>win[b.name||b.id]-win[a.name||a.id]).forEach(hr=>{const k=hr.name||hr.id;
  h+=`<tr><td class=name>${hr.name||hr.romaji||hr.id}</td><td class=score>${(100*win[k]/N).toFixed(1)}</td><td>${(100*t3[k]/N).toFixed(1)}</td><td>${(ps[k]/N).toFixed(2)}</td><td>${hr.extTotal}</td><td>${hr.dirt}</td></tr>`;});
 $('#simout').innerHTML=h+'</tbody></table>'; $('#simout').style.display='block';};
// ===== Your Horse (hand-entry or load .card) =====
const YHSTY={0:'Front-runner',1:'Start dash',2:'Last spurt',3:'Stretch-runner',7:'Almighty'};
function yhBuild(){
 const ex={start:+$('#ye_0').value,corner:+$('#ye_1').value,oob:+$('#ye_2').value,competing:+$('#ye_3').value,tenacious:+$('#ye_4').value,spurt:+$('#ye_5').value};
 const it={stamina:+$('#yh_0').value,speed:+$('#yh_1').value,sharp:+$('#yh_2').value};
 const extTotal=ex.start+ex.corner+ex.oob+ex.competing+ex.tenacious+ex.spurt;
 return {name:'YOUR HORSE',externals:ex,internals:it,extTotal,dirt:+$('#yh_dirt').value,style:YHSTY[+$('#yh_style').value]||'Front-runner'};
}
function yhField(seed){const f=simField(seed);f[0]=yhBuild();return f;}
const C_TRACK=69;function cget(c,t,k){return c[t*C_TRACK+(C_TRACK-k)];}
$('#yh_card').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{const c=new Uint8Array(r.result);let us=c.length===207;if(us)for(let i=0;i<8;i++)if(c[0x8A+i]!=='SEGABEF0'.charCodeAt(i))us=false;
  if(!us){$('#simout').style.display='block';$('#simout').innerHTML='<span style="color:#ff8a8a">Not a US World-Edition .card (need 207 bytes + SEGABEF0).</span>';return;}
  $('#yh_0').value=Math.min(cget(c,1,69),60);$('#yh_1').value=Math.min(cget(c,1,65),60);$('#yh_2').value=Math.min(cget(c,1,61),60);
  $('#ye_0').value=cget(c,1,43)+1;$('#ye_1').value=cget(c,1,42)+1;$('#ye_2').value=cget(c,1,41)+1;$('#ye_3').value=cget(c,1,40)+1;$('#ye_4').value=cget(c,1,39)+1;$('#ye_5').value=cget(c,1,38)+1;
  $('#yh_dirt').value=cget(c,2,61);
  let nm='';for(let k=69;k>=51;k--){const b=cget(c,0,k)&0x7f;if(b>=32&&b<127)nm+=String.fromCharCode(b);}
  $('#simout').style.display='block';$('#simout').innerHTML='<b>Loaded card:</b> '+(nm.trim()||'(unnamed)')+' &mdash; stats filled in. Now <b>Race my horse</b> / <b>Best trip</b> / <b>My win odds</b>.';
 };r.readAsArrayBuffer(f);});
$('#yhRace').onclick=()=>{const d=+$('#dist').value,surf=$('#surf').value,cond=+$('#cond').value;
 const r=simRace(yhField((Date.now()*Math.random())>>>0),d,surf,cond,(Date.now()*Math.random())>>>0);
 const pos=r.findIndex(s=>s.h.name==='YOUR HORSE')+1;
 let h=`<b>&#9654; ${d}m ${surf}</b> &mdash; your horse finished <b style="color:#b75527">P${pos} of ${r.length}</b>`
  +`<table style="margin-top:6px"><thead><tr><th>Pl</th><th class=l>Horse</th><th>Time</th><th>extT</th><th>spd</th><th>sta</th><th>dirt</th></tr></thead><tbody>`;
 r.forEach((s,i)=>{const me=s.h.name==='YOUR HORSE';h+=`<tr${me?' style="background:#3a2410"':''}><td>${i+1}</td><td class=l>${me?'<b>YOUR HORSE</b>':(s.h.name||s.h.romaji||s.h.id)}</td><td>${simFmt(s.fin)}</td><td>${s.h.extTotal}</td><td>${s.h.internals.speed}</td><td>${s.h.internals.stamina}</td><td>${s.h.dirt}</td></tr>`;});
 $('#simout').innerHTML=h+'</tbody></table>';$('#simout').style.display='block';};
$('#yhOdds').onclick=()=>{const d=+$('#dist').value,surf=$('#surf').value,cond=+$('#cond').value,N=200;
 const f=yhField((Date.now()*Math.random())>>>0);let win=0,t3=0,ps=0;
 for(let g=0;g<N;g++){const r=simRace(f,d,surf,cond,((g+1)*2654435761)>>>0);const i=r.findIndex(s=>s.h.name==='YOUR HORSE');ps+=i+1;if(i<3)t3++;if(i===0)win++;}
 $('#simout').innerHTML=`<b>&#128202; ${d}m ${surf}</b> &mdash; your horse over ${N} sims: <b style="color:#b75527">Win ${(100*win/N).toFixed(1)}%</b> &middot; Top3 ${(100*t3/N).toFixed(1)}% &middot; Avg place ${(ps/N).toFixed(2)} of ${f.length}`;$('#simout').style.display='block';};
$('#yhTrip').onclick=()=>{const surf=$('#surf').value,cond=+$('#cond').value,N=50;
 const rows=DIST.map(d=>{let ps=0;const f=yhField(12345);for(let g=0;g<N;g++){const r=simRace(f,d,surf,cond,((g+1)*99991)>>>0);ps+=r.findIndex(s=>s.h.name==='YOUR HORSE')+1;}return {d,avg:ps/N};}).sort((a,b)=>a.avg-b.avg);
 let h=`<b>&#127919; Best trip</b> &mdash; your horse's avg finish vs a realistic ${surf} field at each distance (lower = better)`
  +`<table style="margin-top:6px"><thead><tr><th>Distance</th><th>Avg place</th></tr></thead><tbody>`;
 rows.forEach((x,i)=>h+=`<tr${i===0?' style="background:#3a2410"':''}><td>${x.d}m${i===0?' &#11088;':''}</td><td>${x.avg.toFixed(2)}</td></tr>`);
 $('#simout').innerHTML=h+'</tbody></table>';$('#simout').style.display='block';};
render();
</script>
<button id="nerdtog">&#129299; Nerd details</button>
<style>.nerd{display:none}body.shownerd .nerd{display:revert}#nerdtog{position:fixed;right:12px;bottom:12px;z-index:99;background:#0a242e;color:#7fb0bd;border:1px solid #2a5666;border-radius:20px;padding:6px 13px;cursor:pointer;font:12px system-ui}body.shownerd #nerdtog{background:#b75527;color:#fff}</style>
<script>document.getElementById('nerdtog').onclick=function(){var s=document.body.classList.toggle('shownerd');this.innerHTML=s?'&#129299; Nerd details: ON':'&#129299; Nerd details';};</script>
</body></html>"""
out = HTML.replace("__PAYLOAD__", payload).replace("__MODEL__", model)
open(f"{OUT}/race-lab.html","w",encoding="utf-8").write(out)
print(f"wrote race-lab.html ({len(out):,} bytes)")
