"""Diagnose PSPICE G(VALUE) conversion with mathematically identical native B source.
Only GB6 syntax changes. No current, threshold, timing, tolerance or device value tuning.
"""
from pathlib import Path
import difflib,hashlib,json,re,shutil,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 dest=ROOT/'sim/s06b_native_abm_v1';dest.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py')
 cases=[('controller_nativeGB6',ROOT/'sim/s06_controller_v1/osc_nominal_5ns',5e-9),('integrated_nativeGB6_5ns',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns',5e-9),('integrated_nativeGB6_2p5ns',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns',2.5e-9)]
 dump(dest/'preregister.json',{'date':'2026-11-15','scope':'PSpice compatibility structural diagnosis, no electrical value change','adaptation':'GB6 n+ n- VALUE = {expr} becomes BGB6 n+ n- I = {same expr} in both START and STEADY subcircuits','criteria':'rc0, finite data to500us, no aborted/error/timestep failure. Oscillator115k-class and nominal VREF must remain; source change does not establish full silicon model qualification.','timeout_s_each':40})
 rows=[]
 for name,src,step in cases:
  d=dest/name;d.mkdir()
  for p in src.iterdir():
   if p.is_file() and (p.suffix.lower()=='.lib' or p.name in ['circuit.cir','.spiceinit']):shutil.copyfile(p,d/p.name)
  p=d/'vendor.lib';original=p.read_text();changed=original.replace('GB6 19 GND Value = {','BGB6 19 GND I = {');p.write_text(changed,encoding='ascii')
  dump(d/'adaptation.json',{'original_sha256':hashlib.sha256(original.encode()).hexdigest(),'diff':''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True))),'electrical_parameter_edits':False})
  p=d/'circuit.cir';s=p.read_text();s=re.sub(r'tran \S+ 500u 0 \S+ uic',f'tran {step} 500u 0 {step} uic',s);p.write_text(s,encoding='ascii')
  cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir'];r={'name':name,'step_s':step}
  try:
   proc=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':proc.returncode,'stdout':proc.stdout.decode(errors='replace'),'stderr':proc.stderr.decode(errors='replace')})
   log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=proc.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
   if (d/'waves.txt').exists():
    a=np.loadtxt(d/'waves.txt',skiprows=1);t=a[:,0];r.update(end_s=float(t[-1]),samples=len(t),finite=bool(np.isfinite(a).all()))
    if t[-1]>.00049:r.update(VREF_mean_V=float(a[t>.0002,2].mean()),OUT_max_V=float(a[:,4].max()))
   r['execution']='PASS' if proc.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=499.99e-6 else 'FAIL'
  except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
  rows.append(r);dump(dest/'partial_results.json',rows)
 dump(dest/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
