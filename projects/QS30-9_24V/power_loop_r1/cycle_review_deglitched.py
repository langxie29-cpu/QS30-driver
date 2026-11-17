"""Challenge the first gate-crossing counter with two explicit debounce windows."""
import json
import numpy as np
from local_probe import HERE
from render_evidence import partial
if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic/nominal_24V_gear_resource600';c=partial(d)
 t=c['time'];il=c['i(lpower)'];vg=c['v(gate)']-c['v(src)']
 raw=np.flatnonzero((vg[:-1]<6)&(vg[1:]>=6))+1
 def edges(separation):
  keep=[];last=-1
  for i in raw:
   if t[i]-last>=separation:keep.append(int(i));last=t[i]
  return keep
 e2,e4=edges(2e-6),edges(4e-6)
 rows=[]
 for a,b in zip(e4[:-1],e4[1:]):
  off=vg[a:b]<1
  if not off.any():continue
  x=il[a:b][off]
  rows.append(dict(time_s=float(t[a]),period_s=float(t[b]-t[a]),off_min_A=float(x.min()),zero_cross_seen=bool(x.min()<=0<=x.max())))
 groups=[]
 for a,b in [(.002,.01),(.01,.04),(.05,.06)]:
  s=[x for x in rows if a<=x['time_s']<b]
  groups.append(dict(window_s=[a,b],putative_cycles=len(s),positive_off_min_above20mA=sum(x['off_min_A']>.02 for x in s),
   zero_cross_seen=sum(x['zero_cross_seen'] for x in s),median_frequency_Hz=float(1/np.median([x['period_s'] for x in s])) if s else None))
 r=dict(scope='Gate-derived observations only, not controller-output edge proof or demagnetization qualification',
  original_gate_upcrossings=len(raw),deglitched_2us=len(e2),deglitched_4us=len(e4),two_filters_agree=e2==e4,
  thresholds='VGS rise6V; actual VGS<1V off-window; explicit2us/4us refractory hypotheses, below expected8.7us minimum nominal period.',
  groups=groups,
  correction='First cycle_review.json over-counted ringing crossings and its cycle/frequency interpretation is rejected. Original measurements remain unchanged. Save actual controller OUT next time before claiming switching/idle coverage.',
  conclusion='Some complete putative off-intervals keep IL positive; startup cannot be declared all-DCM. Seeing IL crosszero is insufficient to qualify demagnetization. Hard current-limit and stability remain open.')
 (d/'cycle_review_deglitched.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r,indent=2))
