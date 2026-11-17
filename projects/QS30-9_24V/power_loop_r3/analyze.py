"""Independent full-sample measurements; signed energies never called thermal loss."""
from r3lib import *
import numpy as np,re,csv,argparse
def integ(t,y):return float(np.trapezoid(y,t))
def summarize(t,y):
 return dict(min=float(y.min()),max=float(y.max()),mean=integ(t,y)/(t[-1]-t[0]),rms=float(np.sqrt(integ(t,y*y)/(t[-1]-t[0]))))
def window(t,y,a,b):
 m=(t>a)&(t<b);return np.r_[a,t[m],b],np.r_[np.interp(a,t,y),y[m],np.interp(b,t,y)]
def measure(p):
 reg=json.loads((p/'preregister.json').read_text());cmd=json.loads((p/'command.json').read_text())
 m=dict(case=reg['case'],path=str(p.relative_to(HERE)),execution=cmd,scope=reg['scope'])
 if cmd['endpoint_s'] is None:
  classification='MODEL_FAIL' if reg['case']=='tps_instantiated_probe' else cmd['execution_status']
  return dict(**m,classification=classification)
 c=native(p/'circuit.raw');t=c['time'];m.update(endpoint_s=float(t[-1]),points=len(t),raw_sha256=sha(p/'circuit.raw'),signals=list(c))
 if 'v(hv)' not in c:return dict(**m,classification='MODEL_FAIL')
 for name in ['v(hv)','i(lpower)','v(sense)','i(drec)','i(rsrc)','i(rneg)','i(cout)','v(intvcc)']:
  if name in c:m[name]=summarize(t,c[name])
 vds=c['v(drain)']-c['v(src)'];vgs=c['v(gate)']-c['v(src)'];vd=c['v(drain)']-c['v(hv)'];ip=c['i(lpower)'];idrec=c['i(drec)'];irs=c['i(rsrc)']
 m['MOS_VDS_external_V']=summarize(t,vds);m['MOS_VGS_external_V']=summarize(t,vgs);m['diode_anode_minus_cathode_V']=summarize(t,vd)
 qd=ip-idrec-c['i(rsnub)'];qg=c['i(rg)']-vgs/1e4+c['i(rneg)'];qs=-irs-(c['v(src)']-c['v(sense)'])/22+vgs/1e4-c['i(rneg)']
 m['MOS_external_drain_current_A']=summarize(t,qd);m['MOS_external_gate_current_A']=summarize(t,qg);m['MOS_external_source_current_A']=summarize(t,qs)
 m['MOS_reconstructed_KCL_A']=float(np.max(np.abs(qd+qg+qs)))
 pext=vds*qd+vgs*qg
 m['MOS_terminal_power_W']=summarize(t,pext);m['MOS_signed_terminal_energy_J']=integ(t,pext);m['MOS_positive_terminal_energy_J']=integ(t,np.maximum(0,pext));m['MOS_negative_terminal_energy_J']=integ(t,np.minimum(0,pext))
 m['diode_terminal_power_W']=summarize(t,vd*idrec);m['diode_signed_terminal_energy_J']=integ(t,vd*idrec)
 m['shunt_power_W']=summarize(t,irs**2*.062);m['shunt_energy_J']=integ(t,irs**2*.062)
 m['initialization_sample']={k:float(c[k][0]) for k in ['time','v(hv)','i(lpower)']}
 m['IL_nonzero_time_A']=summarize(t[1:],ip[1:])
 m['inductor_copper25_est_W']=.16*summarize(t,ip)['rms']**2;m['inductor_copper100_est_W']=m['inductor_copper25_est_W']*(1+.00393*75)
 if 'i(bpass)' in c:
  pp=(c['v(vin)']-c['v(in)'])*c['i(bpass)'];m['frontend_power_W']=summarize(t,pp);m['frontend_signed_energy_J']=integ(t,pp);m['frontend_current_A']=summarize(t,c['i(bpass)']);m['branch_voltage_V']=summarize(t,c['v(in)']);m['input_energy_J']=integ(t,c['v(vin)']*c['i(bpass)'])
  if t[-1]>=.1-1e-10:m['frontend_last20ms_energy_J']=integ(*window(t,pp,t[-1]-.02,t[-1]))
 # Classify only pre-registered finite windows; never use a selected low-ripple excerpt.
 if reg['case'].startswith('front') and reg['stop_s']>=.08:
  for a,b in [(.04,.06),(.06,.08),(.08,.10),(.10,.12)]:
   if t[-1]>=b-1e-10:m.setdefault('windows',{})[f'{a:.2f}-{b:.2f}']=stats(c,a,b)
  oob=np.flatnonzero((c['v(hv)']<164.9)|(c['v(hv)']>175.1))
  m['entered_and_remained_to_endpoint_s']=None if len(oob) and oob[-1]==len(t)-1 else float(t[oob[-1]+1] if len(oob) else t[0])
  w=m.get('windows',{}).get('0.10-0.12') if reg['stop_s']>=.12 else m.get('windows',{}).get('0.06-0.08');m['output_only_pass']=bool(w and 164.9<=w['mean']<=175.1 and w['pp']<=1 and c['v(hv)'].max()<=180 and m['entered_and_remained_to_endpoint_s'] is not None and m['entered_and_remained_to_endpoint_s']<=1)
  m['classification']='LIMITED_PASS' if m['output_only_pass'] and 'loss' not in reg['case'] else 'INCONCLUSIVE'
  m['qualification_scope']='Output metrics only under favorable parameter frontend / native LDO / 25C power models; NOT actual TPS26601, thermal, independent OVP or manufacturing qualification.'
 else:m['classification']='INCONCLUSIVE'
 if reg['case'].startswith('cell'):
  a,b=1.02e-6,1.10e-6
  tw,neg=window(t,np.maximum(-idrec,0),a,b);m['diode_negative_terminal_charge_C']=integ(tw,neg)
  tw,pw=window(t,vd*idrec,a,b);m['diode_window_signed_energy_J']=integ(tw,pw)
  tw,pw=window(t,pext,a,b);m['MOS_event_signed_terminal_energy_J']=integ(tw,pw);m['MOS_event_positive_terminal_energy_J']=integ(tw,np.maximum(0,pw));m['MOS_event_negative_terminal_energy_J']=integ(tw,np.minimum(0,pw))
  event=(t>=a)&(t<=b);m['MOS_event_external_VDS_V']=summarize(t[event],vds[event]);m['MOS_event_external_VGS_V']=summarize(t[event],vgs[event])
  m['diode_event_max_reverse_dvdt_V_per_ns']=float(np.max(np.abs(np.diff(vd[event])/np.diff(t[event])))*1e-9)
  m['diode_reverse_above400V_samples']=int(np.sum(-vd>400));m['diode_reverse_above380V_duration_s']=integ(t,(-vd>380).astype(float))
  m['diode_max_reverse_dvdt_V_per_ns']=float(np.max(np.abs(np.diff(vd)/np.diff(t)))*1e-9)
  if 'v(q:13)' in c:
   m['MOS_intrinsic_VDS_V']=summarize(t,c['v(q:13)']-c['v(q:9)']);m['MOS_intrinsic_VGS_V']=summarize(t,c['v(q:5)']-c['v(q:9)'])
  if 'i(vqd)' in c:
   m['independent_terminal_probe_errors_A']={name:float(np.max(np.abs(x-c[y]))) for name,x,y in [('drain',qd,'i(vqd)'),('gate',qg,'i(vqg)'),('source',-qs,'i(vqs)')]}
  # No repetition frequency in isolated single-edge cell; do not scale by fs as if all cycles identical.
  m['classification']='INCONCLUSIVE'
 if 'short' in reg['case']:
  m['classification']='ELECTRICAL_FAIL' if ip.max()>3.1 else 'INCONCLUSIVE'
  m['failure_scope']='25C constant150uH result exceeds manufacturer3.1A10pct-L-drop point. Invalidates linear-L saturation-margin screen; actual saturated peak not bounded. Not a destructive-current absolute rating.'
  for a,b in [(.012,.0121),(.012,.025)]:
   tw,yy=window(t,ip,a,b);m.setdefault('fault_windows',{})[str((a,b))]=summarize(tw,yy)
  m['fault_switch_current_derived_peak_A']=float(np.max(c['v(hv)'][t>=.012001]/.01))
 return m
def main():
 all=[]
 for p in sorted((HERE/'experiments').iterdir()):
  if p.name.startswith('pending'):continue
  dest=HERE/'evidence/metrics'/f'{p.name}.json'
  if dest.exists():m=json.loads(dest.read_text())
  else:
   try:m=measure(p)
   except Exception as ex:m=dict(case=p.name,classification='EXECUTION_FAIL',analysis_error=str(ex))
   dump(dest,m)
  all.append(m)
 dump(HERE/'evidence/metrics_index.json',all)
 print(json.dumps([dict(case=m['case'],status=m['classification'],entry_s=m.get('entered_and_remained_to_endpoint_s'),HV=m.get('v(hv)'),IL=m.get('i(lpower)'),windows=m.get('windows')) for m in all],ensure_ascii=False),flush=True)
if __name__=='__main__':main()
