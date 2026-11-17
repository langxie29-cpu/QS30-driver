"""Bounded, principal-reviewed native regressions; NEVER a real-input/hot-L signoff."""
import argparse,importlib.util,json,re
from pathlib import Path
import numpy as np
import lab
BASE=lab.HERE/'evidence/principal/filter22R_4p7n_threads1_correct_60ms'
WORKER=lab.HERE/'extension/runs/20261117T153515Z/round_02/loop_followup/build_regression.py'
SPECS={'num_gear100':(.012,180,None),'num_trap200':(.012,180,None),
       'vin21p6':(.12,900,(.08,.12)),'vin26p4':(.12,900,(.08,.12)),
       'load_step':(.30,1800,(.26,.30)),'overload':(.16,900,(.14,.16))}
SAVE='.save V(hv) V(sense) I(LPOWER) V(drain) V(gate) V(src) V(out) I(DREC) I(RNEG) I(RSNUB)'
def build(p,kind):
 stop,timeout,window=SPECS[kind];lab.full(p,stop=stop,step=2e-7)
 s=(BASE/'circuit.cir').read_text(encoding='ascii')
 if kind.startswith('num_'):
  s=s.replace('.tran 2e-07 0.06 0 2e-07 uic','.tran 2e-07 0.012 0 2e-07 uic')
  if kind=='num_gear100':s=s.replace('.tran 2e-07 0.012 0 2e-07 uic','.tran 1e-07 0.012 0 1e-07 uic')
  else:s=s.replace('method=gear','method=trap')
 else:
  spec=importlib.util.spec_from_file_location('reviewed_worker',WORKER);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  s=mod.mutate(s,kind)
  if kind.startswith('vin'):s=s.replace('.tran 2e-07 0.2 0 2e-07 uic','.tran 2e-07 0.12 0 2e-07 uic')
  s=re.sub(r'(?m)^\.save .*$',SAVE,s)
 assert 'RF src sense 22' in s and 'CF sense 0 4.7n' in s and 'RSRC src 0 .062' in s
 assert 'RCOMP vc comp 22k' in s and 'CCOMP comp 0 6.8n' in s
 (p/'circuit.cir').write_text(s,encoding='ascii')
 lab.dump(p/'study.json',dict(kind=kind,stop_s=stop,timeout_s=timeout,final_window_s=window,worker_transform_sha256=lab.sha(WORKER),observations='Ten essential top-level signals for corners; source/RF/RGS currents are derivable exactly from saved node voltages and unchanged ideal resistors. No waveform compression.',isolation='Ideal1msinputandAUX,25ClinearL,equivalentresistiveload only. ActualeFuse/hot/fault/9tubeHOLD.',steady_diagnostic='last consecutive10msmeans delta<=.1V plus full predefined final-window rawVpp<=1V',overload_diagnostic='Intentional beyond6W resistive demand; normal170V regulation not required. Pinabs<.3V, observedtrueIL<=2A coldmodel screen only, not hotcurrentrating or faultOVP release.'))
