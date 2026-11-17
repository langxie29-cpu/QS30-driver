"""Verify all delivered exact-copy records and gzip parts against SHA256."""
from pathlib import Path
import json,hashlib,gzip,re,shutil
HERE=Path(__file__).resolve().parent
E=HERE/'evidence'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
if __name__=='__main__':
 folder=E/'worker_run_20261117T051440Z';manifest=json.loads((folder/'archive_manifest.json').read_text())
 checks=[];seen=set()
 for r in manifest['records']:
  if r['storage']=='EXACT_COPY':
   p=folder/r['path'];checks.append(dict(path=r['path'],kind='copy',passed=p.is_file() and digest(p)==r['sha256']))
  if r['storage']!='EXACT_GZIP_BLOB' or r['sha256'] in seen:continue
  sha=r['sha256'];assert re.fullmatch('[0-9a-f]{64}',sha);seen.add(sha)
  temp=HERE/'.local'/('verify-'+sha+'.gz')
  with temp.open('wb') as out:
   for part in r['archive']['parts']:
    p=(E/part['path']).resolve();assert p.is_relative_to((E/'raw_blobs').resolve())
    assert p.stat().st_size==part['bytes'] and digest(p)==part['sha256']
    with p.open('rb') as f:shutil.copyfileobj(f,out,1024*1024)
  h=hashlib.sha256();size=0
  with gzip.open(temp,'rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b);size+=len(b)
  checks.append(dict(path=sha,kind='reconstructed_raw',bytes=size,passed=h.hexdigest()==sha and size==r['bytes']))
  temp.unlink()
 result=dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',scope='Artifact byte integrity ONLY; not electrical PASS',
  exact_copy_checks=sum(c['kind']=='copy' for c in checks),unique_reconstructed_raws=len(seen),checks=checks)
 (E/'archive_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
 if result['status']!='PASS':raise SystemExit(1)
