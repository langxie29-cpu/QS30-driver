"""Bounded passive CS unit test, NOT a UCC28C43 model or closed-loop simulation.
Append-only output: --run cs_v1 (new name required for each run).
"""
from pathlib import Path
import argparse, hashlib, json, math, re, subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT.parents[1]/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
def run(name):
 if not re.fullmatch(r'[a-zA-Z0-9_-]+',name): raise ValueError('invalid run name')
 dest=ROOT/'sim'/name;dest.mkdir(exist_ok=False,parents=True)
 cfg=json.loads((ROOT/'config/sprint05.json').read_text(encoding='utf8')); results=[]
 (dest/'runner_snapshot.py').write_bytes(Path(__file__).read_bytes())
 (dest/'config_snapshot.json').write_bytes((ROOT/'config/sprint05.json').read_bytes())
 pre={'scope':'Actual 100ohm/220pF passive filter only; ideal current ramp, ideal voltage threshold. No controller silicon, PWM latch, gate, eFuse, boost, tube or protection model.',
 'acceptance_before_run':'rc0; no error; native endpoint10us; >=100 samples; ramp RC error <=1mV; step-halving threshold time difference <=5ns; peak-leading-edge case must remain below0.9V in first200ns.',
 'simulator':str(EXE),'simulator_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'temperature_C':27,'stop_s':10e-6,'reltol':1e-5,'abstol_A':1e-10,'vntol_V':1e-7,'max_runtime_s_each':30,'engineering_status':'24V-07 NOT QUALIFIED regardless of passive test result'}
 (dest/'preregister.json').write_text(json.dumps(pre,indent=2),encoding='utf8')
 for vin,L,threshold,noise in [(26.4,121.5e-6,1.1,-.05),(20.5,165e-6,.9,.05),(24,150e-6,1,0)]:
  for step in [5e-9,2.5e-9]:
   label=f'v{vin}_l{L*1e6:.1f}_th{threshold}_n{noise}_dt{step*1e9}'
   d=dest/label;d.mkdir();slope=.82*vin/L
   # The disturbance source lies in the measurement path only. A 20ns spike tests RC response,
   # not the real MOSFET's unknown recovery noise. No artificial blanking is introduced.
   deck=f'''S05 Kelvin filter passive qualification - not a controller model
BRAMP ideal 0 V={slope}*time
VNOISE sensed ideal {noise}
VSPIKE raw sensed PWL(0 0 1n .5 21n .5 22n 0 10u 0)
RCSF raw cs 100
CCSF cs 0 220p IC=0
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 method=gear
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran {step} 10u 0 {step} uic
meas tran native_end MAX time
wrdata waves.txt v(ideal) v(raw) v(cs)
quit
.endc
.end
'''
   (d/'circuit.cir').write_text(deck,encoding='ascii')
   cmd=[str(EXE),'-b','-o','ngspice.log','circuit.cir']
   try:
    p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30)
    (d/'command.json').write_text(json.dumps({'argv':cmd,'rc':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')},indent=2),encoding='utf8')
    log=(d/'ngspice.log').read_text(errors='replace');a=np.loadtxt(d/'waves.txt',skiprows=1)
    t=a[:,0];cs=a[:,3];raw=a[:,2];tau=22e-9
    window=t>1e-6
    expect=slope*(t-tau)+noise
    error=float(np.max(np.abs(cs[window]-expect[window])))
    cross=np.where((cs[:-1]<threshold)&(cs[1:]>=threshold))[0]
    tc=None
    if len(cross):
     j=cross[0];tc=float(t[j]+(threshold-cs[j])*(t[j+1]-t[j])/(cs[j+1]-cs[j]))
    errlog=bool(re.search(r'(?im)^\s*(error|fatal)|timestep too small|analysis.*aborted',log))
    spike=float(cs[t<200e-9].max())
    ok=p.returncode==0 and not errlog and t[-1]>=9.999e-6 and len(t)>100 and error<=.001 and spike<.9 and tc is not None
    results.append(dict(case=label,Vin_V=vin,L_H=L,threshold_V=threshold,noise_V=noise,step_s=step,samples=len(t),end_s=float(t[-1]),threshold_time_s=tc,current_at_threshold_A=vin/L*tc if tc else None,CS_peak_first200ns_V=spike,RC_error_V=error,result='PASS_PASSIVE_SCOPE_ONLY' if ok else 'FAIL',parsed_error=errlog))
   except Exception as e: results.append(dict(case=label,result='FAIL',error=str(e)))
 sensitivity=[]
 for i in range(0,len(results),2):
  x,y=results[i:i+2];diff=abs(x.get('threshold_time_s',math.inf)-y.get('threshold_time_s',0)) if x.get('threshold_time_s') and y.get('threshold_time_s') else math.inf
  sensitivity.append({'case':x['case'],'threshold_time_difference_s':diff,'result':'PASS' if diff<=5e-9 else 'FAIL'})
 output={'preregister':pre,'cases':results,'step_halving':sensitivity,'passive_filter_pass':all(r['result'].startswith('PASS') for r in results) and all(r['result']=='PASS' for r in sensitivity),'24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','missing':['qualified UCC28C43 oscillator/PWM/UVLO model','nonlinear inductance versus current and temperature','vendor MOS/diode and real gate delay','startup/CCM slope compensation with CT-loading test','fault latch and independent shutdown','eFuse hotplug/SOA and rail sequencing','USB boot/inrush/power loss bench qualification']}
 (dest/'results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(output,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);run(p.parse_args().run)
