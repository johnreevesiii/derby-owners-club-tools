#!/usr/bin/env python3
"""doc-core: generator for food-tool.html (the offline Food/Feed editor + Enable-Beer patcher).

Embeds doc_core_food.json (the canonical food table, all 4 versions) into a single offline HTML.
The tool itself reads a USER-supplied .ic22 live via FileReader (ROM-Studio pattern), decodes the
food table from that ROM using the embedded per-version geometry, lets the user edit effect bytes,
applies the documented one-click "Enable Beer" patch (+2 DRAFT / +4 BLACK to effect cols 0-5),
and exports the patched ROM byte-exact (4,194,304 bytes) via a Blob. The 4MB ROM is never embedded.

Regenerate: python3 build_food.py && python3 build_food_tool.py
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OUT = r"C:/DerbyOwnersClub/doc-core"
DATA = json.load(open(f"{OUT}/doc_core_food.json", encoding="utf-8"))
DATA_JSON = json.dumps(DATA, ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Food / Feed Editor + Enable Beer &middot; doc-core</title>
<style>
 :root{--teal:#014b50;--orange:#b75527;--sand:#eae8e2;--blue:#0e2f3c;--gold:#d8a630}
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--blue);color:var(--sand);font-size:13px}
 header{background:var(--teal);padding:12px 18px;border-bottom:3px solid var(--orange)}
 header h1{margin:0;font-size:18px} header .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:var(--sand);border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 input.search{width:200px}
 button{background:var(--orange);color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600}
 button:disabled{opacity:.4;cursor:not-allowed}
 button.sec{background:#125;border:1px solid #2a5560}
 button.beer{background:var(--gold);color:#2a1c00}
 #drop{margin:14px 18px;padding:22px;border:2px dashed #2a5560;border-radius:10px;text-align:center;color:#9ab;cursor:pointer;background:#0a242e}
 #drop.hot{border-color:var(--gold);color:var(--gold)}
 .wrap{max-height:70vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 7px;border-bottom:1px solid #143;white-space:nowrap;text-align:right}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase;z-index:1}
 th.l,td.l{text-align:left} td.name{text-align:left;font-weight:600}
 tr:hover td{background:#10323e}
 tr.beer td{background:#2a2200} tr.beer:hover td{background:#3a2f00}
 tr.dirty td{background:#1a3320} tr.dirty:hover td{background:#224028}
 td input.eff{width:38px;text-align:center;padding:2px} td input.idx{width:46px;text-align:center;padding:2px}
 .romaji{color:#9cc;font-style:italic;font-size:11px}
 .hint{color:#9ab;font-size:12px;padding:0 18px 6px} .hint code{color:var(--gold)}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
 .ok{color:#9fe0b0} .warn{color:var(--gold)} .err{color:#ff9a9a}
 .flag0{color:#caa6ff} .flag1{color:#7ad2ff}
 #status{padding:6px 18px;color:#9ab;font-size:12px}
</style></head><body>
<header><h1>&#127866; DOC Food / Feed Editor <span class="sub">doc-core &middot; load a .ic22 &middot; edit effects &middot; one-click Enable Beer &middot; byte-exact export</span></h1></header>

<div id="drop">Drop a DOC program ROM here (<b>epr-*.ic22</b>, 4,194,304 bytes) &mdash; or click to choose. The 4MB ROM stays on your machine; nothing is uploaded.</div>

<div class="bar" id="bar" style="display:none">
 <span class="pill" id="verPill"></span>
 <input class="search" id="q" placeholder="Search food name / #&hellip;">
 <button class="beer" id="beerBtn" title="Apply the documented Enable-Beer effect patch">&#127866; Enable Beer</button>
 <button class="sec" id="resetBtn" title="Discard edits, reload from the loaded ROM">&#8634; Revert edits</button>
 <button id="saveBtn" title="Export the patched ROM, byte-exact">&#11015; Export patched .ic22</button>
 <button class="sec" onclick="exp('csv')">&#11015; CSV</button>
 <button class="sec" onclick="exp('json')">&#11015; JSON</button>
 <span class="pill" id="count"></span>
</div>
<div class="hint" id="hint" style="display:none">
 Effect cols: <code>Speed Stamina Sharp</code> verified; <code>col3-col6</code> secondary growth (tentative). Edit any cell (0&ndash;255). <b>Enable Beer</b> = +2 to DRAFT &amp; +4 to BLACK across cols 0&ndash;5 (the verified KOREAN-GINSENG template; the same 12-byte change as the original beer experiment). <code>Index</code> stays in the 1&ndash;39 range (out-of-range crashes the cabinet). Edited rows turn green; beer rows are amber.
</div>
<div class="wrap" id="wrap" style="display:none"><table id="t"></table></div>
<div id="status"></div>

<script>
const DATA = __DATA__;
const ROM_SIZE = DATA.romSize;
const REC = DATA.recordSize;          // 44
const EFF_OFF = 28, CLASS_OFF = 35, RARITY_OFF = 36, INDEX_OFF = 40, NAME_W = 24;
const COLS = DATA.effectColumns;      // 7 labels
const $ = s => document.querySelector(s);

let rom = null;          // Uint8Array of the loaded ROM (live, edits applied in place)
let pristine = null;     // pristine copy of the loaded ROM (for Revert)
let verKey = null;       // detected version key
let fileName = "";
let foods = [];          // decoded rows {slot, recOffset, name, isBeer, ...}

// ---- name decode (ascii low7 / euc-jp) ----
const eucDec = (typeof TextDecoder !== "undefined") ? new TextDecoder("euc-jp") : null;
function decodeName(bytes, enc){
  let end = bytes.indexOf(0); if(end < 0) end = bytes.length;
  const raw = bytes.subarray(0, end);
  if(enc === "ascii"){
    let s=""; for(const b of raw) s += String.fromCharCode(b & 0x7f);
    return s.trim();
  }
  if(eucDec){ try{ return eucDec.decode(raw); }catch(e){} }
  let s=""; for(const b of raw) s += String.fromCharCode(b); return s;
}

// ---- version detection: try every known version, match the embedded name list at its table offset ----
function detectVersion(buf){
  let best=null, bestScore=-1;
  for(const key of Object.keys(DATA.versions)){
    const v = DATA.versions[key];
    const base = parseInt(v.table,16), enc = v.nameEnc;
    let score=0, checked=0;
    for(const f of v.foods){
      const off = base + REC*f.slot;
      if(off+NAME_W > buf.length) break;
      const nm = decodeName(buf.subarray(off, off+NAME_W), enc);
      checked++;
      if(nm === f.name) score++;
    }
    const frac = checked ? score/checked : 0;
    if(frac > bestScore){ bestScore=frac; best=key; }
  }
  return {key: best, frac: bestScore};
}

// ---- decode the live ROM's food table into editable rows ----
function decodeFoods(){
  const v = DATA.versions[verKey];
  const base = parseInt(v.table,16), enc = v.nameEnc;
  foods = [];
  for(let n=0; n<64; n++){
    const r = base + REC*n;
    if(r+REC > rom.length) break;
    const idx = rom[r+INDEX_OFF] | (rom[r+INDEX_OFF+1]<<8) | (rom[r+INDEX_OFF+2]<<16) | (rom[r+INDEX_OFF+3]<<24);
    const name = decodeName(rom.subarray(r, r+NAME_W), enc);
    if(idx === 0 && name === "") break;          // terminator
    const eff = []; for(let i=0;i<7;i++) eff.push(rom[r+EFF_OFF+i]);
    foods.push({
      slot:n, recOffset:r, name, index:idx>>>0, eff,
      classFlag: rom[r+CLASS_OFF], rarityFlag: rom[r+RARITY_OFF],
      isBeer: /^(DRAFT BEER|BLACK DRAFT BEER)$/.test(name) || name==="生中" || name==="黒生中",
      orig: { eff: [], index: idx>>>0 }
    });
    foods[foods.length-1].orig.eff = eff.slice();
  }
}

function dirty(f){ return f.index!==f.orig.index || f.eff.some((x,i)=>x!==f.orig.eff[i]); }

// ---- write current row state back into the live ROM bytes ----
function commit(f){
  for(let i=0;i<7;i++) rom[f.recOffset+EFF_OFF+i] = f.eff[i] & 0xff;
  rom[f.recOffset+INDEX_OFF]   =  f.index        & 0xff;
  rom[f.recOffset+INDEX_OFF+1] = (f.index>>>8)   & 0xff;
  rom[f.recOffset+INDEX_OFF+2] = (f.index>>>16)  & 0xff;
  rom[f.recOffset+INDEX_OFF+3] = (f.index>>>24)  & 0xff;
}

// ---- render ----
function rows(){
  const q = $("#q").value.toLowerCase().trim();
  return foods.filter(f => !q || (f.name+" "+f.index+" "+f.slot).toLowerCase().includes(q));
}
function render(){
  const head = `<thead><tr><th>#</th><th class="l">Food</th><th>Idx</th>`
    + COLS.map((c,i)=>`<th title="effect col ${i} (+${EFF_OFF+i})">${c}</th>`).join("")
    + `<th title="+35 class flag">Cls</th><th title="+36 rarity">Rar</th><th title="record offset">Offset</th></tr></thead><tbody>`;
  let h = head;
  for(const f of rows()){
    const cls = (f.isBeer?"beer ":"") + (dirty(f)?"dirty":"");
    let cells = `<td>${f.slot}</td><td class="name">${escapeHtml(f.name)||"<i>(blank)</i>"}</td>`
      + `<td><input class="idx" data-slot="${f.slot}" data-k="index" value="${f.index}"></td>`;
    for(let i=0;i<7;i++) cells += `<td><input class="eff" data-slot="${f.slot}" data-k="${i}" value="${f.eff[i]}"></td>`;
    const cf = f.classFlag===1?'flag1':'flag0';
    cells += `<td class="${cf}">${f.classFlag}</td><td>${f.rarityFlag}</td><td class="l">0x${f.recOffset.toString(16).toUpperCase()}</td>`;
    h += `<tr class="${cls}">${cells}</tr>`;
  }
  $("#t").innerHTML = h + "</tbody>";
  $("#count").textContent = `${rows().length} foods${foods.some(dirty)?" · unsaved edits":""}`;
  $("#t").querySelectorAll("input").forEach(inp=>{
    inp.addEventListener("change", onEdit);
    inp.addEventListener("input", onEdit);
  });
}
function escapeHtml(s){ return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

function onEdit(e){
  const inp=e.target, slot=+inp.dataset.slot, k=inp.dataset.k;
  const f=foods.find(x=>x.slot===slot); if(!f) return;
  let val=parseInt(inp.value,10); if(isNaN(val)) return;
  if(k==="index"){
    val = Math.max(0, Math.min(255, val));
    if(val>39){ status(`Index ${val} is out of the safe 1–39 range — the cabinet builds a ~39-entry lookup and crashes on higher ids. Clamped to 39.`,"warn"); val=39; inp.value=39; }
    f.index=val;
  } else {
    val = Math.max(0, Math.min(255, val)); inp.value=val; f.eff[+k]=val;
  }
  commit(f);
  // toggle dirty class on the row without full re-render
  const tr=inp.closest("tr"); tr.classList.toggle("dirty", dirty(f));
  $("#count").textContent = `${rows().length} foods${foods.some(dirty)?" · unsaved edits":""}`;
}

// ---- one-click Enable Beer (documented patch: +2 DRAFT, +4 BLACK across cols 0-5) ----
function enableBeer(){
  const beers = foods.filter(f=>f.isBeer);
  if(!beers.length){ status("This ROM has no beer records (DOC '99 never shipped beer). Nothing to enable.","warn"); return; }
  for(const f of beers){
    const isBlack = /BLACK/.test(f.name) || f.name==="黒生中";
    const delta = isBlack?4:2;
    for(let i=0;i<6;i++) f.eff[i]=delta;     // cols 0-5; col6 + class flag untouched (matches the experiment)
    commit(f);
  }
  render();
  status(`Enable Beer applied: DRAFT +2 / BLACK +4 to effect cols 0–5 (the verified KOREAN-GINSENG template). Note: beer index stays at 1 (shares CARROT's slot) — boots, but the menu-builder gate (open Q3) means visibility in the feed menu is unconfirmed. Export and test in Flycast/DEMUL.`,"warn");
}

// ---- export byte-exact ----
function save(){
  if(!rom){ return; }
  if(rom.length!==ROM_SIZE){ status(`Refusing to export: ROM is ${rom.length} bytes, expected ${ROM_SIZE}.`,"err"); return; }
  const blob=new Blob([rom],{type:"application/octet-stream"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob);
  a.download=(fileName.replace(/\.ic22$/i,"")||"epr")+"-foodedit.ic22";
  a.click();
  status(`Exported ${a.download} (${rom.length.toLocaleString()} bytes, byte-exact).`,"ok");
}

function exp(fmt){
  if(!foods.length) return;
  const cols=["slot","name","index","classFlag","rarityFlag"].concat(COLS.map((c,i)=>"eff"+i));
  let blob,name;
  if(fmt==="json"){
    const out=foods.map(f=>({slot:f.slot,name:f.name,index:f.index,classFlag:f.classFlag,rarityFlag:f.rarityFlag,
      effect:f.eff,recOffset:"0x"+f.recOffset.toString(16).toUpperCase()}));
    blob=new Blob([JSON.stringify(out,null,1)],{type:"application/json"}); name=`doc-food-${verKey}.json`;
  } else {
    const esc=x=>`"${String(x==null?"":x).replace(/"/g,'""')}"`;
    const lines=[cols.join(",")];
    for(const f of foods) lines.push([f.slot,f.name,f.index,f.classFlag,f.rarityFlag].concat(f.eff).map(esc).join(","));
    blob=new Blob(["﻿"+lines.join("\n")],{type:"text/csv;charset=utf-8"}); name=`doc-food-${verKey}.csv`;
  }
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=name; a.click();
}

function status(msg,cls){ const s=$("#status"); s.className=cls||""; s.textContent=msg; }

// ---- load ----
function loadFile(file){
  fileName=file.name;
  const fr=new FileReader();
  fr.onload=()=>{
    const buf=new Uint8Array(fr.result);
    if(buf.length!==ROM_SIZE){
      status(`That file is ${buf.length.toLocaleString()} bytes; a NAOMI program ROM is ${ROM_SIZE.toLocaleString()}. Load the raw epr-*.ic22 (not a .zip).`,"err");
      return;
    }
    const det=detectVersion(buf);
    if(det.frac < 0.5){
      status(`Couldn't recognize this as a DOC food ROM (best match ${det.key} only ${(det.frac*100).toFixed(0)}% of names). Loaded anyway as ${det.key}; verify the table.`,"warn");
    }
    rom=buf; pristine=buf.slice(); verKey=det.key;
    const v=DATA.versions[verKey];
    decodeFoods();
    $("#bar").style.display="flex"; $("#hint").style.display="block"; $("#wrap").style.display="block";
    $("#verPill").textContent=`${v.tag} · ${v.label} · table ${v.table} · ${foods.length} foods`;
    $("#beerBtn").disabled = !foods.some(f=>f.isBeer);
    render();
    status(`Loaded ${fileName} — detected ${v.tag} (${(det.frac*100).toFixed(0)}% name match). Edits apply live; export when ready.`,"ok");
  };
  fr.readAsArrayBuffer(file);
}

// ---- wiring ----
const drop=$("#drop");
const picker=document.createElement("input"); picker.type="file"; picker.accept=".ic22,.bin"; picker.style.display="none"; document.body.appendChild(picker);
drop.onclick=()=>picker.click();
picker.onchange=e=>{ if(e.target.files[0]) loadFile(e.target.files[0]); };
drop.addEventListener("dragover",e=>{e.preventDefault(); drop.classList.add("hot");});
drop.addEventListener("dragleave",()=>drop.classList.remove("hot"));
drop.addEventListener("drop",e=>{e.preventDefault(); drop.classList.remove("hot"); if(e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);});
$("#q").addEventListener("input",render);
$("#beerBtn").onclick=enableBeer;
$("#saveBtn").onclick=save;
$("#resetBtn").onclick=()=>{ if(rom&&pristine){ rom=pristine.slice(); decodeFoods(); render(); status("Reverted all edits to the originally-loaded ROM bytes.","ok"); } };
</script></body></html>"""

def main():
    html = HTML.replace("__DATA__", DATA_JSON)
    path = f"{OUT}/food-tool.html"
    open(path, "w", encoding="utf-8").write(html)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")

if __name__ == "__main__":
    main()
