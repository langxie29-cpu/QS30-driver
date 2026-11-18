"""Restore exact raw bytes from authenticated draft assets, no SPICE/API model calls."""
from archive import *
from artifact_store import token
import argparse,io
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  n=super().redirect_request(req,fp,code,msg,headers,newurl)
  if n is not None and urllib.parse.urlsplit(newurl).hostname!='api.github.com':
   for h in list(n.headers):
    if h.lower()=='authorization':n.remove_header(h)
  return n
def restore(rec,base,dest):
 target=(dest/rec['source']).resolve();assert target.is_relative_to(dest.resolve())
 target.parent.mkdir(parents=True,exist_ok=True)
 if rec.get('codec')=='gzip-original-bytes':
  with raw_archive.Parts([base/p['path'] for p in rec['parts']]) as r,gzip.GzipFile(fileobj=r) as gz,target.open('xb') as out:shutil.copyfileobj(gz,out)
  assert target.stat().st_size==rec['original_bytes'] and sha(target)==rec['original_sha256']
  return dict(status='EXACT_BYTE_RECONSTRUCTION',bytes=target.stat().st_size,original_sha256=sha(target))
 return raw_archive.verify(rec,base,target)
def main():
 a=argparse.ArgumentParser();a.add_argument('--list',action='store_true');a.add_argument('--case');a.add_argument('--download-root',type=Path,default=HERE);a.add_argument('--restore-root',type=Path);v=a.parse_args()
 m=json.loads(MAN.read_text());records=[r for r in m['records'] if not v.case or v.case in r['source']]
 if v.list:
  print(json.dumps([dict(source=r['source'],bytes=r['original_bytes'],sha256=r['original_sha256']) for r in records],indent=2));return
 state=json.loads((HERE/'evidence/github_artifacts.json').read_text());tok=token();opener=urllib.request.build_opener(SafeRedirect())
 for rec in records:
  for part in rec['parts']:
   p=(v.download_root/part['path']).resolve();assert p.is_relative_to(v.download_root.resolve())
   p.parent.mkdir(parents=True,exist_ok=True)
   if not p.exists():
    asset=state['assets'][p.name];req=urllib.request.Request(asset['api_url'],headers={'Authorization':'Bearer '+tok,'Accept':'application/octet-stream','User-Agent':'QS30-R4-restore'})
    with opener.open(req,timeout=180) as r,p.open('xb') as out:shutil.copyfileobj(r,out)
   assert p.stat().st_size==part['bytes'] and sha(p)==part['sha256']
  if v.restore_root:print(rec['source'],restore(rec,v.download_root,v.restore_root),flush=True)
if __name__=='__main__':main()
