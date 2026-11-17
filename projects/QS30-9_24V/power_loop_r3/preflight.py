from r3lib import *
import subprocess,os
E=HERE/'evidence'; E.mkdir(exist_ok=True)
if (E/'historical_before.json').exists():raise RuntimeError('Original preflight already exists; use checks.py --historical, never replace before snapshot')
required=['ENGINEERING_REPORT.md','REPRODUCE.md','MODEL_MATRIX_R2.md','evidence/independent/startup_strategy.json','evidence/independent/qualification_matrix.json','evidence/independent/review.json','evidence/execution_ledger.json','evidence/raw_archive_manifest.json','evidence/delivery_receipt.json']
read=[]
for n in required:
 p=R2/n; txt=p.read_text(encoding='utf8');read.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,read=True))
for n in ['safety_r1/architecture/SAFETY_ARCHITECTURE.md','safety_r1/governance/holds.json','docs/TASKS.csv','netlist/candidate_power_pins.csv']:
 p=ROOT/'projects/QS30-9_24V'/n; p.read_text(encoding='utf8');read.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,read=True))
dump(E/'required_reads.json',read)
# Freeze bytes of tracked R1/R2 history plus all extant native raw, including partial runs.
records=[]
for stage in ['r1','r2']:
 base=Path(f'D:/PROJECTS/dsharness/QS30-power-loop-{stage}')
 tracked=subprocess.check_output(['git','ls-files',f'projects/QS30-9_24V/power_loop_{stage}','projects/QS30-9_24V/safety_r1'],cwd=base,text=True).splitlines()
 paths={base/n for n in tracked}
 paths.update((base/f'projects/QS30-9_24V/power_loop_{stage}').rglob('*.raw'))
 for p in sorted(paths):
  if '.local' in p.parts:continue
  records.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
dump(E/'historical_before.json',records)
sid=subprocess.check_output(['whoami','/user','/fo','csv','/nh'],text=True).strip().split(',')[-1].strip('"')
acl=[]
for base in [Path('D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1'),R2,ROOT/'projects/QS30-9_24V/power_loop_r1',ROOT/'projects/QS30-9_24V/power_loop_r2']:
 # Targeted evidence ACLs only; do not touch .git, current unrelated work or credentials.
 cmd=['pwsh','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE/'protect.ps1'),'-EvidencePath',str(base)]
 r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace')
 acl.append(dict(path=str(base),argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
dump(E/'preservation_control.json',dict(utc=utc(),acl=acl,worker_architecture='Remote HTTPS completion with NO tools, NO local worker process, NO execution of generated code. Controller writes response text to drafts. No worker filesystem authority exists.',limitations='Administrator can change ACLs; this is not an administrator-proof immutable store or a separate local worker SID sandbox.',historical_missing_raws_R2=2))
print(json.dumps(dict(historical_files=len(records),acl_rc=[x['rc'] for x in acl],reads=len(read))))
