#!/usr/bin/env python3
"""doc-core tool #13: DOC-ROM-Studio — unified field-map ROM editor + patch library.

Builds rom-studio.html: drop a .ic22 -> fingerprint -> a byte-labeled editor for the 244-record
CPU racing table (all 4 versions; 32-byte WE/2000, 28-byte '99 field maps), with name editing
(ASCII), enum dropdowns (grade/style), and per-field 0-255 inputs. Plus a Patches tab (one-click
Enable Beer, byte-exact). Exports a patched .ic22.

SAFETY: edits the ONE loaded ROM in place (always safe). Cross-version transpose is intentionally
NOT offered (the 22 RevC<->DOC2000 divergent records make blind transpose unsafe); instead the
editor flags each record's divergence-vs-DOC2000 for awareness. JP name edit is read-only
(EUC-JP encode-back not included); stat-byte editing works for all versions.

Provenance: horse-stats.md field map (build_roster.py FIELDS 32/28, SOLID 244/244), version sigs
(doc_core_versions.json), beer patch (doc_core_food.json, beerPatchReproducesTestROM=true).
"""
import json, io
OUT = r"C:/DerbyOwnersClub/doc-core"
V = json.load(io.open(f"{OUT}/doc_core_versions.json", encoding="utf-8"))
R = json.load(io.open(f"{OUT}/doc_core_roster.json", encoding="utf-8"))
F = json.load(io.open(f"{OUT}/doc_core_food.json", encoding="utf-8"))

FIELDS = {
 32: dict(hiddenA=1, id=2, dirt=5, grade=8, start=9, corner=10, oob=11, comp=12, tenac=13, spurt=14, hiddenB=16, style=21, coat=22, hxLo=23, hxHi=24, stam=29, speed=30, sharp=31),
 28: dict(hiddenA=0, id=1, dirt=4, grade=7, start=9, corner=10, oob=11, comp=12, tenac=13, spurt=14, hiddenB=17, style=18, coat=19, hxLo=20, hxHi=21, stam=24, speed=25, sharp=26),
}
STYLE = {0:"Front-runner",1:"Start dash",2:"Last spurt",3:"Stretch-runner",7:"Almighty"}
COAT  = {0:"Default",192:"Chestnut",193:"Black",199:"Brown",202:"Bay",204:"Dark Gray",207:"Light Gray",222:"Special"}
GRADE = {0:"Ungraded",1:"G3",2:"G2",3:"G1"}

# divergence: ids where RevC vs DOC2000 decoded fields differ
def sig_of(h):
    e=h["externals"]; i=h["internals"]
    return (h["grade"],h["dirt"],e["start"],e["corner"],e["oob"],e["competing"],e["tenacious"],e["spurt"],i["stamina"],i["speed"],i["sharp"],h["style"])
rc={h["id"]:sig_of(h) for h in R["versions"]["drbyocwc"]["horses"]}
o2={h["id"]:sig_of(h) for h in R["versions"]["derbyo2k"]["horses"]}
divergent=sorted([i for i in rc if i in o2 and rc[i]!=o2[i]])

versions={}
for vk,vv in V["versions"].items():
    off=vv["offsets"]
    versions[vk]={
        "tag":vv["tag"],"label":vv["label"],"fmt":vv["recordFmt"],
        "rec":int(off["stat"],16),"names":int(off["names"],16),"nameStride":18,
        "enc":"euc-jp" if vv["nameEnc"]!="ascii" else "ascii",
        "count":R["versions"][vk]["count"],
        "sig":vv["sig8000"],
        "beer":[{"off":int(b["effectFieldOffsetHex"],16),"name":b["name"],"idx":b["index"]}
                for b in F["versions"][vk].get("beerRecords",[])],
    }
