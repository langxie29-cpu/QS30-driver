"""Standalone TI UCC27511 model test; integrated controller failure retained separately."""
from pathlib import Path
import difflib,hashlib,json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 dest=ROOT/'sim/s06_driver_unit_v1';dest.mkdir(exist_ok=False)
 model=next((ROOT/'sources/sprint06/UCC27511_unencrypted/unpacked').rglob('*.lib'))
 src=model.read_text(encoding='cp1252');compat=src.replace('(5,52m)6,58m)','(5,52m)(6,58m)')
 pre={'date':'2026-11-15','scope':'Standalone UCC27511DBVR, IN logic sources; 5.333nF linear surrogate equals64nC/12V; not real ST MOS/Miller or integrated boost','model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'diff':''.join(difflib.unified_diff(src.splitlines(True),compat.splitlines(True))),'criteria':{'endpoint_s':100e-6,'gate_fall_3V_delay_s_max':100e-9,'gate_inhibited_V_max':.4,'step_difference_s_max':5e-9},'temperature_C':27,'reltol':.001,'max_runtime_s':30}
 dump(dest/'preregister.json',pre);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py');rows=[]
 for v,mode,step in [(11.4,'switch',2e-9),(11.4,'switch',1e-9),(12.6,'switch',2e-9),(12.6,'inhibited',2e-9),(12.6,'inputs_float',2e-9)]:
  d=dest/f'{v}_{mode}_{step*1e9:g}ns';d.mkdir();(d/'driver.lib').write_text(compat,encoding='cp1252');(d/'.spiceinit').write_text('set ngbehavior=ps\n',encoding='ascii')
  inp='RFP inp 0 1G\nRFM inm 0 1G' if mode=='inputs_float' else 'VIN inp 0 PULSE(0 3.3 10u 2n 2n 20u 40u)\nVIM inm 0 '+('3.3' if mode=='inhibited' else '0')
  deck=f'''S06 independent UCC27511 driver {mode}
.include driver.lib
VDD vdd 0 PWL(0 0 1u {v} 100u {v})
{inp}
XD inp inm 0 vdd dh dl UCC27511_TRANS
RGON dh gate 10
RGOFF dl gate 2.2
RGS gate 0 10k
CG gate 0 5.333333n
.options reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran {step} 100u 0 {step} uic
meas tran native_end MAX time
wrdata waves.txt v(inp) v(inm) v(gate)
quit
.endc
.end
'''
  (d/'circuit.cir').write_text(deck,encoding='ascii');cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']
  try:
   p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30);dump(d/'command.json',{'argv':cmd,'rc':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
   log=(d/'ngspice.log').read_text(errors='replace');a=np.loadtxt(d/'waves.txt',skiprows=1);t,inp,inm,g=a.T
   good=p.returncode==0 and t[-1]>=99.999e-6 and not re.search(r'timestep too small|aborted|(?im:^\s*error)',log) and np.isfinite(a).all()
   delays=[]
   if mode=='switch':
    for j in np.where((inp[:-1]>1.65)&(inp[1:]<=1.65))[0]:
     ti=t[j]+(1.65-inp[j])*(t[j+1]-t[j])/(inp[j+1]-inp[j])
     idx=np.where((g[:-1]>3)&(g[1:]<=3)&(t[:-1]>=ti))[0]
     if len(idx):
      k=idx[0];tg=t[k]+(3-g[k])*(t[k+1]-t[k])/(g[k+1]-g[k]);delays.append(float(tg-ti))
    criterion=bool(delays and max(delays)<=100e-9 and g[t>10e-6].max()>10)
   else:criterion=bool(np.max(g[t>5e-6])<=.4)
   rows.append({'vdd_V':v,'mode':mode,'step_s':step,'execution':'PASS' if good else 'FAIL','gate_max_V':float(g.max()),'gate_fall_delay_s':delays,'engineering':'PASS_STANDALONE_SURROGATE' if good and criterion else 'FAIL','end_s':float(t[-1])})
  except Exception as e:rows.append({'vdd_V':v,'mode':mode,'execution':'FAIL','engineering':'FAIL','error':str(e)})
 delta=None
 if len(rows[0].get('gate_fall_delay_s',[])) and len(rows[1].get('gate_fall_delay_s',[])):delta=abs(rows[0]['gate_fall_delay_s'][0]-rows[1]['gate_fall_delay_s'][0])
 result={'preregister':pre,'cases':rows,'step_delta_s':delta,'passed_standalone_scope':all(x['engineering'].startswith('PASS') for x in rows) and delta is not None and delta<=5e-9,'integrated_controller_gate':'FAILED_NUMERICAL_QUALIFICATION_SEE_s06_buffered_gate_v1','24V_07':'NOT_PASSED'}
 dump(dest/'results.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
