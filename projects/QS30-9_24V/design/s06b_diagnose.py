"""Append-only exact failure replay and controlled hypothesis tests. No HV loop."""
from pathlib import Path
import difflib,hashlib,json,re,shutil,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 dest=ROOT/'sim/s06b_diagnostic_v1';dest.mkdir(exist_ok=False)
 out=ROOT/'docs/sprint06b';out.mkdir(exist_ok=False)
 snapshot={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.is_relative_to(dest) and not p.is_relative_to(out)}
 dump(out/'input_snapshot.json',snapshot)
 (out/'git_status_before.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=REPO))
 exe=REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
 cases=[(f'driver1ns_replay{i}',ROOT/'sim/s06_driver_unit_v1/11.4_switch_1ns',None,100e-6) for i in range(1,4)]
 cases += [('integrated_replay5ns',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns',None,500e-6),('integrated_input100ohm',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns','inputR',500e-6),('integrated_STEADY_diagnostic',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns','steady',500e-6)]
 dump(dest/'preregister.json',{'date':'2026-11-15','scope':'failure reproduction and controlled component-model diagnosis, no boost','cases':[dict(name=n,source=str(s.relative_to(ROOT)),change=m,stop_s=t) for n,s,m,t in cases],'criteria':'rc0, no fatal/error/aborted/timestep too small, finite waves, native end. Any premature end is FAIL. Same tolerances as archived fixture; no model electrical retuning.','simulator':str(exe),'simulator_sha256':sha(exe),'timeout_s_each':40})
 shutil.copyfile(Path(__file__),dest/'runner_snapshot.py');results=[]
 for name,source,mode,stop in cases:
  d=dest/name;d.mkdir()
  for p in source.iterdir():
   if p.is_file() and (p.suffix.lower()=='.lib' or p.name in ['circuit.cir','.spiceinit']):shutil.copyfile(p,d/p.name)
  p=d/'circuit.cir';original=p.read_text(encoding='ascii');changed=original
  if mode=='inputR':changed=changed.replace('XD out inhibit','RINPUT out din 100\nXD din inhibit')
  if mode=='steady':changed=changed.replace('UCC28C43_START','UCC28C43_STEADY')
  if mode:
   p.write_text(changed,encoding='ascii');dump(d/'fixture_change.json',{'hypothesis':mode,'diff':''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True))),'scope':'Diagnostic only. Physical resistor or STEADY model changes are not proof of START performance.'})
  cmd=[str(exe),'-b','-o','ngspice.log','circuit.cir'];start=time.monotonic();r={'name':name,'change':mode,'expected_stop_s':stop}
  try:
   proc=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
   dump(d/'command.json',{'argv':cmd,'cwd':str(d),'rc':proc.returncode,'stdout':proc.stdout.decode(errors='replace'),'stderr':proc.stderr.decode(errors='replace'),'seconds':time.monotonic()-start})
   log=(d/'ngspice.log').read_text(errors='replace') if (d/'ngspice.log').exists() else ''
   bad=bool(re.search(r'(?im)^\s*(error|fatal)|timestep too small|simulation\(s\) aborted',log));r.update(rc=proc.returncode,parsed_error=bad)
   if (d/'waves.txt').exists():
    data=np.loadtxt(d/'waves.txt',skiprows=1);r.update(end_s=float(data[-1,0]),samples=len(data),finite=bool(np.isfinite(data).all()))
   r['execution']='PASS' if proc.returncode==0 and not bad and r.get('finite') and r.get('end_s',0)>=stop*(1-1e-6) else 'FAIL'
  except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
  results.append(r);dump(dest/'partial_results.json',results)
 result={'date':'2026-11-15','cases':results,'qualification':'DIAGNOSTIC_SCOPE_ONLY_07_NOT_PASSED'};dump(dest/'results.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
