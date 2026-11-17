"""Compare historical input bytes with the first Flash audit's frozen hashes."""
from pathlib import Path
import json,hashlib,re
from local_probe import HERE,OLD
if __name__=='__main__':
 registry=HERE/'evidence/worker_run_20261117T051440Z/round_01/baseline_audit/provenance_scan_historical.json'
 rows=json.loads(registry.read_text(encoding='utf8'))['files']
 base=OLD.parents[1];changes=[];unhashed=[];count=0;total=0;raws=0
 for r in rows:
  rel=Path(r['path']);p=(base/rel).resolve()
  if rel.is_absolute() or '..' in rel.parts or not p.is_relative_to(OLD.resolve()):raise ValueError('Untrusted historical path')
  expected=r.get('sha256','')
  if not re.fullmatch('[0-9a-f]{64}',expected):unhashed.append(r['path']);continue
  if not p.is_file():changes.append(dict(path=r['path'],reason='MISSING'));continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  count+=1;total+=p.stat().st_size;raws+=p.suffix=='.raw'
  if h.hexdigest()!=expected:changes.append(dict(path=r['path'],reason='CHANGED',expected=expected,observed=h.hexdigest()))
 result=dict(scope='Historical input byte preservation only, not electrical/model qualification',
  registry_sha256=hashlib.sha256(registry.read_bytes()).hexdigest(),checked_files=count,checked_bytes=total,checked_native_raw_files=raws,
  changes=changes,not_hashed_by_original_auditor=unhashed,status='PASS' if not changes and not unhashed else 'INCONCLUSIVE')
 (HERE/'evidence/preflight/historical_inputs_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(result,indent=2))
