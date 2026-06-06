#!/usr/bin/env python3
"""Shared universal horse-file loader (single source of truth for the Suite).

Every Suite tool that opens a horse file gets the SAME normalizer via this constant, so the
two on-disk formats are handled identically and nothing drifts between tools:
  - NEW binary  .card  : the 207-byte Flycast payload (used as-is)
  - OLD text    .raw    : the card-reader export (3 tracks x 144 hex under [DATA]) -> decoded
                          back to the same 207-byte canonical layout

Ported byte-for-byte from the Stable Management System (Tools/DOC-Card-Creator.html):
decodeTrack() + parseRawFile(). After normalize(), a tool's existing 207-byte logic works for
BOTH formats unchanged. kind() classifies us / jp / unknown so each tool can render JP (identity
only, no on-card stats) gracefully instead of rejecting it.

Inject by putting the token  __LOADER__  inside the page's first <script> block and calling
  .replace("__LOADER__", LOADER_JS)  in the generator. Exposes window.DOCcard.
"""

LOADER_JS = r"""
/* ===== DOC universal horse-file loader (shared; generated from _loader_js.py) =====
   Normalizes EITHER the new 207-byte binary .card OR the old text .raw export into the one
   207-byte canonical card layout, so each tool's card logic works for both. Read-only. */
(function(g){
 function decodeTrack(hex){            // 144 hex chars -> arHex[1..69]  (SMS decodeTrack, byte-exact)
  if(!hex||hex.length!==144)return null;
  var mc=256-parseInt(hex.slice(2,4),16); if(!mc)return null;
  var a=new Array(70).fill(0);
  var t=parseInt(hex.slice(140,142),16)-mc+1;
  t=(parseInt(hex.slice(138,140),16)%mc)*256+t; a[69]=Math.floor(t/mc);
  for(var c=68;c>=1;c--){
   var hi=parseInt(hex.slice(c*2+2,c*2+4),16), lo=parseInt(hex.slice(c*2,c*2+2),16);
   t=Math.floor(hi/mc)*mc; t=(lo%mc)*256+t; a[c]=Math.floor(t/mc);
  }
  return a;
 }
 function rawToCard(text){             // .raw text -> Uint8Array(207) or null  (SMS parseRawFile + reverse-pack)
  var lines=text.replace(/\r\n/g,'\n').split('\n'), di=-1;
  for(var i=0;i<lines.length;i++){ if(lines[i].indexOf('[DATA]')>=0){di=i;break;} }
  if(di<0)return null;
  var tracks=[];
  for(var j=di+1;j<lines.length&&tracks.length<3;j++){
   var l=lines[j].trim(); if(!l||l.charAt(0)==='[')continue;
   l=l.replace(/^[^0-9A-Fa-f]+/,'');  // strip the leading track marker (control byte 0x01-03 or a glyph)
   if(l.length===144&&/^[0-9A-Fa-f]+$/.test(l))tracks.push(l.toUpperCase());
  }
  if(tracks.length!==3)return null;
  var bytes=new Uint8Array(207);
  for(var t=0;t<3;t++){ var ar=decodeTrack(tracks[t]); if(!ar)return null;
   for(var k=1;k<=69;k++)bytes[t*69+(69-k)]=ar[k]; }            // store reversed, same as a binary .card
  return bytes;
 }
 function normalize(u8){               // any uploaded file (Uint8Array) -> 207-byte card or null
  if(!u8)return null;
  if(u8.length===207)return u8;                                 // already a binary .card
  var s=''; for(var i=0;i<u8.length;i++)s+=String.fromCharCode(u8[i]);
  return rawToCard(s);                                          // else parse as text .raw export
 }
 function kind(c){                     // 'us' (World Edition) | 'jp' (DOC 2000/'99) | 'unknown'
  if(!c||c.length!==207)return 'unknown';
  var ok=true; for(var i=0;i<8;i++){ if(c[0x8A+i]!=='SEGABEF0'.charCodeAt(i)){ok=false;break;} }
  if(ok)return 'us';
  if(c[0x20]===0x03&&c[0x21]===0x02)return 'jp';
  return 'unknown';
 }
 g.DOCcard={normalize:normalize,kind:kind,rawToCard:rawToCard,decodeTrack:decodeTrack};
})(window);
"""
