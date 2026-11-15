"""Sprint02 append-only evidence summary; no historical files are written."""
from pathlib import Path
import json,hashlib,gzip,subprocess,math,re,sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'sim/sprint02'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'docs9/electrical_sprint02';out.mkdir(exist_ok=False)
 results=[]
 for run in ['controller_v1','power_v1','slope_candidate_v1']:
  p=BASE/run/'results.json'
  if not p.exists():raise FileNotFoundError(p)
  for row in json.loads(p.read_text())['results']:
   f=BASE/run/row['case']['id'];log=(f/'ngspice.log').read_text(errors='replace')
   valid=row['execution']=='PASS'
   if valid:
    assert row['rc']==0 and not any(s in log.lower() for s in ['error:','aborted','failed!','timestep too small'])
    endpoint=re.search(r'end_time\s*=\s*([\deE.+-]+)',log);assert endpoint and abs(float(endpoint[1])-row['requested_stop_s'])<1e-6
   results.append({'run':run,'case':row['case'],'execution':row['execution'],'engineering':row.get('engineering','BLOCKED'),'native':row.get('native_measurements',{}),'metrics':row.get('metrics',{}),'cause':'UNSUPPORTED' if row['rc']=='TIMEOUT' else ('PERFORMANCE_FAIL' if row.get('engineering')=='FAIL' else None)})
 baseline=json.loads((BASE/'baseline.json').read_text(encoding='utf-8'))
 checks={'inherited_inputs_unchanged':all(sha(ROOT/p)==h for p,h in baseline['input_sha256'].items())}
 before=json.loads((ROOT/'kicad/logs/sprint02_before/results.json').read_text(encoding='utf-8'))
 after=json.loads((ROOT/'kicad/logs/sprint02_after/results.json').read_text(encoding='utf-8'))
 def stats(d):return {b:{k:d['boards'][b][k] for k in ['erc','drc','reconciliation','pcb_nc_inventory_matches']} for b in d['boards']}
 checks['native_stats_identical']=stats(before)==stats(after)
 checks['native_inputs_identical']=before['input_sha256']==after['input_sha256']
 audits=[json.loads((ROOT/'kicad/logs'/r/'electrical_audit.json').read_text(encoding='utf-8')) for r in ['sprint02_before','sprint02_after']]
 checks['12_mapping_audits']=all(len(a['checks'])==12 and all(c['status']=='PASS' for c in a['checks']) for a in audits)
 # Raw waves are kept locally; compressed exact copies make evidence portable.
 for p in BASE.rglob('waves.txt'):
  gz=Path(str(p)+'.gz')
  if not gz.exists():
   with gzip.open(gz,'wb') as f:f.write(p.read_bytes())
 checks['wave_archives_exact']=all(gzip.decompress(p.read_bytes())==Path(str(p)[:-3]).read_bytes() for p in BASE.rglob('waves.txt.gz'))
 matrix=[{'id':'SIM-01','status':'FAIL','reason':'Actual netlist startup still fails; isolated candidates do not meet acceptance'},
 {'id':'SIM-02','status':'FAIL','reason':'No accepted steady state; binary-switch commutation model cannot qualify device stress'},
 {'id':'SIM-03','status':'BLOCKED','reason':'No accepted nominal operating point; full load matrix deferred at Gate1'},
 {'id':'SIM-04','status':'BLOCKED','reason':'Exact supply specification and duty margin not frozen; prior Sprint01 failure retained'},
 {'id':'SIM-05','status':'BLOCKED','reason':'Prerequisite normal-operation/model gates not met; actual CS/latch remain known FAIL'},
 {'id':'SIM-06','status':'BLOCKED','reason':'No validated autonomous HV startup for a credible complete shutdown test; prior passive RC results retained'}]
 data={'system_status':'FAIL/HOLD','gate1':'BLOCKED','native_writeback':'NOT_PERFORMED','tests':matrix,'diagnostics':results,'checks':checks}
 (out/'results.json').write_text(json.dumps(data,indent=2)+'\n')
 files=[p for p in BASE.rglob('*') if p.is_file() and p.name!='waves.txt' and '__pycache__'not in str(p)]
 files += [ROOT/'design9'/n for n in ['sprint02_hv.py','sprint02_vendor.py','sprint02_review.py']]
 (out/'manifest.json').write_text(json.dumps({'sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'scope':'Input snapshots, decks, simulator/model/scripts, raw logs, exact compressed wave files; inherited user/Sprint01 inputs unchanged'},indent=2)+'\n')
 print(json.dumps({'checks':checks,'diagnostic_cases':len(results),'execution_completed':sum(r['execution']=='PASS' for r in results),'tests':matrix},indent=2))
 assert all(checks.values())
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf-8');main()
