"""Lossless native-raw archive. Byte/bit transforms only; never rounds waveforms.

Container: magic, little-endian <IIQQI> (header bytes, record bytes, physical
records, trailing bytes, block records), original header, XOR/byte-shuffled
record blocks, original trailing bytes. Whole container gzip, mtime=0.
Every reconstructed original byte is checked by SHA256, including timeout tails.
"""
from pathlib import Path
import argparse,gzip,hashlib,io,json,os,re,struct
import numpy as np
import lab
MAGIC=b'QS30RAW1\n';FMT='<IIQQI';BLOCK=32768;PART=256*1024*1024
def layout(p):
 with p.open('rb') as f:b=f.read(131072)
 enc='utf-16-le' if b.startswith(b'T\0') else 'utf8'
 for mark in ['Binary:\r\n','Binary:\n']:
  marker=mark.encode(enc);k=b.find(marker)
  if k>=0:break
 if k<0:raise ValueError('Not a supported native binary raw')
 h=b[:k].decode(enc);flags=re.search(r'Flags:\s*([^\r\n]+)',h)[1].lower().split()
 if 'double' not in flags or any(x in flags for x in ['complex','fastaccess']):raise ValueError('Only normal-order double raw is archived by this codec')
 prefix=b[:k+len(marker)];stride=8*int(re.search(r'No\. Variables:\s*(\d+)',h)[1]);rows,tail=divmod(p.stat().st_size-len(prefix),stride)
 return prefix,stride,rows,tail,int(re.search(r'No\. Points:\s*(\d+)',h)[1])
class Split:
 def __init__(self,d,key,cap):self.d=d;self.key=key;self.cap=cap;self.f=None;self.n=0;self.files=[]
 def write(self,b):
  total=len(b)
  while b:
   if self.f is None:
    p=self.d/f'{self.key}.qraw.gz.part{len(self.files):03d}';self.f=p.open('xb');self.files.append(p);self.n=0
   take=min(len(b),self.cap-self.n);self.f.write(b[:take]);self.n+=take;b=b[take:]
   if self.n==self.cap:self.f.close();self.f=None
  return total
 def flush(self):
  if self.f:self.f.flush()
 def close(self):
  if self.f:self.f.close();self.f=None
class Parts(io.RawIOBase):
 def __init__(self,parts):self.parts=iter(parts);self.f=None
 def readable(self):return True
 def readinto(self,b):
  while True:
   if self.f is None:
    try:self.f=next(self.parts).open('rb')
    except StopIteration:return 0
   n=self.f.readinto(b)
   if n:return n
   self.f.close();self.f=None
 def close(self):
  if self.f:self.f.close()
  super().close()
