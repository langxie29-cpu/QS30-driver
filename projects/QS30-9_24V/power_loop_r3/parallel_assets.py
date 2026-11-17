"""Upload only NEW batch2 asset names. Never races batch1 state writes."""
from archive import *
from concurrent.futures import ThreadPoolExecutor,as_completed
import time
def main():
 first=json.loads((HERE/'evidence/upload_batch1_snapshot.json').read_text());reserved={p['path'].split('/')[-1] for r in first['records'] for p in r['parts']}
 m=json.loads(MAN.read_text());state=json.loads((HERE/'evidence/github_artifacts.json').read_text());tok=token();jobs=[p for r in m['records'] for p in r['parts'] if p['path'].split('/')[-1] not in reserved]
 remote=[];page=1
 while True:
  r=request(f'https://api.github.com/repos/langxie29-cpu/QS30-driver/releases/{state["id"]}/assets?per_page=100&page={page}',tok);remote+=r
  if len(r)<100:break
  page+=1
 existing={r['name']:r for r in remote}
 D=HERE/'evidence/upload_batch2_receipts';D.mkdir(exist_ok=True)
 def one(part):
  p=HERE/part['path'];name=p.name;receipt=D/(name+'.json')
  if receipt.exists():return name,'ALREADY_VERIFIED'
  assert sha(p)==part['sha256']
  started=time.monotonic()
  if name in existing:r=existing[name]
  else:
   with p.open('rb') as f:r=request(state['upload_url']+'?'+urllib.parse.urlencode({'name':name}),tok,f,'POST',{'Content-Type':'application/octet-stream','Content-Length':str(part['bytes'])},300)
  assert r['size']==part['bytes'] and r.get('digest')=='sha256:'+part['sha256']
  dump(receipt,dict(id=r['id'],name=name,bytes=r['size'],local_sha256=part['sha256'],remote_digest=r['digest'],api_url=r['url'],browser_download_url=r['browser_download_url'],state=r['state'],elapsed_s=time.monotonic()-started))
  return name,'SHA_VERIFIED'
 with ThreadPoolExecutor(max_workers=3) as pool:
  for f in as_completed([pool.submit(one,p) for p in jobs]):print(*f.result(),flush=True)
if __name__=='__main__':main()
