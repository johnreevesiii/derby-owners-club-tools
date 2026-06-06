#!/usr/bin/env python3
"""doc-core tool #7: Card Differ / Lineage & Pedigree Viewer.

Builds card-differ.html: drop two .card files (207 bytes) -> in-browser decode (JS port of
doc_card.py: US full-stat + JP identity), a field-by-field DIFF table (highlighting changes),
a LINEAGE panel that joins each card's sire/dam names to the embedded breeding pool (all 4
versions) and shows their stats, plus a same-horse check via the triplicated 4-byte UID and a
JP-kana -> EN stat-twin cross-reference.

Provenance: us-card.md / jp-card.md decode (doc_card.py, selftest 11/11 byte-exact),
breeding-system.md pool (doc_core_breeding.json). Offline, data embedded, no deps.
"""
import json, io, os
OUT = r"C:/DerbyOwnersClub/doc-core"
breeding = json.load(io.open(f"{OUT}/doc_core_breeding.json", encoding="utf-8"))

# compact pool for lineage lookup: name(lower) -> {ver,kind,st,sp,sh,ac,ext,bands}
pool_index = {}
for vk, vv in breeding["versions"].items():
    for r in vv.get("pool", []):
        nm = (r.get("name") or r.get("romaji") or r.get("nameJP") or "").strip()
        if not nm:
            continue
        pool_index.setdefault(nm.lower(), []).append({
            "ver": vk, "name": nm, "nameJP": r.get("nameJP"), "kind": r.get("kind"),
            "st": r["st"], "sp": r["sp"], "sh": r["sh"], "ac": r["ac"],
            "ext": r["externals"], "bands": r.get("bands", ""), "index": r.get("index"),
        })
# stat-twin index for JP<->EN crossref: (st,sp,sh,ac) -> names
twin_index = {}
for vk, vv in breeding["versions"].items():
    for r in vv.get("pool", []):
        key = "%d_%d_%d_%d" % (r["st"], r["sp"], r["sh"], r["ac"])
        nm = (r.get("name") or r.get("romaji") or "").strip()
        if nm:
            twin_index.setdefault(key, []).append({"ver": vk, "name": nm, "nameJP": r.get("nameJP")})

