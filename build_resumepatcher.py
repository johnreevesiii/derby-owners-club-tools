#!/usr/bin/env python3
"""doc-core tool #9: Battery-Resume Patcher (NVRAM header / resume-counter editor).

Builds resume-patcher.html: drop a cabinet .sram (32 KB BBSRAM) -> shows both redundant save
regions' headers, highlights the +0x08 LE32 counter (the leading candidate for the program/pace
resume-section counter, per nvram.md), and lets you edit it (and any header byte). On export it
writes the edit to BOTH regions and RE-COMPUTES the region checksum IF the algorithm can be
auto-detected against your own file (it tries a family of LE16 sum variants and uses the one whose
result already matches the file's stored checksum). If none match, it writes the bytes and clearly
flags that the checksum was NOT recomputed -> validate on hardware/emulator.

Provenance: nvram.md region map (doc_core_nvram.json regionOffsets/checksumLocations, corrected
offsets baked in). Checksum algorithm is NOT yet reversed; the runtime self-test is the workaround.
HARDWARE-GATED: whether +0x08 is the resume counter (vs a date/win stamp) needs edit-and-observe.
"""
import json, io
OUT = r"C:/DerbyOwnersClub/doc-core"
N = json.load(io.open(f"{OUT}/doc_core_nvram.json", encoding="utf-8"))
ro = N["schema"]["regionOffsets"]
cfg = {
 "regionStride": N["schema"]["regionStride"],
 "region1": {k: ro["region1"][k] for k in ro["region1"] if k != "note"},
 "region2": {k: ro["region2"][k] for k in ro["region2"] if k != "note"},
 "checksum": N["schema"]["checksumLocations"],
}
DATA = json.dumps(cfg, ensure_ascii=False)

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>DOC Battery-Resume Patcher</title>
<style>
 body{margin:0;font:13px/1.45 system-ui,Segoe UI,Arial;background:#06181f;color:#e8eef0}
 header{padding:10px 18px;background:#0a242e;border-bottom:1px solid #143b48}
 h1{margin:0;font-size:18px;color:#eae8e2}.sub{color:#7fb0bd;font-size:12px;font-weight:400}
 .wrap{padding:14px 18px;max-width:900px}
 .pill{display:inline-block;background:#014b50;color:#cfe;border-radius:10px;padding:3px 10px;cursor:pointer}
 button{background:#014b50;color:#cfe;border:0;border-radius:5px;padding:6px 12px;cursor:pointer}
 button.act{background:#b75527;color:#fff}button:disabled{opacity:.4;cursor:not-allowed}
 .card{background:#08202a;border:1px solid #143b48;border-radius:8px;padding:12px;margin:10px 0}
 .card h3{margin:.2em 0;color:#eae8e2;font-size:14px}
 table{border-collapse:collapse;margin-top:6px}
 th,td{border:1px solid #143b48;padding:3px 9px;text-align:left;font-size:12px}
 th{background:#0a242e;color:#9cc}
 input.v{width:120px;background:#06303a;color:#fff;border:1px solid #2a5666;border-radius:4px;padding:3px 6px;font-family:Consolas,monospace}
 .mono{font-family:Consolas,monospace}
 .ok{color:#7fdca0}.warn{color:#ffb27f}.bad{color:#ff8a8a}.muted{color:#6f9aa6}
 .note{color:#7fb0bd;font-size:12px;margin:8px 0}
 .hex{font-family:Consolas,monospace;font-size:11px;color:#9fb4bb;white-space:pre;background:#06181f;padding:6px;border-radius:5px;overflow:auto}
</style></head><body>
<header><h1>&#128267; DOC Battery-Resume Patcher <span class="sub">tool #9 &middot; NVRAM resume-counter / header editor</span></h1></header>
<div class="wrap">
 <div class="note">Drop a cabinet <code>.sram</code> (32&nbsp;KB BBSRAM). This targets the header <b>+0x08 LE32</b> in each save region &mdash; the leading candidate for the program/pace <b>resume-section counter</b>. <span class="warn">It is a candidate, not confirmed</span>: whether editing it makes the cabinet resume mid-program needs edit-and-observe on hardware/emulator. The checksum algorithm isn't reversed, so on export the tool auto-detects it against your file and only recomputes if it can; otherwise it flags it.</div>
 <label class="pill" style="cursor:pointer">Drop / pick .sram<input id="f" type="file" accept=".sram,.nv,.bin" style="display:none"></label>
 <span id="status" class="muted"> &mdash; no file loaded</span>
 <div id="body"></div>
 <div id="exportRow" style="display:none;margin-top:12px">
  <button id="exp" class="act">&#128190; Export patched .sram</button>
  <span id="expstat" class="muted"></span>
 </div>
</div>
<script>
const CFG=__DATA__;
let buf=null;const $=s=>document.querySelector(s);
const H=n=>parseInt(n,16);
function u32(b,o){return (b[o]|(b[o+1]<<8)|(b[o+2]<<16)|(b[o+3]<<24))>>>0;}
function setU32(b,o,v){b[o]=v&0xFF;b[o+1]=(v>>>8)&0xFF;b[o+2]=(v>>>16)&0xFF;b[o+3]=(v>>>24)&0xFF;}
function u16(b,o){return (b[o]|(b[o+1]<<8))&0xFFFF;}
function setU16(b,o,v){b[o]=v&0xFF;b[o+1]=(v>>>8)&0xFF;}
function hexdump(b,start,len){let s='';for(let i=0;i<len;i+=16){let h='',a='';for(let j=0;j<16&&i+j<len;j++){const c=b[start+i+j];h+=c.toString(16).padStart(2,'0')+' ';a+=(c>=32&&c<127)?String.fromCharCode(c):'.';}s+=(start+i).toString(16).padStart(5,'0')+'  '+h.padEnd(48,' ')+' '+a+'\n';}return s;}

// checksum self-test: try LE16 sum-of-bytes and sum-of-u16 over candidate ranges; return the
// variant whose computed value == the stored checksum for region1 (and same variant for region2).
function checksumVariants(){
 return [
  {name:'sum8 [hdr+2..trailer)',  calc:(b,hs,tr)=>{let s=0;for(let i=hs+2;i<tr;i++)s=(s+b[i])&0xFFFF;return s;}},
  {name:'sum16 [hdr+2..trailer)', calc:(b,hs,tr)=>{let s=0;for(let i=hs+2;i<tr;i+=2)s=(s+u16(b,i))&0xFFFF;return s;}},
  {name:'sum8 [hdr+0x10..trailer)',calc:(b,hs,tr)=>{let s=0;for(let i=hs+0x10;i<tr;i++)s=(s+b[i])&0xFFFF;return s;}},
  {name:'sum8 [hdr+0x38..trailer)',calc:(b,hs,tr)=>{let s=0;for(let i=hs+0x38;i<tr;i++)s=(s+b[i])&0xFFFF;return s;}},
 ];
}
function detectChecksum(b){
 const r1hs=H(CFG.region1.header), r1tr=H(CFG.region1.trailer);
 const r2hs=H(CFG.region2.header), r2tr=H(CFG.region2.trailer);
 const stored1=u16(b,r1hs), stored2=u16(b,r2hs);
 for(const v of checksumVariants()){
  if((v.calc(b,r1hs,r1tr)===stored1)&&(v.calc(b,r2hs,r2tr)===stored2))return v;
 }
 return null;
}
function render(){
 const b=buf;const r1hs=H(CFG.region1.header),r2hs=H(CFG.region2.header);
 const c1=u32(b,r1hs+8), c2=u32(b,r2hs+8);
 const det=detectChecksum(b);
 let h='<div class="card"><h3>Resume-counter candidate (header +0x08 LE32)</h3>'
  +'<table><tr><th>Region</th><th>Header @</th><th>+0x08 counter</th><th>New value</th></tr>'
  +'<tr><td>Region 1 (primary)</td><td class="mono">'+CFG.region1.header+'</td><td class="mono">'+c1+' ('+('0x'+c1.toString(16))+')</td>'
   +'<td><input class="v" id="nv1" value="'+c1+'"></td></tr>'
  +'<tr><td>Region 2 (backup)</td><td class="mono">'+CFG.region2.header+'</td><td class="mono">'+c2+' ('+('0x'+c2.toString(16))+')</td>'
   +'<td><input class="v" id="nv2" value="'+c2+'"></td></tr></table>'
  +'<div class="note">Tip: set both regions to the same value. Other header bytes shown below if you need them.</div></div>';
 h+='<div class="card"><h3>Checksum self-test</h3>'+(det
   ? '<span class="ok">&#9679; Detected: <b>'+det.name+'</b> &mdash; matches the stored checksum in BOTH regions. The tool will recompute it on export, so the cabinet should accept the edit.</span>'
   : '<span class="warn">&#9679; Not auto-detected</span> &mdash; none of the tested LE16 sum variants reproduce this file\'s stored checksum (it may use a different algorithm). On export the edit is written but the checksum is left as-is; <b>validate on hardware</b> (the cabinet may reject it).')
  +'<div class="note">Stored checksums: region1 @'+CFG.region1.header+' = 0x'+u16(b,r1hs).toString(16)+' (dup @0x208), region2 @'+CFG.region2.header+' = 0x'+u16(b,r2hs).toString(16)+'.</div></div>';
 h+='<div class="card"><h3>Region 1 header (0x1f8..) hexdump</h3><div class="hex">'+hexdump(b,r1hs,0x40)+'</div>'
   +'<h3>Region 2 header (0x15bc..) hexdump</h3><div class="hex">'+hexdump(b,r2hs,0x40)+'</div></div>';
 $('#body').innerHTML=h;
 window.__det=det;
}
$('#f').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();
 r.onload=()=>{buf=new Uint8Array(r.result);
  if(buf.length<H(CFG.region2.trailer)){$('#status').innerHTML=' &mdash; <span class="bad">file is '+buf.length+' bytes; expected ~32768 BBSRAM</span>';$('#body').innerHTML='';$('#exportRow').style.display='none';return;}
  $('#status').innerHTML=' &mdash; <span class="ok">'+f.name+' ('+buf.length+' bytes)</span>';
  render();$('#exportRow').style.display='';
 };r.readAsArrayBuffer(f);});
$('#exp').addEventListener('click',()=>{
 const out=buf.slice();const r1hs=H(CFG.region1.header),r2hs=H(CFG.region2.header);
 const nv1=parseInt($('#nv1').value)>>>0, nv2=parseInt($('#nv2').value)>>>0;
 setU32(out,r1hs+8,nv1);setU32(out,r2hs+8,nv2);
 let cs='';const det=window.__det;
 if(det){
  const r1tr=H(CFG.region1.trailer),r2tr=H(CFG.region2.trailer);
  const v1=det.calc(out,r1hs,r1tr),v2=det.calc(out,r2hs,r2tr);
  setU16(out,r1hs,v1);setU16(out,0x208,v1);setU16(out,r2hs,v2);setU16(out,0x15cc,v2);
  cs=' &middot; checksums recomputed ('+det.name+')';
 } else cs=' &middot; <span class="warn">checksum NOT recomputed (validate on hardware)</span>';
 const b=new Blob([out],{type:'application/octet-stream'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='patched.sram';a.click();
 $('#expstat').innerHTML='<span class="ok">exported</span> (region1='+nv1+', region2='+nv2+')'+cs;
});
document.addEventListener('dragover',e=>e.preventDefault());
document.addEventListener('drop',e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f){$('#f').files=e.dataTransfer.files;$('#f').dispatchEvent(new Event('change'));}});
</script></body></html>"""
html = HTML.replace("__DATA__", DATA)
open(f"{OUT}/resume-patcher.html", "w", encoding="utf-8").write(html)
print("wrote resume-patcher.html (%d bytes)" % len(html))
