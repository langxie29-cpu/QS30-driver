"""Download selected draft raw assets with existing GitHub credentials, no logging secrets."""
from pathlib import Path
import argparse,json,urllib.request,urllib.error,urllib.parse
import artifact_store as api
import lab
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def stream_asset(url,tok):
 if not url.startswith('https://api.github.com/repos/langxie29-cpu/QS30-driver/releases/assets/'):raise ValueError('Unexpected asset API origin')
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+tok,'Accept':'application/octet-stream','User-Agent':'QS30-R2-Evidence'})
 try:return urllib.request.build_opener(NoRedirect()).open(req,timeout=60)
 except urllib.error.HTTPError as e:
  if e.code not in (301,302,303,307,308):raise
  location=e.headers['Location'];u=urllib.parse.urlparse(location)
  if u.scheme!='https' or not (u.hostname or '').endswith('.githubusercontent.com'):raise ValueError('Unexpected asset redirect origin')
  # No Authorization header is forwarded to the signed content URL.
  return urllib.request.urlopen(urllib.request.Request(location,headers={'User-Agent':'QS30-R2-Evidence'}),timeout=120)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--case',help='Substring of source case path; omit for all');a.add_argument('--list',action='store_true');v=a.parse_args()
 manifest=json.loads((lab.HERE/'evidence/raw_archive_manifest.json').read_text(encoding='utf8'))
 rows=[r for r in manifest['records']if not v.case or v.case in r['source']]
 if not rows:raise ValueError('No matching raw case')
 if v.list:
  for r in rows:print(r['source'],r['original_bytes'])
 else:
  state=json.loads((lab.HERE/'evidence/github_artifacts.json').read_text(encoding='utf8'));tok=api.token()
  for rec in rows:
   for part in rec['parts']:
    dst=(lab.HERE/part['path']).resolve()
    if not dst.is_relative_to(lab.HERE):raise ValueError('Unsafe cache path')
    if dst.exists():
     if lab.sha(dst)!=part['sha256']:raise ValueError('Existing cache part differs; preserve and inspect it')
     continue
    asset=state['assets'].get(dst.name)
    if not asset:raise ValueError('Manifest part is not yet a verified uploaded asset')
    dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_suffix(dst.suffix+'.download_incomplete')
    with stream_asset(asset['api_url'],tok) as response,tmp.open('xb') as f:
     while b:=response.read(1024*1024):f.write(b)
    if tmp.stat().st_size!=part['bytes'] or lab.sha(tmp)!=part['sha256']:raise ValueError('Downloaded part failed integrity; incomplete file preserved')
    tmp.rename(dst);print(dst.name,'SHA256 verified',flush=True)
