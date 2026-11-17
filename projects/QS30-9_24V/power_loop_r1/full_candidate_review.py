"""Quantitative independent review using full uncompressed native doubles."""
import json,sys,re
import numpy as np
from local_probe import HERE
from render_evidence import partial

if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic'/sys.argv[1]
 cmd=json.loads((d/'command.json').read_text());c=partial(d)
 t=c['time'];v=c['v(hv)'];il=c['i(lpower)'];vg=c['v(gate)']-c['v(src)']
 complete=cmd['rc']==0 and t[-1]>=.06 and np.isfinite(v).all() and (np.diff(t)>0).all()
 r=dict(source='circuit.raw',scope='Nominal25C real-controller/resistive-load/linear-L fixture ONLY; no hardware, hot magnetics, corners or fault signoff',
    endpoint_s=float(t[-1]),process_rc=cmd['rc'],endpoint_reached=bool(complete),initial_V=float(v[0]),
    peak_V=float(v.max()),last_V=float(v[-1]),IL_peak_A=float(il.max()),IL_min_A=float(il.min()),
    VGS_min_V=float(vg.min()),VGS_max_V=float(vg.max()),SENSE_max_V=float(c['v(sense)'].max()),
    total_samples=len(t),binary_decoder_note='Uncompressed double records; RC format equivalence at1e-14 failed by6.24e-8V, numerical cause not fully isolated. No assertion of bit-identical ASCII and binary waves.')
 if complete:
  k=t>=.04;tw=t[k];vw=v[k]
  area=np.trapezoid(vw,tw) if hasattr(np,'trapezoid') else np.trapz(vw,tw)
  bad=np.flatnonzero((v<164.9)|(v>175.1));entry=float(t[bad[-1]+1]) if len(bad) and bad[-1]+1<len(t) else (float(t[0]) if not len(bad) else None)
  mean=float(area/(tw[-1]-tw[0]));ripple=float(vw.max()-vw.min())
  r.update(steady_window_s=[float(tw[0]),float(tw[-1])],mean_V=mean,raw_ripple_Vpp=ripple,sustained_entry_in_observed_trace_s=entry,
           gate_note='GATE measured relative to actual source; no derivative current-limit timing claim')
  assertions=dict(Cout_initial_zero=abs(v[0])<1e-6,mean_164p9_to175p1=164.9<=mean<=175.1,ripple_le1V=ripple<=1,
    normal_peak_le180V=v.max()<=180,startup_le1s=entry is not None and entry<=1,
    VGS_within20V_screen=vg.min()>=-20 and vg.max()<=20,IL_below_3p1A_cold_linear_screen=il.max()<=3.1)
  r['assertions']={k:bool(v) for k,v in assertions.items()}
  r['evaluation_status']='LIMITED_PASS' if all(assertions.values()) else 'ELECTRICAL_FAIL'
 else:r['evaluation_status']='INCONCLUSIVE';r['reason']='Incomplete run, cannot infer steady state or startup pass'
 r['remaining']=['Native-reference numerical convergence and high-frequency/peak current checks remain limited',
   'Input21.6/26.4V, load-step recovery, thermal/tolerance sweeps not covered',
   'Actual eFuse/AUX/source rise and hot nonlinear magnetics not modeled',
   '195V specified faults and independent OVP not tested; safety/manufacturing HOLD unchanged']
 (d/'independent_metrics.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r,indent=2))