DATA=json.dumps({"versions":versions,"fields":FIELDS,"style":STYLE,"coat":COAT,"grade":GRADE,
                 "divergent":divergent}, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC-ROM-Studio</title>
<style>
 body{margin:0;font:13px/1.4 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:10px 18px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:18px;color:#eae8e2}.sub{color:#7fb0bd;font-size:12px;font-weight:400}
 .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 18px;background:#0a242e;position:sticky;top:0;z-index:6;border-bottom:1px solid #143b48}
 .bar input[type=text],.bar select{background:#06303a;color:#e8eef0;border:1px solid #2a5666;border-radius:5px;padding:4px 8px}
 button{background:#014b50;color:#cfe;border:0;border-radius:5px;padding:5px 11px;cursor:pointer;font-size:12px}
 button.act{background:#b75527;color:#fff}button:disabled{opacity:.4;cursor:not-allowed}
 .pill{display:inline-block;background:#014b50;color:#cfe;border-radius:9px;padding:1px 8px;cursor:pointer}
 .wrap{padding:6px 12px 50px}
 .tabs{display:flex;gap:6px;margin:8px 6px}
 .tabs button{background:#0a242e;color:#9cc;border:1px solid #143b48}.tabs button.on{background:#014b50;color:#fff}
 table{border-collapse:collapse;background:#08202a;font-variant-numeric:tabular-nums}
 th,td{border:1px solid #143b48;padding:2px 5px;text-align:center;font-size:12px;white-space:nowrap}
 th{background:#0a242e;color:#9cc;position:sticky;top:46px;z-index:2}
 td.l{text-align:left}
 input.f{width:42px;background:#06303a;color:#fff;border:1px solid #2a5666;border-radius:3px;padding:1px 3px;text-align:center;font-size:12px}
 input.f.changed{border-color:#d8a630;background:#2a2410}
 input.nm{width:120px;background:#06303a;color:#fff;border:1px solid #2a5666;border-radius:3px;padding:1px 4px;font-size:12px}
 select.f{background:#06303a;color:#fff;border:1px solid #2a5666;border-radius:3px;font-size:12px}
 select.f.changed{border-color:#d8a630}
 .div{color:#ffb27f}.muted{color:#6f9aa6}.ok{color:#7fdca0}.warn{color:#ffb27f}
 .note{color:#7fb0bd;font-size:12px;margin:6px}
 #status{margin-left:auto;font-size:12px}
 .scroll{overflow:auto;max-height:78vh;margin:0 6px}
 .patch{background:#08202a;border:1px solid #143b48;border-radius:8px;padding:12px;margin:8px 6px;max-width:680px}
 .patch h3{margin:.2em 0;color:#eae8e2}
</style></head><body>
<header><h1>&#128295; DOC-ROM-Studio <span class="sub">tool #13 &middot; unified field-map roster editor + patch library</span></h1></header>
<div class="bar">
 <label class="pill">Drop / pick ROM (.ic22)<input id="rom" type="file" accept=".ic22,.bin" style="display:none"></label>
 <select id="ver"></select>
 <input id="q" type="text" placeholder="filter by name/id..." size="18">
 <button id="exp" class="act" disabled>&#128190; Export patched .ic22</button>
 <span id="status" class="muted">no ROM loaded</span>
</div>
<div class="wrap">
 <div class="tabs"><button id="tRoster" class="on">Roster Editor</button><button id="tPatch">Patches</button></div>
 <div id="rosterPane">
  <div class="note">Edit any field of the 244 CPU racing records. Grade/Style are dropdowns; other fields are raw 0&ndash;255 bytes (hidden A/B/X exposed raw &mdash; meaning inferred). Name edit is ASCII only (JP names read-only). <span class="div">&#9650;</span> = record differs from DOC 2000 (one of the 22 rebalanced; edit freely &mdash; this only matters for cross-version transpose, which this tool intentionally doesn't do).</div>
  <div class="scroll"><div id="tbl"></div></div>
 </div>
 <div id="patchPane" style="display:none">
  <div class="patch"><h3>&#127866; Enable Beer</h3>
   <p class="muted">The two beer foods ship with all-zero effect fields (disabled). This writes the proven +2 (Draft) / +4 (Black Draft) to their six stat columns &mdash; byte-exact, reproduces the validated test-ROM diff.</p>
   <div id="beerInfo" class="muted">load a ROM first</div>
   <button id="beerBtn" disabled>Apply Enable-Beer patch</button> <span id="beerStat"></span>
  </div>
  <div class="note">More table editors (food feed values, NVRAM, strings) live as focused tools in the launcher: food-tool, nvram-dashboard, string-tool. ROM-Studio is the roster + patch shell.</div>
 </div>
</div>
<script>
const D=__DATA__;
let rom=null,curVer='drbyocwc',recs=[],edits={},nameEdits={},patches={beer:false};
const $=s=>document.querySelector(s);
const hx=n=>'0x'+n.toString(16).toUpperCase();
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));}
{const vs=$('#ver');for(const k in D.versions){const o=document.createElement('option');o.value=k;o.textContent=D.versions[k].tag;vs.appendChild(o);}vs.value=curVer;}
const DIV=new Set(D.divergent);

function readName(bytes,base,enc){let end=base;const lim=base+18;while(end<lim&&bytes[end]!==0)end++;try{return new TextDecoder(enc).decode(bytes.slice(base,end));}catch(e){return new TextDecoder('ascii').decode(bytes.slice(base,end));}}
function build(){
 const v=D.versions[curVer],F=D.fields[v.fmt];recs=[];
 if(!rom){$('#tbl').innerHTML='<div class="note">Drop a ROM to load its 244 records.</div>';return;}
 for(let n=0;n<v.count;n++){
  const r=v.rec+v.fmt*n, g=k=>rom[r+F[k]];
  recs.push({n,id:g('id')|(rom[r+F.id+1]<<8),name:readName(rom,v.names+v.nameStride*n,v.enc),
   dirt:g('dirt'),grade:g('grade'),start:g('start'),corner:g('corner'),oob:g('oob'),comp:g('comp'),tenac:g('tenac'),spurt:g('spurt'),
   stam:g('stam'),speed:g('speed'),sharp:g('sharp'),style:g('style'),coat:g('coat'),hA:g('hiddenA'),hB:g('hiddenB'),hxLo:g('hxLo'),hxHi:g('hxHi')});
 }
 render();
}
const COLS=[['dirt','dirt'],['start','st'],['corner','co'],['oob','ob'],['comp','cp'],['tenac','tn'],['spurt','sp'],['stam','STA'],['speed','SPD'],['sharp','SHP'],['hA','hA'],['hB','hB'],['hxLo','hXlo'],['hxHi','hXhi']];
function ek(n,f){return n+':'+f;}
function render(){
 if(!rom)return;
 const q=$('#q').value.toLowerCase();const v=D.versions[curVer];
 const rows=recs.filter(r=>!q||r.name.toLowerCase().includes(q)||String(r.id).includes(q)||String(r.n+1).includes(q));
 let h='<table><thead><tr><th>#</th><th>id</th><th class=l>name</th><th>grade</th><th>style</th><th>coat</th>'
   +COLS.map(c=>'<th>'+c[1]+'</th>').join('')+'<th>&#916;</th></tr></thead><tbody>';
 rows.forEach(r=>{
  const nmEd=nameEdits[r.n], nm=nmEd!=null?nmEd:r.name;
  const nmDis = v.enc!=='ascii'?'disabled title="JP name read-only"':'';
  h+='<tr><td>'+(r.n+1)+'</td><td>'+r.id+'</td>'
   +'<td class=l><input class="nm'+(nmEd!=null&&nmEd!==r.name?' changed':'')+'" data-n="'+r.n+'" value="'+esc(nm)+'" '+nmDis+'></td>'
   +'<td>'+sel(r.n,'grade',r.grade,D.grade)+'</td>'
   +'<td>'+sel(r.n,'style',r.style,D.style)+'</td>'
   +'<td>'+num(r.n,'coat',r.coat)+'<div class="muted" style="font-size:10px">'+(D.coat[curVal(r.n,'coat',r.coat)]||'')+'</div></td>'
   +COLS.map(c=>'<td>'+num(r.n,c[0],r[c[0]])+'</td>').join('')
   +'<td>'+(DIV.has(r.id)?'<span class="div" title="differs from DOC 2000">&#9650;</span>':'')+'</td></tr>';
 });
 $('#tbl').innerHTML=h+'</tbody></table>';
 $('#tbl').querySelectorAll('input.nm').forEach(inp=>inp.addEventListener('input',e=>{const n=+e.target.dataset.n;nameEdits[n]=e.target.value.slice(0,18);e.target.classList.toggle('changed',nameEdits[n]!==recs[n].name);flag();}));
 $('#tbl').querySelectorAll('input.f,select.f').forEach(el=>el.addEventListener('input',e=>{const n=+e.target.dataset.n,f=e.target.dataset.f;let val=Math.max(0,Math.min(255,parseInt(e.target.value)||0));edits[ek(n,f)]=val;e.target.classList.toggle('changed',val!==recs[n][f]);flag();}));
}
function curVal(n,f,orig){const e=edits[ek(n,f)];return e!=null?e:orig;}
function num(n,f,orig){const v=curVal(n,f,orig);return '<input class="f'+(edits[ek(n,f)]!=null&&edits[ek(n,f)]!==orig?' changed':'')+'" data-n="'+n+'" data-f="'+f+'" value="'+v+'">';}
function sel(n,f,orig,enm){const v=curVal(n,f,orig);let o='';const keys=new Set(Object.keys(enm).map(Number));keys.add(v);[...keys].sort((a,b)=>a-b).forEach(k=>{o+='<option value="'+k+'"'+(k===v?' selected':'')+'>'+(enm[k]||k)+'</option>';});return '<select class="f'+(edits[ek(n,f)]!=null&&edits[ek(n,f)]!==orig?' changed':'')+'" data-n="'+n+'" data-f="'+f+'">'+o+'</select>';}
function flag(){
 const nf=Object.keys(edits).filter(k=>{const[n,f]=k.split(':');return edits[k]!==recs[+n][f];}).length;
 const nn=Object.keys(nameEdits).filter(n=>nameEdits[n]!==recs[+n].name).length;
 const tot=nf+nn+(patches.beer?1:0);
 $('#status').innerHTML=rom?('<span class="ok">&#9679; '+D.versions[curVer].tag+'</span>'+(tot?' &middot; <span class="warn">'+nf+' fields, '+nn+' names'+(patches.beer?', +beer':'')+'</span>':'')):'no ROM loaded';
 $('#exp').disabled=!(rom&&tot);
}
// ROM load
$('#rom').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{rom=new Uint8Array(r.result);const sig=[...rom.slice(0x8000,0x8010)].map(b=>b.toString(16).padStart(2,'0')).join('');
  let m=null;for(const k in D.versions)if(D.versions[k].sig===sig)m=k;
  if(m){curVer=m;$('#ver').value=m;}
  edits={};nameEdits={};patches.beer=false;build();updBeer();
  $('#status').innerHTML=m?('<span class="ok">&#9679; '+f.name+' &mdash; '+D.versions[m].tag+'</span>'):('<span class="warn">&#9679; '+f.name+' &mdash; unknown sig; using '+D.versions[curVer].tag+'</span>');
 };r.readAsArrayBuffer(f);});
$('#ver').addEventListener('change',e=>{curVer=e.target.value;edits={};nameEdits={};build();updBeer();flag();});
$('#q').addEventListener('input',render);
// export
$('#exp').addEventListener('click',()=>{const out=rom.slice();const v=D.versions[curVer],F=D.fields[v.fmt];
 let nf=0,nn=0;
 for(const k in edits){const[n,f]=k.split(':');const val=edits[k];if(val===recs[+n][f])continue;out[v.rec+v.fmt*(+n)+F[f]]=val&0xFF;nf++;}
 for(const n in nameEdits){const nm=nameEdits[n];if(nm===recs[+n].name)continue;const base=v.names+v.nameStride*(+n);for(let i=0;i<v.nameStride;i++)out[base+i]=(i<nm.length)?(nm.charCodeAt(i)&0x7f):0;nn++;}
 if(patches.beer)applyBeer(out,v);
 const b=new Blob([out],{type:'application/octet-stream'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=v.tag.replace(/[^A-Za-z0-9]/g,'')+'_studio.ic22';a.click();
 $('#status').innerHTML='<span class="ok">exported '+nf+' fields, '+nn+' names'+(patches.beer?', beer patch':'')+'</span>';
});
// beer patch
function updBeer(){const v=D.versions[curVer];const has=v.beer&&v.beer.length;
 $('#beerInfo').innerHTML=rom?(has?('Beer foods: '+v.beer.map(b=>esc(b.name)+' @'+hx(b.off)).join(', ')):'<span class="warn">this version has no beer foods</span>'):'load a ROM first';
 $('#beerBtn').disabled=!(rom&&has);}
function applyBeer(out,v){v.beer.forEach(b=>{const val=b.idx===1?2:4;for(let i=0;i<6;i++)out[b.off+i]=val;});}
$('#beerBtn').addEventListener('click',()=>{patches.beer=!patches.beer;$('#beerStat').innerHTML=patches.beer?'<span class="ok">queued (applied on export)</span>':'';$('#beerBtn').textContent=patches.beer?'Un-queue Enable-Beer':'Apply Enable-Beer patch';flag();});
// tabs
$('#tRoster').addEventListener('click',()=>{$('#tRoster').classList.add('on');$('#tPatch').classList.remove('on');$('#rosterPane').style.display='';$('#patchPane').style.display='none';});
$('#tPatch').addEventListener('click',()=>{$('#tPatch').classList.add('on');$('#tRoster').classList.remove('on');$('#patchPane').style.display='';$('#rosterPane').style.display='none';});
document.addEventListener('dragover',e=>e.preventDefault());
document.addEventListener('drop',e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f){$('#rom').files=e.dataTransfer.files;$('#rom').dispatchEvent(new Event('change'));}});
build();
</script></body></html>"""
html = HTML.replace("__DATA__", DATA)
open(f"{OUT}/rom-studio.html","w",encoding="utf-8").write(html)
print("wrote rom-studio.html (%d bytes); divergent RevC<->DOC2000 = %d records: %s" % (len(html), len(divergent), divergent[:12]))
