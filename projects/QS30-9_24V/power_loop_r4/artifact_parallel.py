"""Parallel draft-asset transfer; raw evidence and prior transfer attempts preserved."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import argparse,json,threading,time,urllib.parse
import artifact_store as api
import r4lib as lab
def remote_assets(tok,state):
 result=[];page=1
 while True:
  rows=api.request(f'https://api.github.com/repos/{api.REPO}/releases/{state["id"]}/assets?per_page=100&page={page}',tok,timeout=60)
  result.extend(rows)
  if len(rows)<100:return result
  page+=1
class BoundedFile:
 def __init__(self,f):self.f=f;self.start=time.monotonic()
 def read(self,n=-1):
  if time.monotonic()-self.start>900:raise TimeoutError('900s asset transfer wall budget')
  return self.f.read(n)
def main(workers,reconcile=False):
 tok=api.token();state=api.create(tok);manifest=json.loads((lab.HERE/'evidence/raw_archive_manifest.json').read_text(encoding='utf8'))
 wanted={Path(p['path']).name:p for rec in manifest['records'] for p in rec['parts']}
 existing={x['name']:x for x in remote_assets(tok,state)}
 if reconcile:
  checked={};pending=[]
  for name,p in wanted.items():
   x=existing.get(name)
   if not x or x['state']!='uploaded' or x['size']!=p['bytes']:pending.append(name);continue
   if x.get('digest')!='sha256:'+p['sha256']:raise ValueError('Remote SHA256 missing or mismatched; audit cannot pass')
   checked[name]=dict(id=x['id'],bytes=x['size'],local_sha256=p['sha256'],remote_digest=x.get('digest'),browser_download_url=x['browser_download_url'],api_url=x['url'],state=x['state'])
  state['assets']=checked;state['pending_assets']=pending;state['expected_assets']=len(wanted);state['status']='COMPLETE_REMOTE_DIGEST_AUDIT' if not pending else 'INCOMPLETE_TRANSFER';lab.dump(api.STATE,state)
  print(json.dumps(dict(expected=len(wanted),uploaded_verified=len(checked),pending=len(pending))));return
 jobs=[(n,p)for n,p in wanted.items()if n not in existing]
 log=lab.HERE/'evidence/parallel_upload_log.jsonl';lock=threading.Lock()
 def one(name,p):
  start=time.monotonic();file=lab.HERE/p['path']
  try:
   if lab.sha(file)!=p['sha256']:raise ValueError('Local part hash changed')
   url=state['upload_url']+'?'+urllib.parse.urlencode({'name':name})
   with file.open('rb') as f:x=api.request(url,tok,BoundedFile(f),'POST',{'Content-Type':'application/octet-stream','Content-Length':str(p['bytes'])},600)
   if x['state']!='uploaded' or x['size']!=p['bytes']:raise ValueError('Remote state/size mismatch')
   if x.get('digest')!='sha256:'+p['sha256']:raise ValueError('Remote SHA256 missing or mismatched; audit cannot pass')
   r=dict(name=name,status='UPLOADED',bytes=x['size'],remote_digest=x.get('digest'),id=x['id'],elapsed_s=time.monotonic()-start)
  except Exception as e:r=dict(name=name,status='EXECUTION_FAIL',error=repr(e),elapsed_s=time.monotonic()-start)
  with lock:
   with log.open('a',encoding='utf8') as f:f.write(json.dumps(r)+'\n')
  return r
 print('queued',len(jobs),'existing',len(existing),'workers',workers,flush=True)
 with ThreadPoolExecutor(max_workers=workers) as pool:
  futures=[pool.submit(one,n,p)for n,p in jobs]
  for f in as_completed(futures):print(json.dumps(f.result()),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--workers',type=int,default=6);a.add_argument('--reconcile',action='store_true');v=a.parse_args();main(min(8,max(1,v.workers)),v.reconcile)
