"""Use unchanged, tested R2 lossless byte codec; R3 output roots are explicit."""
from r3lib import *
import raw_archive,argparse,subprocess,urllib.request,urllib.parse,urllib.error,gzip,shutil
MAN=HERE/'evidence/raw_archive_manifest.json'
def compress():
 m=json.loads(MAN.read_text()) if MAN.exists() else dict(codec='QS30RAW1',records=[],R2_missing_raws_permanently=2)
 known={x['source'] for x in m['records']}
 for p in sorted((HERE/'experiments').glob('*/circuit.raw')):
  if p.parent.name.startswith('pending_'):continue
  rel=str(p.relative_to(HERE)).replace('\\','/')
  if rel in known:continue
  try:
   raw_archive.layout(p)
   rec=raw_archive.archive(p,HERE/'.local/raw_archives',HERE,cap=90*1024*1024)
   rec['verification']=raw_archive.verify(rec,HERE)
  except ValueError as ex:
   if 'Only normal-order double raw' not in str(ex):raise
   # Small smoke-probe mixed raw: exact-byte gzip instead of forcing double layout.
   digest=sha(p);sink=raw_archive.Split(HERE/'.local/raw_archives',digest,90*1024*1024)
   with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz,p.open('rb') as src:shutil.copyfileobj(src,gz)
   sink.close()
   rec=dict(source=rel,original_bytes=p.stat().st_size,original_sha256=digest,codec='gzip-original-bytes',parts=[dict(path=str(q.relative_to(HERE)).replace('\\','/'),bytes=q.stat().st_size,sha256=sha(q)) for q in sink.files])
   h=hashlib.sha256();n=0
   with raw_archive.Parts(sink.files) as src,gzip.GzipFile(fileobj=src) as gz:
    for b in iter(lambda:gz.read(1048576),b''):h.update(b);n+=len(b)
   assert h.hexdigest()==digest and n==p.stat().st_size
   rec['verification']=dict(status='EXACT_BYTE_RECONSTRUCTION',original_sha256=digest,bytes=n,electrical_status='NOT_INFERRED')
  m['records'].append(rec);dump(MAN,m);print('ARCHIVED',rel,p.stat().st_size,len(rec['parts']),flush=True)
 return m
def token():
 p=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,timeout=30)
 fields=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
 if p.returncode or not fields.get('password'):raise RuntimeError('Existing GitHub credentials unavailable')
 return fields['password']
def request(url,tok,data=None,method=None,headers=None,timeout=120):
 h={'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','User-Agent':'QS30-R3-Evidence','X-GitHub-Api-Version':'2022-11-28'};h.update(headers or {})
 with urllib.request.urlopen(urllib.request.Request(url,data=data,method=method,headers=h),timeout=timeout) as r:return json.load(r)
def upload():
 statep=HERE/'evidence/github_artifacts.json';tok=token();repo='langxie29-cpu/QS30-driver'
 if statep.exists():state=json.loads(statep.read_text())
 else:
  body=dict(tag_name='qs30-power-loop-r3-evidence-20261118',target_commitish='nxt/qs30-power-loop-engineering-r3',name='[RESEARCH HOLD] QS30 R3 native raw evidence',draft=True,prerelease=True,body='Development simulation evidence only. All manufacturing/H01-H10/24V07-10 HOLD retained. Parameter frontend is NOT native TPS26601 qualification. Includes failed and partial raw outputs. QS30RAW1 archives reconstruct exact original bytes. No model libraries, credentials, procurement or hardware authorization. See R3 manifest and reports. R2 two deleted raw files remain permanently missing.')
  r=request(f'https://api.github.com/repos/{repo}/releases',tok,json.dumps(body).encode(),'POST',{'Content-Type':'application/json'})
  state=dict(id=r['id'],html_url=r['html_url'],draft=r['draft'],upload_url=r['upload_url'].split('{')[0],tag_name=r['tag_name'],assets={});dump(statep,state)
 manifest=json.loads(MAN.read_text())
 # Recover prior successful uploads if HTTP failed after the server accepted data; no deletion.
 existing=request(f'https://api.github.com/repos/{repo}/releases/{state["id"]}/assets?per_page=100',tok)
 remote={x['name']:x for x in existing}
 for rec in manifest['records']:
  for part in rec['parts']:
   p=HERE/part['path'];name=p.name
   if name in state['assets']:continue
   assert p.stat().st_size==part['bytes'] and sha(p)==part['sha256']
   if name in remote:r=remote[name]
   else:
    with p.open('rb') as f:r=request(state['upload_url']+'?'+urllib.parse.urlencode({'name':name}),tok,f,'POST',{'Content-Type':'application/octet-stream','Content-Length':str(part['bytes'])},300)
   assert r['size']==part['bytes'] and r.get('digest')=='sha256:'+part['sha256']
   state['assets'][name]=dict(id=r['id'],bytes=r['size'],local_sha256=part['sha256'],remote_digest=r['digest'],api_url=r['url'],browser_download_url=r['browser_download_url'],state=r['state'])
   dump(statep,state);print('UPLOADED_SHA_VERIFIED',name,r['size'],flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['compress','upload']);v=a.parse_args();compress() if v.action=='compress' else upload()
