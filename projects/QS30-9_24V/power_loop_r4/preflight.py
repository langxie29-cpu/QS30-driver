"""Read-only frozen input verification; writes R4 evidence only."""
from r4lib import *
import subprocess,os
def main():
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASELINE
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=R3.parents[2],text=True).strip()
 previous=json.loads((R3/'evidence/historical_before.json').read_text(encoding='utf8'))
 records=list(previous);seen={r['path']for r in records}
 for base,dirs,files in os.walk(R3):
  dirs[:]=[d for d in dirs if d not in ['.local','appdata','localappdata','__pycache__']]
  for name in files:
   p=Path(base)/name
   if str(p)not in seen:records.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 mismatches=[]
 for r in records:
  p=Path(r['path'])
  if not p.exists()or p.stat().st_size!=r['bytes']or sha(p)!=r['sha256']:mismatches.append(r['path'])
 dump(HERE/'evidence/preflight/historical_before.json',records)
 refs=subprocess.check_output(['git','ls-remote','--heads','origin','nxt/qs30-power-loop-engineering-r1','nxt/qs30-power-loop-engineering-r2','nxt/qs30-power-loop-engineering-r3'],cwd=ROOT,text=True)
 dump(HERE/'evidence/preflight/baseline.json',dict(utc=utc(),HEAD=BASELINE,branch='nxt/qs30-power-loop-engineering-r4',old_R3_clean=True,verified_files=len(records),verified_bytes=sum(r['bytes']for r in records),mismatches=mismatches,remote_refs=refs,Kicad=subprocess.check_output([str(KC),'version'],text=True).strip(),Kicad_exe_sha256=sha(KC),LT_exe_sha256=sha(LT),R4_limits=dict(rounds=2,Flash=6,child_Codex=0,native_LT=12),scope='Historical bytes and available tools only; not electrical qualification'))
 assert not mismatches
 print(json.dumps(dict(verified_files=len(records),mismatches=len(mismatches),KiCad='10.0.8')))
if __name__=='__main__':main()
