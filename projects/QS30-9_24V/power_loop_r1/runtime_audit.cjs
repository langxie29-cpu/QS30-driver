// Export only selected non-secret fields, never the original session bodies.
const fs=require('fs'),z=require('zlib'),path=require('path');
const root=__dirname;
function walk(p){return fs.readdirSync(p,{withFileTypes:true}).flatMap(x=>x.isDirectory()?walk(path.join(p,x.name)):[path.join(p,x.name)]);}
const sessions=[];
for(const p of walk(path.join(root,'.local/dsh_home/sessions')).filter(p=>p.endsWith('.zstd'))){
 try{
 const rows=z.zstdDecompressSync(fs.readFileSync(p)).toString().trim().split('\n').map(JSON.parse);
 const headers=rows.filter(r=>r.type==='request/header').map(r=>r.data.header.config);
 const use=rows.filter(r=>r.type==='assistant/message').map(r=>r.data.usage||{});
 sessions.push({session:path.basename(path.dirname(p)),headers:headers.map(c=>({provider:c.provider,model:c.model,maxTokens:c.maxTokens,reasoningEffort:c.reasoningEffort})),
   request_count:headers.length,tool_calls:rows.filter(r=>r.type==='tool/call').length,
   usage:use.reduce((a,b)=>{for(const [k,v] of Object.entries(b))if(typeof v==='number')a[k]=(a[k]||0)+v;return a;},{}),
   last_event:rows.at(-1).type,endpoint:'https://api.deepseek.com (explicit dedicated overlay; no packet capture)',
   all_requests_expected:headers.length>0&&headers.every(c=>c.provider==='deepseek-official'&&c.model==='deepseek-flash')});
 }catch(e){sessions.push({error:e.message});}
}
fs.mkdirSync(path.join(root,'evidence/preflight'),{recursive:true});
fs.writeFileSync(path.join(root,'evidence/preflight/dsh_runtime.json'),JSON.stringify({sessions},null,2)+'\n');
console.log(JSON.stringify(sessions.map(s=>({session:s.session,requests:s.request_count,tools:s.tool_calls,expected:s.all_requests_expected,last:s.last_event}))));
