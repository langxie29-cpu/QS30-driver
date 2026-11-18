"""Use unchanged, tested R2 lossless byte codec; R4 output roots are explicit."""
from r4lib import *
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

if __name__=="__main__":compress()