POOL = json.dumps(pool_index, ensure_ascii=False)
TWIN = json.dumps(twin_index, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC Card Differ / Lineage</title>
<style>
 body{margin:0;font:13px/1.45 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:10px 18px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:18px;color:#eae8e2}.sub{color:#7fb0bd;font-size:12px;font-weight:400}
 .wrap{padding:14px 18px;max-width:1180px}
 .drops{display:flex;gap:14px;flex-wrap:wrap}
 .drop{flex:1;min-width:300px;border:2px dashed #2a5666;border-radius:8px;padding:14px;background:#0a222b;text-align:center;transition:.15s}
 .drop.over{border-color:#b75527;background:#10303b}
 .drop h2{margin:.2em 0;font-size:14px;color:#9cc}
 .drop input{display:none}
 .pill{display:inline-block;background:#014b50;color:#cfe;border-radius:10px;padding:1px 8px;font-size:11px;margin:2px}
 table{border-collapse:collapse;width:100%;margin-top:8px;background:#08202a}
 th,td{border:1px solid #143b48;padding:3px 8px;text-align:left;font-size:12px}
 th{background:#0a242e;color:#9cc}
 .diff{background:#3a2410;color:#ffd9a8}
 .same td{color:#9fb4bb}
 .l{text-align:left}.r{text-align:right}
 .grid{display:flex;gap:14px;flex-wrap:wrap;margin-top:14px}
 .card{flex:1;min-width:320px;background:#08202a;border:1px solid #143b48;border-radius:8px;padding:10px}
 .card h3{margin:.1em 0 .4em;color:#eae8e2;font-size:14px}
 .ok{color:#7fdca0}.warn{color:#ffb27f}.bad{color:#ff8a8a}.muted{color:#6f9aa6}
 .lin{margin:4px 0;padding:6px;border-left:3px solid #014b50;background:#0a242e;border-radius:0 6px 6px 0}
 .lin b{color:#cfe}
 code{background:#06303a;padding:0 4px;border-radius:3px}
 .note{color:#7fb0bd;font-size:12px;margin:6px 0}
 .stat{font-variant-numeric:tabular-nums}
</style></head><body>
<header><h1>&#127942; DOC Card Differ / Lineage <span class="sub">tool #7 &middot; decode + diff two cards + pedigree against the breeding pool</span></h1></header>
<div class="wrap">
 <div class="note">Drop two <code>.card</code> files (207 bytes; US World-Edition or JP identity). Everything runs locally in your browser &mdash; nothing is uploaded. Decoder is a JS port of <code>doc_card.py</code> (selftest 11/11 byte-exact); lineage joins sire/dam to the embedded breeding pool (all 4 versions).</div>
 <div class="drops">
  <label class="drop" id="dropA"><h2>Card A</h2><div id="nameA" class="muted">click or drop a .card</div><input type="file" id="fileA" accept=".card,.raw,.bin"></label>
  <label class="drop" id="dropB"><h2>Card B (optional &mdash; for diff)</h2><div id="nameB" class="muted">click or drop a .card</div><input type="file" id="fileB" accept=".card,.raw,.bin"></label>
 </div>
 <div id="uidmatch"></div>
 <div id="difftable"></div>
 <div class="grid"><div class="card" id="cardA"></div><div class="card" id="cardB"></div></div>
</div>
<script>
const POOL=__POOL__, TWIN=__TWIN__;
const CARD_LEN=207, TRACK=69;
const SEX={0:"Male",1:"Female",2:"Gelding"};
const LEG=["Front-runner","Start dash","Last spurt","Stretch-runner","Almighty"];
const SILK=['Black','Grey','Blue','Teal','Brown','Maroon','Green','Light Green','Magenta','Light Blue','Purple','Pink','Red','White','Yellow'];
const PB=[[0,47,"Rough"],[48,63,"Imposing"],[64,111,"Calm"],[112,127,"Firm"],[128,175,"Sensitive"],[176,191,"Moody"],[192,239,"Gentle"],[240,255,"Proud"]];
function pband(v){for(const[a,b,n]of PB)if(v>=a&&v<=b)return n;return "?";}
const G1=[{n:"Winter Stakes",b:57,m:1},{n:"Sprinter Trophy",b:55,m:16},{n:"Doc 1000",b:57,m:2},{n:"Doc 2000",b:57,m:4},{n:"Spring Classic",b:57,m:8},{n:"American Oak",b:57,m:128},{n:"American Derby",b:57,m:16},{n:"Summer Grand Prix",b:56,m:1},{n:"Super Dirt GPX",b:56,m:2},{n:"Sprinter Stakes",b:55,m:1},{n:"Stayers Stakes",b:56,m:16},{n:"QE II",b:56,m:32},{n:"Mile Champ",b:56,m:64},{n:"Japan Cup Dirt",b:55,m:8},{n:"Japan Cup",b:56,m:128},{n:"Derby Owners Cup",b:55,m:4},{n:"Hong Kong Derby",b:57,m:64},{n:"Hong Kong Oaks",b:57,m:32}];
// JP kana table (port of doc_card.py)
const COLS={a:[...'アカサタナハマヤラワガザダバパ'],
 i:['イ','キ','シ','チ','ニ','ヒ','ミ',null,'リ',null,'ギ','ジ','ヂ','ビ','ピ'],
 u:['ウ','ク','ス','ツ','ヌ','フ','ム','ユ','ル',null,'グ','ズ','ヅ','ブ','プ'],
 e:['エ','ケ','セ','テ','ネ','ヘ','メ',null,'レ',null,'ゲ','ゼ','デ','ベ','ペ'],
 o:[...'オコソトノホモヨロヲゴゾドボポ']};
const JPT={};['a','i','u','e','o'].forEach((v,ci)=>{for(let r=0;r<15;r++){if(COLS[v][r]!=null)JPT[ci*15+r]=COLS[v][r];}});
Object.assign(JPT,{0x4b:'ァ',0x4c:'ィ',0x4d:'ゥ',0x4e:'ェ',0x4f:'ォ',0x50:'ャ',0x51:'ュ',0x52:'ョ',0x53:'ッ',0x54:'ー',0x45:'ン'});
function aget(c,t,k){return c[t*TRACK+(TRACK-k)];}
function asciiName(c,t,hi,lo){let o='';for(let k=hi;k>=lo;k--){let b=aget(c,t,k)&0x7f;if(b>=32&&b<127)o+=String.fromCharCode(b);}return o.replace(/\s+$/,'').replace(/^\s+/,'');}
function detectKind(c){let us=true;const sig='SEGABEF0';for(let i=0;i<8;i++)if(c[0x8A+i]!==sig.charCodeAt(i)){us=false;break;}if(us)return'us';if(c[0x20]===0x03&&c[0x21]===0x02)return'jp';return'unknown';}
function legType(ex){const all=[ex.start,ex.corner,ex.oob,ex.competing,ex.tenacious,ex.spurt];if(all.every(v=>v===all[0]))return 4;const con=[ex.start,ex.oob,ex.competing,ex.tenacious,ex.spurt];let rank=1+con.filter(v=>v>ex.start).length;return rank<=1?0:rank===2?1:rank===3?2:3;}
function decodeUS(c){
 const g=(t,k)=>aget(c,t,k);
 const ext={start:g(1,43)+1,corner:g(1,42)+1,oob:g(1,41)+1,competing:g(1,40)+1,tenacious:g(1,39)+1,spurt:g(1,38)+1};
 const titles=G1.filter(r=>({55:g(1,55),56:g(1,56),57:g(1,57)})[r.b]&r.m).map(r=>r.n);
 return {kind:'us',uid:[g(0,2),g(0,3),g(0,4),g(0,5)],
  name:asciiName(c,0,69,51),sire:asciiName(c,0,49,31),dam:asciiName(c,0,29,11),
  sex:SEX[g(1,16)]||'?',coatBase:g(0,8),coatMod:g(0,9),personality:pband(g(0,6))+' ('+g(0,6)+')',
  ext, internals:{stamina:Math.min(g(1,69),60),speed:Math.min(g(1,65),60),sharp:Math.min(g(1,61),60)},
  dirt:g(2,61),hearts:((g(1,37)+1)>>2),legType:LEG[legType(ext)],
  races:{total:g(1,35),won:g(1,49),place:g(1,48),show:g(1,47),out:g(1,46)},
  earnings:(g(1,51)*65536+g(1,52)*256+g(1,53))*1000,
  silk:{pattern:g(1,15),c1:SILK[g(1,14)]||g(1,14),c2:SILK[g(1,13)]||g(1,13)},
  g1:titles};
}
function jpField(c,start){let seg=[],i=start;while(i<0x45&&c[i]!==0x7d){seg.push(c[i]);i++;}let s=seg.map(b=>JPT[b]||'').join('');return {text:s,end:i};}
function decodeJP(c){
 let i=0x28,f=[];for(let n=0;n<3;n++){const r=jpField(c,i);f.push(r.text);i=r.end;while(i<0x45&&c[i]===0x7d)i++;}
 return {kind:'jp',uid:[c[0x25],c[0x26],c[0x27]],name:f[0],sire:f[1],dam:f[2],
  leadId:[c[0x25],c[0x26],c[0x27]],trailer:[c[0x43],c[0x44]],note:'JP identity/pedigree card: stats are cabinet-side, not on the card.'};
}
function decode(bytes){if(bytes.length!==CARD_LEN)return{kind:'unknown',err:'card is '+bytes.length+' bytes, expected 207'};const k=detectKind(bytes);if(k==='us')return decodeUS(bytes);if(k==='jp')return decodeJP(bytes);return{kind:'unknown',err:'no SEGABEF0 and no JP skeleton'};}

// ---- lineage lookup ----
function lookup(name){if(!name)return[];return POOL[name.toLowerCase().trim()]||[];}
function twins(rec){const key=rec.st+'_'+rec.sp+'_'+rec.sh+'_'+rec.ac;return (TWIN[key]||[]).filter(t=>t.name.toLowerCase()!==rec.name.toLowerCase());}
function lineHTML(role,name){
 const hits=lookup(name);
 if(!name) return '<div class="lin"><b>'+role+':</b> <span class="muted">(none)</span></div>';
 if(!hits.length) return '<div class="lin"><b>'+role+':</b> '+esc(name)+' <span class="warn">&mdash; not in breeding pool</span></div>';
 let h='<div class="lin"><b>'+role+':</b> '+esc(name)+' ';
 hits.forEach(r=>{
  h+='<div style="margin:3px 0 3px 10px">'+'<span class="pill">'+r.ver+'</span> '+(r.kind||'')+
     ' &mdash; <span class="stat">ST '+r.st+' / SP '+r.sp+' / SH '+r.sh+' / dirt '+r.ac+'</span>'+
     ' <span class="muted">ext '+Object.values(r.ext).join('/')+' &middot; apt '+esc(r.bands||'')+'</span>';
  const tw=twins(r);
  if(tw.length)h+=' <span class="muted">&#8596; '+tw.map(t=>esc((t.nameJP?t.nameJP+' ':'')+t.name)+' ['+t.ver+']').join(', ')+'</span>';
  h+='</div>';
 });
 return h+'</div>';
}
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}

let A=null,B=null;
function cardHTML(d){
 if(!d)return '<span class="muted">no card</span>';
 if(d.err)return '<span class="bad">decode failed: '+esc(d.err)+'</span>';
 if(d.kind==='jp'){
  return '<h3>'+esc(d.name||'(JP card)')+' <span class="pill">JP</span></h3>'+
   '<div>Sire: '+esc(d.sire)+' &middot; Dam: '+esc(d.dam)+'</div>'+
   '<div class="muted">lead-id '+d.leadId.map(x=>x.toString(16).padStart(2,'0')).join(' ')+' &middot; trailer '+d.trailer.map(x=>x.toString(16).padStart(2,'0')).join(' ')+'</div>'+
   '<div class="note">'+esc(d.note)+'</div>'+
   '<h3>Pedigree</h3>'+lineHTML('Sire',d.sire)+lineHTML('Dam',d.dam);
 }
 const it=d.internals,ex=d.ext;
 return '<h3>'+esc(d.name||'(unnamed)')+' <span class="pill">US</span> <span class="muted">UID '+d.uid.map(x=>x.toString(16).padStart(2,'0')).join('')+'</span></h3>'+
  '<div class="stat">'+d.sex+' &middot; '+d.legType+' &middot; '+d.personality+' &middot; '+d.hearts+'&#10084; &middot; dirt '+d.dirt+'</div>'+
  '<div class="stat">Internals: ST '+it.stamina+' / SP '+it.speed+' / SH '+it.sharp+'</div>'+
  '<div class="stat">Externals: start '+ex.start+' corner '+ex.corner+' oob '+ex.oob+' comp '+ex.competing+' ten '+ex.tenacious+' spurt '+ex.spurt+'</div>'+
  '<div class="stat">Record: '+d.races.total+' races &middot; W'+d.races.won+' P'+d.races.place+' S'+d.races.show+' O'+d.races.out+' &middot; $'+d.earnings.toLocaleString()+'</div>'+
  '<div class="stat muted">Silk '+d.silk.pattern+' '+d.silk.c1+'/'+d.silk.c2+'</div>'+
  (d.g1.length?'<div class="ok">G1: '+d.g1.map(esc).join(', ')+'</div>':'<div class="muted">No G1 titles</div>')+
  '<h3>Pedigree</h3>'+lineHTML('Sire',d.sire)+lineHTML('Dam',d.dam);
}
const FIELDS=[
 ['Kind',d=>d.kind],['Name',d=>d.name],['Sire',d=>d.sire],['Dam',d=>d.dam],
 ['UID',d=>d.uid?d.uid.map(x=>x.toString(16).padStart(2,'0')).join(''):''],
 ['Sex',d=>d.sex],['Leg type',d=>d.legType],['Personality',d=>d.personality],['Hearts',d=>d.hearts],
 ['Stamina',d=>d.internals&&d.internals.stamina],['Speed',d=>d.internals&&d.internals.speed],['Sharp',d=>d.internals&&d.internals.sharp],
 ['Dirt apt',d=>d.dirt],
 ['Ext start',d=>d.ext&&d.ext.start],['Ext corner',d=>d.ext&&d.ext.corner],['Ext oob',d=>d.ext&&d.ext.oob],
 ['Ext competing',d=>d.ext&&d.ext.competing],['Ext tenacious',d=>d.ext&&d.ext.tenacious],['Ext spurt',d=>d.ext&&d.ext.spurt],
 ['Races',d=>d.races&&d.races.total],['Wins',d=>d.races&&d.races.won],['Earnings',d=>d.earnings],
 ['G1 titles',d=>d.g1&&d.g1.join(', ')],['Silk',d=>d.silk&&(d.silk.pattern+' '+d.silk.c1+'/'+d.silk.c2)],
];
function render(){
 document.getElementById('cardA').innerHTML=cardHTML(A);
 document.getElementById('cardB').innerHTML=cardHTML(B);
 const um=document.getElementById('uidmatch');
 if(A&&B&&A.uid&&B.uid){
  const same=A.uid.join()===B.uid.join();
  um.innerHTML='<div class="note">'+(same?'<span class="ok">&#9679; Same horse / lineage UID</span> &mdash; these cards share the triplicated 4-byte UID':'<span class="warn">&#9679; Different UIDs</span> &mdash; not the same on-card horse')+'</div>';
 } else um.innerHTML='';
 const dt=document.getElementById('difftable');
 if(A&&B&&!A.err&&!B.err){
  let h='<table><thead><tr><th>Field</th><th>Card A</th><th>Card B</th></tr></thead><tbody>';
  for(const[label,fn]of FIELDS){
   let a=fn(A),b=fn(B);a=(a==null?'':a);b=(b==null?'':b);
   const diff=String(a)!==String(b);
   h+='<tr class="'+(diff?'diff':'same')+'"><td class="l">'+label+'</td><td class="l">'+esc(a)+'</td><td class="l">'+esc(b)+'</td></tr>';
  }
  dt.innerHTML='<h3 style="margin:14px 0 0">Field-by-field diff <span class="muted">(changed rows highlighted)</span></h3>'+h+'</tbody></table>';
 } else dt.innerHTML='';
}
function loadFile(file,slot){
 const r=new FileReader();
 r.onload=()=>{const b=new Uint8Array(r.result);const d=decode(b);if(slot==='A'){A=d;document.getElementById('nameA').textContent=file.name;}else{B=d;document.getElementById('nameB').textContent=file.name;}render();};
 r.readAsArrayBuffer(file);
}
function wire(dropId,fileId,slot){
 const drop=document.getElementById(dropId),inp=document.getElementById(fileId);
 inp.addEventListener('change',e=>{if(e.target.files[0])loadFile(e.target.files[0],slot);});
 drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over');});
 drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
 drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('over');if(e.dataTransfer.files[0])loadFile(e.dataTransfer.files[0],slot);});
}
wire('dropA','fileA','A');wire('dropB','fileB','B');
</script></body></html>"""

html = HTML.replace("__POOL__", POOL).replace("__TWIN__", TWIN)
open(f"{OUT}/card-differ.html", "w", encoding="utf-8").write(html)
print("wrote card-differ.html (%d bytes), pool names=%d, twin keys=%d" % (len(html), len(pool_index), len(twin_index)))
