"""Freeze new evidence, compress exact raw bytes into GitHub-sized content blobs.

Does not delete or change raw originals. Vendor binaries/library bundles are kept
local and only referenced by hash. No credentials/private Harness files included.
"""
from pathlib import Path
import gzip,hashlib,json,shutil,sys,os
HERE=Path(__file__).resolve().parent
E=HERE/'evidence'
CHUNK=45*1024*1024
SKIP_EXT={'.exe','.dll','.msi','.zip','.lib','.sub','.asy','.asc','.dio','.mos','.bjt','.chm','.models','.pdf'}
SKIP_DIR={'appdata','localappdata','profile','sim_profile','lib','examples','.local','vendor_bytes','vendor_original','__pycache__'}

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def blob(p,sha):
 out=E/'raw_blobs';out.mkdir(exist_ok=True)
 base=out/(sha+'.gz')
 manifest=out/(sha+'.json')
 if manifest.exists():return json.loads(manifest.read_text())
 temp=HERE/'.local'/('archive-'+sha+'.gz')
 with p.open('rb') as src,temp.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=4,mtime=0) as z:
  shutil.copyfileobj(src,z,1024*1024)
 parts=[]
 with temp.open('rb') as f:
  i=1
  while b:=f.read(CHUNK):
   dest=out/(sha+'.gz.part%03d'%i);dest.write_bytes(b)
   parts.append(dict(path=str(dest.relative_to(E)).replace('\\','/'),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));i+=1
 info=dict(original_sha256=sha,original_bytes=p.stat().st_size,format='Concatenate ordered parts then gzip-decompress; original bytes must match SHA256',parts=parts)
 manifest.write_text(json.dumps(info,indent=2)+'\n',encoding='utf8',newline='\n')
 temp.unlink() # Only own, verified temporary archive; raw source is untouched.
 return info

def freeze(run):
 source=HERE/'runs'/run
 target=E/('worker_run_'+run)
 target.mkdir(exist_ok=False)
 records=[]
 for p in sorted(source.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(source)
  if any(x.lower() in SKIP_DIR for x in rel.parts):continue
  sha=digest(p);r=dict(path=str(rel).replace('\\','/'),sha256=sha,bytes=p.stat().st_size)
  if p.suffix.lower() in SKIP_EXT:
   r['storage']='LOCAL_VENDOR_ARTIFACT_ONLY';records.append(r);continue
  dest=target/rel
  if p.suffix.lower()=='.raw' or p.stat().st_size>2*1024*1024:
   r['storage']='EXACT_GZIP_BLOB';r['archive']=blob(p,sha)
   dest=dest.with_name(dest.name+'.archive.json');dest.parent.mkdir(parents=True,exist_ok=True)
   dest.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
  else:
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);r['storage']='EXACT_COPY'
  records.append(r)
 # Archive primary raw originals, excluding the archive itself and frozen worker outputs.
 for p in sorted(E.rglob('*')):
  if not p.is_file() or any(x in p.parts for x in ('raw_blobs',target.name)):continue
  if p.suffix.lower()=='.raw' or (p.suffix.lower()=='.txt' and p.stat().st_size>2*1024*1024):
   sha=digest(p);records.append(dict(path=str(p.relative_to(HERE)).replace('\\','/'),sha256=sha,bytes=p.stat().st_size,storage='EXACT_GZIP_BLOB',archive=blob(p,sha)))
 (target/'archive_manifest.json').write_text(json.dumps(dict(run=run,records=records,policy='Original sources untouched; library/software binaries omitted; raw exact bytes compressed, never synthesized'),indent=2)+'\n',encoding='utf8',newline='\n')
 print('Frozen records',len(records),'at',target)

if __name__=='__main__':freeze(sys.argv[1])
