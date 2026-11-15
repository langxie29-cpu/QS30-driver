"""Exact model input-port decomposition: IN+ of TI driver is230k + voltage sense only.
Tests a mathematically equivalent load/follower stamp, with no delay or model-value edits.
"""
from pathlib import Path
import json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 dest=ROOT/'sim/s06b_port_equivalent_v1';dest.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py')
 dump(dest/'preregister.json',{'date':'2026-11-15','equivalence':'SLUM488 IN+ enters230k toGND and ideal voltage-controlled comparator only. Place same230k on UCC OUT and ideal zero-delay follower feeding driver IN+; driver own230k current now supplied by follower. Controller external load and input voltage remain identical. Not valid as an actual silicon input-capacitance model.','criteria':'native500us finite, no abort/error; delta step to be evaluated, no delay introduced, original voltage/current constants and solver tolerances unchanged','timeout_s':40})
 rows=[];src=ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns'
 for step in [5e-9,2.5e-9]:
  d=dest/f'{step*1e9:g}ns';d.mkdir()
  for p in src.iterdir():
   if p.is_file() and (p.suffix.lower()=='.lib' or p.name in ['circuit.cir','.spiceinit']):shutil.copyfile(p,d/p.name)
  p=d/'circuit.cir';s=p.read_text();s=s.replace('XD out inhibit','RPORT out 0 230k\nBPORT din 0 V=V(out)\nXD din inhibit');s=re.sub(r'tran \S+ 500u 0 \S+ uic',f'tran {step} 500u 0 {step} uic',s);p.write_text(s,encoding='ascii')
  cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir'];r={'step_s':step}
  try:
   p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
   if (d/'waves.txt').exists():
    a=np.loadtxt(d/'waves.txt',skiprows=1);r.update(end_s=float(a[-1,0]),samples=len(a),finite=bool(np.isfinite(a).all()))
   r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=499.99e-6 else 'FAIL'
  except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
  rows.append(r);dump(dest/'partial_results.json',rows)
 dump(dest/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
