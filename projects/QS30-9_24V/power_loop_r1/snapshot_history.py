"""Copy selected real uncommitted historical evidence, never change the old worktree."""
from pathlib import Path
import hashlib,json,shutil
from local_probe import HERE,OLD
if __name__=='__main__':
 d=HERE/'evidence/historical_snapshot';d.mkdir(parents=True,exist_ok=False)
 chosen=[]
 for s in ('06c','06d','06e','06f'):
  chosen += ['docs/SPRINT'+s.upper()+'_REPORT.md','config/sprint'+s+'.json']
  for p in (OLD/'docs'/('sprint'+s)).glob('*.json'):
   if p.stat().st_size<2*1024*1024:chosen.append(str(p.relative_to(OLD)))
 records=[]
 for rel in sorted(set(chosen)):
  src=OLD/rel
  if not src.is_file():records.append(dict(source=rel,status='ABSENT'));continue
  dest=d/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
  records.append(dict(source=str(src),snapshot=str(dest.relative_to(d)).replace('\\','/'),bytes=src.stat().st_size,
    source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),copy_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
    status='UNCOMMITTED_SOURCE_SNAPSHOT_NOT_AUTOMATICALLY_QUALIFIED'))
 (d/'manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf8',newline='\n')
 print('Historical selected snapshots:',len(records))
