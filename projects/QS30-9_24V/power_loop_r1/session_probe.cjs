// Redacted operational view, never print raw session/credentials.
const fs=require('fs'),z=require('zlib'),path=require('path');
function walk(p){return fs.readdirSync(p,{withFileTypes:true}).flatMap(x=>x.isDirectory()?walk(path.join(p,x.name)):[path.join(p,x.name)]);}
for(const p of walk(path.join(__dirname,'.local/dsh_home/sessions')).filter(p=>p.endsWith('.zstd'))){
 try{
 const s=z.zstdDecompressSync(fs.readFileSync(p)).toString();
 const rows=s.trim().split('\n').map(l=>JSON.parse(l));
 console.log(path.basename(path.dirname(p)),rows.length);
 console.log(JSON.stringify(rows.slice(-3).map(r=>({type:r.type,keys:Object.keys(r),dataKeys:Object.keys(r.data||{})}))));
 for(const r of rows){
  if(/model|llm|usage|error/.test(r.type||'')) console.log(JSON.stringify(r).slice(0,700));
 }
 }catch(e){console.log(e.message);}
}
