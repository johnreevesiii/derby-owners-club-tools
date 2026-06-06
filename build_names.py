#!/usr/bin/env python3
"""doc-core: EN<->JP name cross-reference by horse id. Joins the 4 versions' roster names
(name[n] aligns with stat[n] within each version) -> doc_core_names.json + names-xref.html.
Note: RevC/RevD/DOC2000 share the roster (id N = same horse, 4 names); '99 is a genuinely
different roster, so its id N is whatever '99's horse #N is (still id-indexed)."""
import json, os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
R = json.load(open(f"{OUT}/doc_core_roster.json", encoding="utf-8"))["versions"]
n = R["drbyocwc"]["count"]
rows = []
for i in range(n):
    rows.append({
        "id": R["drbyocwc"]["horses"][i]["id"],
        "revC": R["drbyocwc"]["horses"][i]["name"],
        "revD": R["derbyocw"]["horses"][i]["name"],
        "doc2000": {"kana": R["derbyo2k"]["horses"][i]["nameJP"], "romaji": R["derbyo2k"]["horses"][i]["romaji"]},
        "doc99":   {"kana": R["derbyoc"]["horses"][i]["nameJP"],  "romaji": R["derbyoc"]["horses"][i]["romaji"]},
        "renamedRevD": R["drbyocwc"]["horses"][i]["name"] != R["derbyocw"]["horses"][i]["name"],
    })
data = {"_about": "EN<->JP horse name cross-reference by id. RevC/RevD/DOC2000 = same roster (4 names for one horse); DOC'99 is a different roster indexed by id.", "count": n, "names": rows}
json.dump(data, open(f"{OUT}/doc_core_names.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
renamed = sum(1 for r in rows if r["renamedRevD"])
print(f"wrote doc_core_names.json ({n} ids; {renamed} renamed Rev C->Rev D)")

payload = json.dumps(data, ensure_ascii=False)
HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Name Cross-Reference — doc-core</title>
<style>
 *{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527}header h1{margin:0;font-size:18px}.sub{color:#bcd;font-size:12px}
 .bar{padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 input{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px;width:260px}
 .wrap{max-height:80vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%}th,td{padding:4px 9px;border-bottom:1px solid #143;text-align:left}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;font-size:11px;text-transform:uppercase}
 td.id{color:#9ab;text-align:right}.jp{font-size:15px}.romaji{color:#9cc;font-style:italic;font-size:11px}.rn{color:#ffd27a}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px;margin-left:8px}
</style></head><body>
<header><h1>🪪 DOC Name Cross-Reference <span class="sub">one horse, four versions · EN ↔ カタカナ by id</span></h1></header>
<div class="bar"><input id="q" placeholder="Search any name / romaji / #…"><span class="pill" id="c"></span>
 <span class="sub" style="margin-left:10px">Rev D rename = <span class="rn">orange</span>. '99 is a different roster (id-indexed).</span></div>
<div class="wrap"><table id="t"></table></div>
<script>
const D=__PAYLOAD__,$=s=>document.querySelector(s);
function render(){const q=$('#q').value.toLowerCase().trim();
 const rows=D.names.filter(r=>!q||[r.revC,r.revD,r.doc2000.kana,r.doc2000.romaji,r.doc99.kana,r.doc99.romaji,String(r.id)].join(' ').toLowerCase().includes(q));
 let h='<thead><tr><th>#</th><th>World (Rev C)</th><th>Export (Rev D)</th><th>DOC 2000</th><th>DOC \'99</th></tr></thead><tbody>';
 for(const r of rows){
   h+=`<tr><td class="id">${r.id}</td><td${r.renamedRevD?'':''}>${r.revC||''}</td>`
    +`<td class="${r.renamedRevD?'rn':''}">${r.revD||''}</td>`
    +`<td><span class="jp">${r.doc2000.kana||''}</span> <span class="romaji">${r.doc2000.romaji||''}</span></td>`
    +`<td><span class="jp">${r.doc99.kana||''}</span> <span class="romaji">${r.doc99.romaji||''}</span></td></tr>`;
 }
 $('#t').innerHTML=h+'</tbody>';$('#c').textContent=`${rows.length}/${D.count}`;
}
$('#q').addEventListener('input',render);render();
</script></body></html>"""
open(f"{OUT}/names-xref.html", "w", encoding="utf-8").write(HTML.replace("__PAYLOAD__", payload))
print(f"wrote names-xref.html")
