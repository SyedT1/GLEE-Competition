const fs = require('fs');
const ref = fs.readFileSync('reference_raw.txt', 'utf8');
const out = fs.readFileSync('build_raw.txt', 'utf8');
function words(s) {
  s = s.replace(/^\s*\d{1,3}\s*$/gm, '').replace(/^\s*\d{1,3}\s+(?=[A-Za-z])/gm, '').replace(/-\r?\n\s*/g, '');
  return (s.toLowerCase().match(/[a-z0-9]+/g) || []);
}
const a = words(ref), b = words(out);
const size = 8;
const grams = new Set();
for (let i=0; i+size<=b.length; i++) grams.add(b.slice(i,i+size).join(' '));
let misses = [], run = null, hit=0;
for (let i=0; i+size<=a.length; i++) {
  const ok = grams.has(a.slice(i,i+size).join(' '));
  if (ok) { hit++; if (run) { misses.push(run); run=null; } }
  else if (!run) run={at:i, len:1}; else run.len++;
}
if (run) misses.push(run);
console.log(JSON.stringify({referenceWords:a.length,outputWords:b.length,matchedEightWordSpans:hit,totalEightWordSpans:a.length-size+1,gramMatchRate:(hit/(a.length-size+1)).toFixed(3),misses:misses.filter(x=>x.len>3).slice(0,40).map(x=>({at:x.at,len:x.len,text:a.slice(x.at,x.at+Math.min(x.len+size-1,32)).join(' ')}))},null,2));

// Greedy resynchronization highlights wording differences while tolerating
// different PDF text-extraction order in floating tables.
let i=0, j=0, changes=[];
while (i<a.length && j<b.length) {
  if (a[i]===b[j]) { i++; j++; continue; }
  let found=null;
  const next = new Map();
  for (let db=0; db<500 && j+db+4<=b.length; db++) {
    const key=b.slice(j+db,j+db+4).join(' ');
    if (!next.has(key)) next.set(key,db);
  }
  for (let da=0; da<500 && i+da+4<=a.length; da++) {
    const db=next.get(a.slice(i+da,i+da+4).join(' '));
    if (db!==undefined && (!found || da+db<found.da+found.db)) found={da,db};
  }
  if (!found) break;
  changes.push({at:i,reference:a.slice(i,i+found.da).join(' '),build:b.slice(j,j+found.db).join(' ')});
  i+=found.da; j+=found.db;
}
console.log('Differences:', JSON.stringify(changes.filter(x=>x.reference || x.build).slice(0,70),null,2));
