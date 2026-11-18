"""Read already sealed local waveforms; no native solver calls."""
from r4lib import *
import numpy as np
def main():
 rows=[]
 for prefix in ['sic_1ns','sic_0p5ns','ucc_driver_local']:
  p=next((HERE/'experiments').glob(prefix+'_*'));c=native(p/'circuit.raw');t=c['time'];w=(t>=1.02e-6)&(t<=1.1e-6)
  r=dict(case=prefix,raw_sha256=sha(p/'circuit.raw'),window_s=[1.02e-6,1.1e-6],port_current_names=[k for k in c if k.startswith('i(vq')])
  if all(k in c for k in ['i(vqd)','i(vqg)','i(vqs)']):
   residual=c['i(vqd)']+c['i(vqg)']-c['i(vqs)'];r['MOS_three_terminal_KCL_abs_residual_A']=float(np.max(abs(residual[w])));r['KCL_acceptance_A']=.001;r['KCL_status']='PASS'if r['MOS_three_terminal_KCL_abs_residual_A']<=.001 else'INCONCLUSIVE'
  if'v(q:5)'in c and'v(q:9)'in c:
   v=c['v(q:5)']-c['v(q:9)'];r['intrinsic_VGS_fulltrace_V']=[float(v.min()),float(v.max())]
  if'i(rneg)'in c:r['negative_clamp_peak_abs_A']=float(np.max(abs(c['i(rneg)'])))
  rows.append(r)
 a=json.loads(next((HERE/'evidence/measurements').glob('sic_1ns_*.json')).read_text());b=json.loads(next((HERE/'evidence/measurements').glob('sic_0p5ns_*.json')).read_text())
 dump(HERE/'evidence/supplemental_waveform_analysis.json',dict(utc=utc(),cases=rows,step_halving_change_pct={k:100*abs(a[k]-b[k])/abs(b[k])for k in ['shunt_abs_peak_A','Dnegative_port_charge_C','Dreverse_peak_A']},scope='Typical models/finite matched cell; port KCL is topology consistency, not physical model validation or device qualification'))
 print(json.dumps(rows))
if __name__=='__main__':main()