def measure(p,kind):
 c=lab.native(p/'circuit.raw');t=c['time'];v=c['v(hv)'];stop,timeout,window=SPECS[kind]
 entry=None;bad=np.flatnonzero((v<164.9)|(v>175.1))
 if not len(bad):entry=float(t[0])
 elif bad[-1]+1<len(t):entry=float(t[bad[-1]+1])
 m=dict(endpoint_s=float(t[-1]),endpoint_reached=bool(abs(t[-1]-stop)<1e-12),initial_V=float(v[0]),peak_V=float(v.max()),SENSE_peak_V=float(c['v(sense)'].max()),SENSE_min_V=float(c['v(sense)'].min()),IL_peak_A=float(c['i(lpower)'].max()),source_shunt_peak_A=float(c['v(src)'].max()/.062),VGS_min_V=float((c['v(gate)']-c['v(src)']).min()),VGS_max_V=float((c['v(gate)']-c['v(src)']).max()),sustained_entry_in_observed_trace_s=entry,raw_sha256=lab.sha(p/'circuit.raw'),scope='LIMITED25Cmodel/idealinput/resistiveload only. Noactualfront-end/hotL/9tubes/hardware signoff.')
 checks=dict(endpoint=m['endpoint_reached'],SENSE_absolute=bool(m['SENSE_peak_V']<.3 and m['SENSE_min_V']>-.3))
 if window:
  a,b=window;m['final_window_s']=[a,b];m['final_window']=lab.stats(c,a,b)
  means=[lab.stats(c,float(x),float(x+.01))['mean'] for x in np.arange(a,b-.01+1e-12,.01)]
  m['consecutive10ms_means_V']=means;m['maximum_mean_delta_V']=float(np.max(np.abs(np.diff(means)))) if len(means)>1 else None
  if kind!='overload':
   checks.update(normal_mean=164.9<=m['final_window']['mean']<=175.1,raw_ripple=m['final_window']['pp']<=1,normal_peak=m['peak_V']<=180,steady_mean_diagnostic=m['maximum_mean_delta_V'] is not None and m['maximum_mean_delta_V']<=.1)
 if kind=='load_step':
  m['load_steps']=[]
  for start,end in [(.08,.18),(.18,.30)]:
   lo,hi=np.searchsorted(t,[start,end]);tt=t[lo:hi];vv=v[lo:hi];bad=np.flatnonzero((vv<164.9)|(vv>175.1))
   recovery=0.0 if not len(bad) else (float(tt[bad[-1]+1]-start) if bad[-1]+1<len(tt) else None)
   m['load_steps'].append(dict(time_s=start,observe_until_s=end,recovery_s=recovery,peak_V=float(vv.max()),minimum_V=float(vv.min())))
  checks['load_recovery']=all(x['recovery_s'] is not None and x['recovery_s']<=.1 for x in m['load_steps'])
 elif kind=='overload':
  m['overload_window']=lab.stats(c,.08,.16);m['overload_IL']=lab.stats(c,.08,.16,'i(lpower)');checks['cold_current_limit_screen']=m['overload_IL']['maximum']<=2.0;checks['fault_peak_screen']=m['peak_V']<=195
 elif not kind.startswith('num_'):checks['cold_start_observed']=entry is not None and entry<=1
 m['assertions']=checks;m['classification']='LIMITED_PASS' if all(checks.values()) else 'ELECTRICAL_FAIL'
 lab.dump(p/'metrics.json',m);return m
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('kind',choices=SPECS);a.add_argument('--build-only',action='store_true');v=a.parse_args()
 p=lab.HERE/'evidence/principal/regressions'/v.kind;build(p,v.kind)
 if not v.build_only:
  stop,timeout,window=SPECS[v.kind]
  (p/'decision.txt').write_text('Principal extension approval: bounded isolated regression of alreadyapprovedfilter; actualfront-end/hotmodel/HOLD unchanged. Corners120ms/final80-120ms are PROSPECTIVE finite screens, not promised fullmatrix qualification. Loadsteps80/180ms end300ms, beyondnormaloverload80ms end160ms. Reducedobservation only, actualcircuit unchangedapartfromsole mainvariable. Fixedthresholds unchanged. Totalnativeattemptcap36; thisstudy occupies30-35. Noautoretuneorretryonfailure.')
  cmd=lab.execute(p,'Validate approved filter against '+v.kind+' under declared isolated model conditions','Inputplateau/loadcondition OR numericalmethod/step only; observation settings explicitly registered',timeout)
  if cmd['rc']==0:
   m=measure(p,v.kind);print(json.dumps({k:m[k] for k in ['classification','peak_V','SENSE_peak_V','IL_peak_A','assertions']},indent=2))
  else:print(cmd)
