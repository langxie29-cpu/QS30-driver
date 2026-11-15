"""Physical 100ohm/100pF driver input filter candidate, not model-parameter tuning."""
from pathlib import Path
import difflib,json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def edge(t,y,th):
 idx=np.where((y[:-1]>th)&(y[1:]<=th))[0]
 return np.array([t[j]+(th-y[j])*(t[j+1]-t[j])/(y[j+1]-y[j]) for j in idx])
def main():
 dest=ROOT/'sim/s06b_input_filter_v1';dest.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py')
 dump(dest/'preregister.json',{'date':'2026-11-15','candidate':'driver input100ohm/100pF to KelvinGND; 10ns nominal RC for edge/noise control. New physical parts, not a hidden model fix.','criteria':{'stop_s':500e-6,'CS_to_gate_3V_delay_s_max':300e-9,'step_delay_delta_s_max':10e-9,'inhibit_gate_V_max':.4},'solver':'same gear/.001/1n/1u, no loosened tolerance','scope':'two primary models plus linear64nC load; no true MOS/Miller/power stage; START and nativeGB6 equation-form diagnostic remain separate'})
 rows=[];src=ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns'
 for native in [False,True]:
  for step in [5e-9,2.5e-9]:
   name=f'{"nativeGB6" if native else "vendor"}_{step*1e9:g}ns';d=dest/name;d.mkdir()
   for p in src.iterdir():
    if p.is_file() and (p.suffix.lower()=='.lib' or p.name in ['circuit.cir','.spiceinit']):shutil.copyfile(p,d/p.name)
   p=d/'circuit.cir';old=p.read_text();new=old.replace('XD out inhibit','RINPUT out din 100\nCINPUT din 0 100p\nXD din inhibit');new=re.sub(r'tran \S+ 500u 0 \S+ uic',f'tran {step} 500u 0 {step} uic',new);p.write_text(new,encoding='ascii')
   dump(d/'fixture_change.json',{'diff':''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),'nativeGB6':native})
   if native:
    p=d/'vendor.lib';s=p.read_text();p.write_text(s.replace('GB6 19 GND Value = {','BGB6 19 GND I = {'),encoding='ascii')
   cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir'];r={'case':name,'nativeGB6':native,'step_s':step}
   try:
    proc=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':proc.returncode,'stdout':proc.stdout.decode(errors='replace'),'stderr':proc.stderr.decode(errors='replace')});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=proc.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
    if (d/'waves.txt').exists():
     a=np.loadtxt(d/'waves.txt',skiprows=1);t=a[:,0];r.update(end_s=float(t[-1]),samples=len(t),finite=bool(np.isfinite(a).all()))
     if t[-1]>=499.99e-6:
      ce=edge(t,-a[:,5],-.6);ge=edge(t,a[:,7],3);delays=[]
      for tc in ce:
       if np.interp(tc-2e-9,t,a[:,7])<6:continue
       future=ge[ge>=tc]
       if len(future):delays.append(float(future[0]-tc))
      r.update(CS_gate_delays_s=delays,inhibit_gate_max_V=float(a[(t>375.5e-6)&(t<394.9e-6),7].max()))
    r['execution']='PASS' if proc.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=499.99e-6 else 'FAIL'
    r['engineering']='PASS_FIXTURE_ONLY' if r['execution']=='PASS' and r.get('CS_gate_delays_s') and max(r['CS_gate_delays_s'])<=300e-9 and r.get('inhibit_gate_max_V',99)<=.4 else 'FAIL'
   except Exception as e:r.update(execution='FAIL',engineering='FAIL',error=str(e));dump(d/'exception.json',r)
   rows.append(r);dump(dest/'partial_results.json',rows)
 dump(dest/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
