// Read ALL concatenated zstd frames. Export selected operational fields only.
const fs=require('fs'),z=require('zlib'),path=require('path');
const root=__dirname;
function walk(p){return fs.readdirSync(p,{withFileTypes:true}).flatMap(x=>x.isDirectory()?walk(path.join(p,x.name)):[path.join(p,x.name)]);}
const sessions=[];
for(const p of [path.join(root,'.local/dsh_home/sessions'),path.join(root,'extension/.local/dsh_home/sessions')].flatMap(walk).filter(p=>p.endsWith('.zstd'))){
 const b=fs.readFileSync(p);let offset=0,parts=[];
 while(offset<b.length){const d=z.zstdDecompressSync(b.subarray(offset),{info:true});if(!d.engine.bytesWritten)throw Error('No frame progress');parts.push(d.buffer.toString());offset+=d.engine.bytesWritten;}
 const rows=parts.join('').trim().split('\n').map(JSON.parse);
 const task=['sense_root','passive_bounds','settling_analysis','sense_candidate','startup_candidate','loop_candidate','device_energy_audit','startup_path_audit','ripple_split','device_followup','startup_followup','loop_followup'].find(t=>rows.some(r=>JSON.stringify(r).includes('TASK_ID: '+t)));
 const headers=rows.filter(r=>r.type==='request/header').map(r=>r.data.header.config);
 const use=rows.filter(r=>r.type==='assistant/message').map(r=>r.data.usage||{});
 const calls=rows.filter(r=>r.type==='tool/call');
 sessions.push({session:path.basename(path.dirname(p)),task,zstd_frames:parts.length,compressed_bytes:b.length,
  request_header_records:headers.length,headers:headers.map(c=>({provider:c.provider,model:c.model,maxTokens:c.maxTokens})),
  tool_calls:calls.length,tool_names:[...new Set(calls.map(r=>r.data.name))],
  usage_records:use.length,usage:use.reduce((a,u)=>{for(const[k,v]of Object.entries(u))if(typeof v==='number')a[k]=(a[k]||0)+v;return a;},{}),
  all_requests_expected:headers.length>0&&headers.every(c=>c.provider==='deepseek-official'&&c.model==='deepseek-flash'),
  last_event:rows.at(-1).type});
}
fs.writeFileSync(path.join(root,'evidence/preflight/dsh_runtime.json'),JSON.stringify({sessions,scope:'Operational metadata only, sessions are not token/currency caps; concatenated frames all decoded'},null,2)+'\n');
console.log(JSON.stringify(sessions.map(s=>({task:s.task,requests:s.request_header_records,tools:s.tool_calls,expected:s.all_requests_expected,usage:s.usage})),null,2));
