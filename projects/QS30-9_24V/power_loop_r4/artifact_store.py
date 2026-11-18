"""Draft GitHub evidence assets; no release publication, no credential logging."""
from pathlib import Path
import argparse,json,subprocess,time,urllib.request,urllib.parse,urllib.error
import r4lib as lab
REPO='langxie29-cpu/QS30-driver';STATE=lab.HERE/'evidence/github_artifacts.json'
def token():
 p=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,timeout=30)
 fields=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
 if p.returncode or not fields.get('password'):raise RuntimeError('Existing GitHub credential unavailable')
 return fields['password']
def request(url,tok,data=None,method=None,headers=None,timeout=120):
 h={'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','User-Agent':'QS30-R4-Evidence','X-GitHub-Api-Version':'2022-11-28'};h.update(headers or {})
 req=urllib.request.Request(url,data=data,method=method,headers=h)
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
def create(tok):
 if STATE.exists():return json.loads(STATE.read_text(encoding='utf8'))
 payload=dict(tag_name='qs30-power-loop-r4-evidence-20261118',target_commitish='nxt/qs30-power-loop-engineering-r2',name='[RESEARCH HOLD] QS30-9 R4 native raw evidence',draft=True,prerelease=True,body='Software simulation evidence only. All manufacturing/safety HOLD remain. Original 96a1afef evidence is immutable. These assets are reversible lossless archives of native LTspice raw bytes, including failures and partial tails; verify using the manifest and raw_archive.py on the R2 development branch. Two NEW defective Round1 worker raws were deleted by that worker before interruption and cannot be included; the audit gap is explicitly recorded. This draft is not a product release, hardware qualification, procurement or manufacturing authorization.')
 r=request(f'https://api.github.com/repos/{REPO}/releases',tok,json.dumps(payload).encode(), 'POST',{'Content-Type':'application/json'},60)
 state=dict(id=r['id'],html_url=r['html_url'],upload_url=r['upload_url'].split('{')[0],draft=r['draft'],tag_name=r['tag_name'],assets={},scope='Draft archival only; no release publication authorized or performed')
 lab.dump(STATE,state);return state
def upload(tok,state):
 manifest=json.loads((lab.HERE/'evidence/raw_archive_manifest.json').read_text(encoding='utf8'))
 for rec in manifest['records']:
  for part in rec['parts']:
   p=lab.HERE/part['path'];name=p.name
   if name in state['assets']:continue
   if lab.sha(p)!=part['sha256']:raise ValueError('Part changed before upload')
   url=state['upload_url']+'?'+urllib.parse.urlencode({'name':name})
   with p.open('rb') as f:r=request(url,tok,f,'POST',{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)},600)
   if r['size']!=part['bytes']:raise ValueError('Uploaded byte count mismatch')
   digest=r.get('digest')
   if digest and digest!='sha256:'+part['sha256']:raise ValueError('Remote asset digest mismatch')
   state['assets'][name]=dict(id=r['id'],bytes=r['size'],local_sha256=part['sha256'],remote_digest=digest,browser_download_url=r['browser_download_url'],api_url=r['url'],state=r['state'])
   lab.dump(STATE,state);print(name,r['size'],r['state'],'digest_verified' if digest else 'digest_unavailable',flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--create',action='store_true');a.add_argument('--upload',action='store_true');v=a.parse_args()
 tok=token();s=create(tok)
 if v.upload:upload(tok,s)
 else:print(json.dumps({k:s[k] for k in ['id','html_url','draft','tag_name']},indent=2))
