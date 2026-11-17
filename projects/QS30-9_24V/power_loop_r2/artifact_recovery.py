"""One bounded transfer retry; no deletion or replacement of a remote asset."""
import argparse,json,time,urllib.parse
from pathlib import Path
import lab,artifact_store as api,artifact_parallel as parallel

def main(name):
 state=json.loads(api.STATE.read_text(encoding='utf8'));tok=api.token()
 manifest=json.loads((lab.HERE/'evidence/raw_archive_manifest.json').read_text(encoding='utf8'))
 parts={Path(p['path']).name:p for r in manifest['records']for p in r['parts']}
 if name not in parts:raise ValueError('Name not in frozen archive manifest')
 existing=[x for x in parallel.remote_assets(tok,state)if x['name']==name]
 if existing:raise ValueError('Existing remote asset preserved; reconcile and inspect before retry')
 part=parts[name];p=lab.HERE/part['path'];start=time.monotonic()
 if p.stat().st_size!=part['bytes']or lab.sha(p)!=part['sha256']:raise ValueError('Local archive changed')
 result=dict(name=name,max_read_wall_s=900,socket_timeout_s=600,attempts=1,scope='Archive transfer only; native waveform and prior failure preserved')
 try:
  url=state['upload_url']+'?'+urllib.parse.urlencode({'name':name})
  with p.open('rb')as f:r=api.request(url,tok,parallel.BoundedFile(f),'POST',{'Content-Type':'application/octet-stream','Content-Length':str(part['bytes'])},600)
  if r['state']!='uploaded'or r['size']!=part['bytes']or r.get('digest')!='sha256:'+part['sha256']:raise ValueError('Remote integrity mismatch')
  result.update(status='UPLOADED',id=r['id'],bytes=r['size'],remote_digest=r['digest'])
 except Exception as e:result.update(status='EXECUTION_FAIL',error=repr(e))
 result['elapsed_s']=time.monotonic()-start
 out=lab.HERE/'evidence/preflight'/('transfer_retry_'+name+'.json')
 if out.exists():raise FileExistsError('Retry audit already exists; preserve it')
 lab.dump(out,result);print(json.dumps(result),flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('name');main(a.parse_args().name)