def restored_chunks(parts):
 with Parts(parts) as raw,io.BufferedReader(raw) as buffered,gzip.GzipFile(fileobj=buffered,mode='rb') as gz:
  if gz.read(len(MAGIC))!=MAGIC:raise ValueError('Archive magic mismatch')
  nh,stride,rows,tail,block=struct.unpack(FMT,gz.read(struct.calcsize(FMT)))
  if stride%8 or stride<8 or block>1048576 or nh>1048576:raise ValueError('Invalid container bounds')
  head=gz.read(nh)
  if len(head)!=nh:raise ValueError('Truncated original header')
  yield head
  left=rows
  while left:
   nr=min(block,left);b=gz.read(nr*stride)
   if len(b)!=nr*stride:raise ValueError('Truncated record block')
   arr=np.frombuffer(b,dtype='u1').reshape(stride,nr).T.copy()
   words=arr.view('<u8').reshape(nr,stride//8)
   np.bitwise_xor.accumulate(words,axis=0,out=words)
   yield words.tobytes();left-=nr
  b=gz.read(tail)
  if len(b)!=tail:raise ValueError('Truncated original tail')
  yield b
  if gz.read(1):raise ValueError('Unexpected archive payload')
def verify(record,root,restore=None):
 root=Path(root).resolve();parts=[(root/p['path']).resolve() for p in record['parts']]
 if any(not p.is_relative_to(root) for p in parts):raise ValueError('Archive path outside root')
 for p,m in zip(parts,record['parts']):
  if p.stat().st_size!=m['bytes'] or lab.sha(p)!=m['sha256']:raise ValueError('Archive part corrupted: '+str(p))
 h=hashlib.sha256();n=0;out=Path(restore).open('xb') if restore else None
 try:
  for b in restored_chunks(parts):
   h.update(b);n+=len(b)
   if out:out.write(b)
 finally:
  if out:out.close()
 if n!=record['original_bytes'] or h.hexdigest()!=record['original_sha256']:raise ValueError('Original byte reconstruction mismatch')
 return dict(original_sha256=h.hexdigest(),bytes=n,status='EXACT_BYTE_RECONSTRUCTION',electrical_status='NOT_INFERRED')
def archive(p,d,root,cap=PART):
 p=Path(p);d=Path(d);d.mkdir(parents=True,exist_ok=True);prefix,stride,rows,tail,declared=layout(p);digest=lab.sha(p)
 sink=Split(d,digest,cap)
 try:
  with gzip.GzipFile(filename='',mode='wb',compresslevel=3,fileobj=sink,mtime=0) as gz,p.open('rb') as src:
   gz.write(MAGIC+struct.pack(FMT,len(prefix),stride,rows,tail,BLOCK));gz.write(prefix);src.seek(len(prefix));left=rows
   while left:
    nr=min(BLOCK,left);b=src.read(nr*stride)
    if len(b)!=nr*stride:raise ValueError('Source changed during archival')
    w=np.frombuffer(b,dtype='<u8').reshape(nr,stride//8);dx=w.copy();dx[1:]^=w[:-1]
    gz.write(dx.view('u1').reshape(nr,stride).T.copy().tobytes());left-=nr
   gz.write(src.read(tail))
 finally:sink.close()
 rec=dict(source=str(p.relative_to(root)).replace('\\','/'),original_bytes=p.stat().st_size,original_sha256=digest,codec='QS30RAW1 XOR per record + byte-plane shuffle + gzip (lossless)',declared_points=declared,physical_complete_records=rows,original_trailing_bytes=tail,header_bytes=len(prefix),record_bytes=stride,parts=[dict(path=str(q.relative_to(root)).replace('\\','/'),bytes=q.stat().st_size,sha256=lab.sha(q)) for q in sink.files])
 rec['verification']=verify(rec,root)
 if lab.sha(p)!=digest:raise ValueError('Source changed while verifying archive')
 return rec
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--archive-all',action='store_true');a.add_argument('--verify-manifest');a.add_argument('--restore-root');v=a.parse_args()
 if v.archive_all:
  target=lab.HERE/'.local/raw_archives';target.mkdir(parents=True,exist_ok=True);index=lab.HERE/'evidence/raw_archive_manifest.json'
  old=json.loads(index.read_text(encoding='utf8')) if index.exists() else dict(records=[])
  records=old['records'];known={x['source'] for x in records}
  paths=[]
  for base,dirs,files in os.walk(lab.HERE):
   dirs[:]=[x for x in dirs if x not in ['.local','appdata','localappdata','sim_profile','__pycache__']]
   paths.extend(Path(base)/f for f in files if f=='circuit.raw')
  for p in sorted(paths):
   rel=str(p.relative_to(lab.HERE)).replace('\\','/')
   if rel in known:continue
   if not (p.parent/'command.json').exists():
    print('DEFERRED_RUNNING',rel,flush=True);continue
   rec=archive(p,target,lab.HERE);records.append(rec);lab.dump(index,dict(records=records,scope='Original raw byte reconstruction only, not electrical acceptance',missing_deleted_raws=2));print(rel,rec['original_bytes'],sum(x['bytes'] for x in rec['parts']),flush=True)
 elif v.verify_manifest:
  m=json.loads(Path(v.verify_manifest).read_text(encoding='utf8'))
  for rec in m['records']:
   dest=None
   if v.restore_root:
    rr=Path(v.restore_root).resolve();dest=(rr/rec['source']).resolve()
    if not dest.is_relative_to(rr):raise ValueError('Restore path outside destination')
    dest.parent.mkdir(parents=True,exist_ok=True)
   print(rec['source'],verify(rec,lab.HERE,dest))
