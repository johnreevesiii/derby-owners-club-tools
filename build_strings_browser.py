#!/usr/bin/env python3
"""doc-core: generate the offline string-catalog browser from doc_core_strings.json.

Mirrors build_browser.py / roster-browser.html house style: a single self-contained HTML
with the JSON embedded (runs from file://), dark theme (--teal/--orange/--sand/--blue),
sticky header, searchable + sortable table, CSV/JSON export. Search spans JP/romaji/EN/offset.
%s / %d placeholders are shown verbatim.
"""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OUT = r"C:/DerbyOwnersClub/doc-core"

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Game-Text / String Catalog — doc-core</title>
<style>
 :root{--teal:#014b50;--orange:#b75527;--sand:#eae8e2;--blue:#0e2f3c;--gold:#d8a630}
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527}
 header h1{margin:0;font-size:18px} header .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select,input{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;font-size:13px}
 input.search{width:280px}
 button{background:#b75527;color:#fff;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600}
 button.sec{background:#123;border:1px solid #2a5560;color:#eae8e2}
 .tab{padding:6px 12px;border-radius:6px 6px 0 0;background:#123;cursor:pointer;border:1px solid transparent;border-bottom:0}
 .tab.active{background:#014b50;border-color:#b75527}
 .wrap{max-height:74vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 8px;border-bottom:1px solid #143;text-align:left;vertical-align:top}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;cursor:pointer;font-size:11px;text-transform:uppercase;z-index:1;white-space:nowrap}
 td.off{font-family:Consolas,monospace;color:#9fe0b0;white-space:nowrap}
 td.blk{color:#caa6ff;white-space:nowrap}
 td.cat{white-space:nowrap}
 td.txt{white-space:pre-wrap;max-width:680px;line-height:1.45}
 .ph{background:#3a2410;color:#ffd27a;border-radius:3px;padding:0 3px;font-weight:700}
 .nl{color:#557;font-style:italic}
 .romaji{color:#9cc;font-style:italic;font-size:11px;display:block}
 tr:hover td{background:#10323e}
 .hint{color:#9ab;font-size:12px;padding:0 18px 6px}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px}
 .cat-dialogue{color:#9fe0b0}.cat-menu{color:#7ad2ff}.cat-names{color:#ffd27a}.cat-banned{color:#ff9a9a}.cat-card{color:#caa6ff}.cat-attract{color:#d8a630}.cat-branding{color:#bcd}
 .meta{color:#9ab;font-size:11px;padding:2px 18px 8px}
</style></head><body>
<header><h1>🏇 DOC Game-Text / String Catalog <span class="sub">doc-core · cross-version · byte-verified</span></h1></header>
<div class="bar">
 <span id="tabs"></span>
 <input class="search" id="q" placeholder="Search JP / romaji / EN / offset (0x…)…">
 <label>Category <select id="fc"><option value="">all</option></select></label>
 <label>Block <select id="fb"><option value="">all</option></select></label>
 <button class="sec" onclick="exp('csv')">⬇ CSV</button>
 <button class="sec" onclick="exp('json')">⬇ JSON</button>
 <span class="pill" id="count"></span>
</div>
<div class="hint">Search spans text, romaji and offset. Click a column header to sort. <span class="ph">%s</span>/<span class="ph">%d</span> placeholders are preserved; <span class="nl">\n</span> marks an embedded 0x0A newline. JP rows show カタカナ + romaji.</div>
<div class="meta" id="meta"></div>
<div class="wrap"><table id="t"></table></div>
<script>
const DATA = __DATA__;
const VERS = Object.keys(DATA.versions);
let cur = VERS[0];
let sortKey = "offset", sortDir = 1;
const $ = s => document.querySelector(s);

// flatten one version's blocks into rows
function rowsFor(v){
  const out = [];
  for(const b of DATA.versions[v].blocks){
    for(const s of b.strings){
      out.push({offset:s.offset, offNum:parseInt(s.offset,16), block:b.block, category:b.category, text:s.text, romaji:s.romaji||""});
    }
  }
  return out;
}

function rows(){
  let r = rowsFor(cur);
  const q = $("#q").value.trim().toLowerCase();
  const fc = $("#fc").value, fb = $("#fb").value;
  if(fc) r = r.filter(x=>x.category===fc);
  if(fb) r = r.filter(x=>x.block===fb);
  if(q) r = r.filter(x =>
     x.text.toLowerCase().includes(q) ||
     (x.romaji && x.romaji.toLowerCase().includes(q)) ||
     x.offset.toLowerCase().includes(q) ||
     x.block.toLowerCase().includes(q));
  r.sort((a,b)=>{
    let av,bv;
    if(sortKey==="offset"){ av=a.offNum; bv=b.offNum; }
    else { av=(a[sortKey]||"").toString().toLowerCase(); bv=(b[sortKey]||"").toString().toLowerCase(); }
    return av<bv?-sortDir:av>bv?sortDir:0;
  });
  return r;
}

function esc(s){ return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
// highlight placeholders + newline markers
function fmt(s){
  let h = esc(s);
  h = h.replace(/\n/g, '<span class="nl">\\n</span>\n');
  h = h.replace(/%[-0-9.]*[sdxcu%]/g, m=>`<span class="ph">${m}</span>`);
  return h;
}

const COLS = [["offset","Offset"],["block","Block"],["category","Cat"],["text","String"]];
function render(){
  const r = rows();
  let h = "<thead><tr>"+COLS.map(([k,l])=>`<th data-k="${k}">${l}${sortKey===k?(sortDir>0?" ▲":" ▼"):""}</th>`).join("")+"</tr></thead><tbody>";
  for(const x of r){
    const rj = x.romaji ? `<span class="romaji">${esc(x.romaji)}</span>` : "";
    h += `<tr><td class="off">${x.offset}</td><td class="blk">${esc(x.block)}</td>`
      +  `<td class="cat cat-${x.category}">${x.category}</td>`
      +  `<td class="txt">${fmt(x.text)}${rj}</td></tr>`;
  }
  $("#t").innerHTML = h + "</tbody>";
  $("#count").textContent = `${r.length} strings`;
  $("#t").querySelectorAll("th").forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; if(sortKey===k) sortDir*=-1; else{ sortKey=k; sortDir=1; } render();
  });
}

function exp(fmt){
  const r = rows(); let blob, name;
  if(fmt==="json"){
    blob = new Blob([JSON.stringify(r.map(({offNum,...o})=>o),null,1)],{type:"application/json"});
    name = `doc-strings-${cur}.json`;
  } else {
    const cols=["offset","block","category","text","romaji"];
    const q=x=>`"${String(x==null?"":x).replace(/"/g,'""')}"`;
    const lines=[cols.join(",")].concat(r.map(x=>cols.map(c=>q(x[c])).join(",")));
    blob = new Blob(["﻿"+lines.join("\n")],{type:"text/csv;charset=utf-8"});
    name = `doc-strings-${cur}.csv`;
  }
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=name; a.click();
}

// version tabs
$("#tabs").innerHTML = VERS.map(v=>`<span class="tab" data-v="${v}">${DATA.versions[v].tag}</span>`).join("");
function setMeta(){
  const V = DATA.versions[cur];
  $("#meta").textContent = `${V.label} — ${V.encoding} — ${V.blockCount} blocks, ${V.stringCount} strings (showing capped) — ROM ${V.romSize}`;
}
function rebuildBlockFilter(){
  const blks = DATA.versions[cur].blocks.map(b=>b.block);
  $("#fb").innerHTML = '<option value="">all</option>'+blks.map(b=>`<option>${b}</option>`).join("");
}
$("#tabs").querySelectorAll(".tab").forEach(t=>t.onclick=()=>{
  cur=t.dataset.v;
  $("#tabs").querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===t));
  rebuildBlockFilter(); setMeta(); render();
});
$("#tabs").firstChild.classList.add("active");

// category filter (union across versions)
const cats=[...new Set(VERS.flatMap(v=>DATA.versions[v].blocks.map(b=>b.category)))];
$("#fc").innerHTML='<option value="">all</option>'+cats.map(c=>`<option>${c}</option>`).join("");
["q","fc","fb"].forEach(id=>$("#"+id).addEventListener("input",render));

rebuildBlockFilter(); setMeta(); render();
</script></body></html>"""

def main():
    src = f"{OUT}/doc_core_strings.json"
    data = json.load(open(src, encoding="utf-8"))
    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    path = f"{OUT}/strings-browser.html"
    open(path, "w", encoding="utf-8").write(html)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes) from {os.path.getsize(src):,}-byte JSON")

if __name__ == "__main__":
    main()
