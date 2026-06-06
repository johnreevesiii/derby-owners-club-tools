#!/usr/bin/env python3
"""doc-core consumer: Cross-Version Diff Suite (Tier-1 #3). Embeds the roster JSON; the HTML
diffs any two versions by horse id (stats + names), highlights changed fields, summarizes."""
import json, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:/DerbyOwnersClub/doc-core"
payload = json.dumps(json.load(open(f"{OUT}/doc_core_roster.json", encoding="utf-8")), ensure_ascii=False)

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOC Cross-Version Diff — doc-core</title>
<style>
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#0e2f3c;color:#eae8e2;font-size:13px}
 header{background:#014b50;padding:12px 18px;border-bottom:3px solid #b75527} header h1{margin:0;font-size:18px} .sub{color:#bcd;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 18px;background:#0a242e;position:sticky;top:0;z-index:5}
 select{background:#0a242e;color:#eae8e2;border:1px solid #2a5560;border-radius:5px;padding:5px 8px}
 .sum{padding:8px 18px;color:#9fe0b0;font-size:13px} .sum b{color:#ffd27a}
 .wrap{max-height:74vh;overflow:auto;margin:0 12px;border:1px solid #143;border-radius:6px}
 table{border-collapse:collapse;width:100%} th,td{padding:4px 8px;border-bottom:1px solid #143;text-align:left;vertical-align:top}
 th{position:sticky;top:0;background:#0a242e;color:#9cc;font-size:11px;text-transform:uppercase}
 td.id{color:#9ab;text-align:right} .chg{color:#ffd27a}
 .b{color:#9cc} .a{color:#9fe0b0} .romaji{color:#9cc;font-style:italic;font-size:11px}
 .pill{background:#125;border:1px solid #2a5560;border-radius:10px;padding:1px 7px;font-size:11px;margin-left:6px}
 .hint{color:#9ab;font-size:12px;padding:0 18px 6px}
 code{background:#0a242e;padding:1px 5px;border-radius:4px}
</style></head><body>
<header><h1>🔀 DOC Cross-Version Diff <span class="sub">doc-core · compare any two of the 4 versions by horse #</span></h1></header>
<div class="bar">
 Base <select id="base"></select> → Compare <select id="cmp"></select>
 <label>Show <select id="mode"><option value="all">all changes</option><option value="stats">stats only</option><option value="names">names only</option></select></label>
 <span class="pill" id="count"></span>
</div>
<div class="sum" id="sum"></div>
<div class="hint">Compares horse #N in each version (rosters are id-aligned for the 32-byte builds; '99 is a different roster, so expect many diffs vs WE). Changed fields show <span class="b">base</span> → <span class="a">compare</span>.</div>
<div class="wrap"><table id="t"></table></div>
<script>
const DATA=__PAYLOAD__, VERS=Object.keys(DATA.versions);
const $=s=>document.querySelector(s);
const STAT=['dirt','grade','style','coat','start','corner','oob','competing','tenacious','spurt','stamina','speed','sharp'];
function fields(h){return {dirt:h.dirt,grade:h.grade,style:h.style,coat:h.coat,...h.externals,...h.internals,
   name:h.name||'',nameJP:h.nameJP||'',hA:h.hidden.A,hB:h.hidden.B,hX:h.hidden.X};}
function diff(){
 const a=DATA.versions[$('#base').value].horses, b=DATA.versions[$('#cmp').value].horses, mode=$('#mode').value;
 const NAMEK=['name','nameJP'], STATK=['dirt','grade','style','coat','start','corner','oob','competing','tenacious','spurt','stamina','speed','sharp','hA','hB','hX'];
 const keys = mode==='stats'?STATK : mode==='names'?NAMEK : STATK.concat(NAMEK);
 const rows=[]; let nStat=0,nName=0;
 for(let i=0;i<Math.min(a.length,b.length);i++){
   const fa=fields(a[i]), fb=fields(b[i]), ch=[];
   for(const k of keys){ if(String(fa[k])!==String(fb[k])) ch.push({k,from:fa[k],to:fb[k]}); }
   if(ch.length){
     if(ch.some(c=>STATK.includes(c.k))) nStat++;
     if(ch.some(c=>NAMEK.includes(c.k))) nName++;
     rows.push({id:a[i].id, a:a[i], b:b[i], ch});
   }
 }
 return {rows,nStat,nName};
}
function nm(h){return h.name?h.name:`${h.nameJP||''} <span class="romaji">${h.romaji||''}</span>`;}
function render(){
 const bV=$('#base').value, cV=$('#cmp').value;
 const {rows,nStat,nName}=diff();
 $('#sum').innerHTML = `<b>${DATA.versions[bV].tag}</b> vs <b>${DATA.versions[cV].tag}</b>: `+
   `${rows.length} horses differ — ${nStat} with stat changes, ${nName} with name changes.`+
   (bV===cV?' (same version)':'');
 $('#count').textContent=`${rows.length} diffs`;
 let h='<thead><tr><th>#</th><th>'+DATA.versions[bV].tag+'</th><th>'+DATA.versions[cV].tag+'</th><th>changed fields</th></tr></thead><tbody>';
 for(const r of rows){
   const chg=r.ch.map(c=>`<span class="chg">${c.k}</span> <span class="b">${c.from}</span>→<span class="a">${c.to}</span>`).join(' &nbsp; ');
   h+=`<tr><td class="id">${r.id}</td><td>${nm(r.a)}</td><td>${nm(r.b)}</td><td>${chg}</td></tr>`;
 }
 $('#t').innerHTML=h+'</tbody>';
}
$('#base').innerHTML=$('#cmp').innerHTML=VERS.map(v=>`<option value="${v}">${DATA.versions[v].tag}</option>`).join('');
$('#base').value=VERS[0]; $('#cmp').value=VERS.find(v=>v!==VERS[0])||VERS[0];
['base','cmp','mode'].forEach(id=>$('#'+id).addEventListener('change',render));
render();
</script></body></html>"""
out = HTML.replace("__PAYLOAD__", payload)
open(f"{OUT}/version-diff.html","w",encoding="utf-8").write(out)
print(f"wrote {OUT}/version-diff.html ({len(out):,} bytes)")
