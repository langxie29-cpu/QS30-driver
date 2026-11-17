"""Supplement the preserved initial40-60ms window; separate startup from ripple.

Does not erase the earlier failure or alter electrical thresholds. Sense absolute
rating is checked independently, even when the output voltage looks acceptable.
"""
import json
import numpy as np
from local_probe import HERE
from render_evidence import partial

def stats(t,v,a,b):
 lo=np.searchsorted(t,a,side='right');hi=np.searchsorted(t,b,side='left')
 tt=np.r_[a,t[lo:hi],b];vv=np.r_[np.interp(a,t,v),v[lo:hi],np.interp(b,t,v)]
 area=np.trapezoid(vv,tt) if hasattr(np,'trapezoid') else np.trapz(vv,tt)
 return dict(start_s=a,end_s=b,mean_V=float(area/(b-a)),min_V=float(vv.min()),max_V=float(vv.max()),pp_V=float(vv.max()-vv.min()))

if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic/nominal_24V_gear_resource600'
 c=partial(d);t=c['time'];v=c['v(hv)'];sense=c['v(sense)'];ix=int(sense.argmax())
 windows=[stats(t,v,a,b) for a,b in [(.04,.06),(.05,.055),(.055,.06)]]
 high=sense>.3
 last=windows[-1]
 r=dict(scope='Supplemental independently selected observed late windows; no new SPICE run, no rewrite of original40-60ms ELECTRICAL_FAIL',
  explanation='40-60ms spans the measured46.2019ms startup band entry, so its13.46V span is not a pure steady ripple metric. Show BOTH that window and two later windows; do not delete the failed initial analysis.',
  windows=windows,late_window_mean_change_V=abs(windows[-1]['mean_V']-windows[-2]['mean_V']),
  SENSE_absolute_rating_V=[-.3,.3],SENSE_min_V=float(sense.min()),SENSE_max_V=float(sense.max()),
  SENSE_outside_rating_samples=int(np.count_nonzero((sense<-.3)|(sense>.3))),
  peak_event=dict(time_s=float(t[ix]),VOUT_V=float(v[ix]),IL_A=float(c['i(lpower)'][ix]),source_V=float(c['v(src)'][ix]),
   VGS_V=float(c['v(gate)'][ix]-c['v(src)'][ix]),SS_V=float(c['v(ss)'][ix]),VC_V=float(c['v(vc)'][ix])),
  evaluation_status='ELECTRICAL_FAIL',
  reason='SENSE exceeds LT3757A +/-0.3V absolute rating in this model. Fast extrema not yet timestep-qualified; physical magnitude INCONCLUSIVE. Output success cannot approve the candidate.',
  milestone='Real controller/0V-to-target behavior observed under nominal fixture. M2 complete qualification and M3 NOT achieved.',
  manufacturer_source='https://www.analog.com/media/en/technical-documentation/data-sheets/LT3757-3757A.pdf page2 absolute maximum ratings')
 (d/'settled_window_review.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r,indent=2))
