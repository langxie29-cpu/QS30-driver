"""Independent cycle observations from the actual completed native trace."""
import json
import numpy as np
from local_probe import HERE
from render_evidence import partial
if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic/nominal_24V_gear_resource600'
 c=partial(d);t=c['time'];il=c['i(lpower)'];vg=c['v(gate)']-c['v(src)'];sense=c['v(sense)']
 rises=np.flatnonzero((vg[:-1]<6)&(vg[1:]>=6))+1
 rows=[]
 for a,b in zip(rises[:-1],rises[1:]):
  off=vg[a:b]<1
  if not off.any():continue
  vals=il[a:b][off];period=float(t[b]-t[a])
  rows.append(dict(time_s=float(t[a]),period_s=period,IL_off_min_A=float(vals.min()),IL_off_max_A=float(vals.max()),
                   no_zero_cross_in_off=bool(vals.min()>.02),zero_cross_seen=bool(vals.min()<=0<=vals.max())))
 def group(a,b):
  r=[x for x in rows if a<=x['time_s']<b]
  return dict(window_s=[a,b],cycles=len(r),no_zero_cross_off_cycles=sum(x['no_zero_cross_in_off'] for x in r),zero_cross_seen_cycles=sum(x['zero_cross_seen'] for x in r),
    median_frequency_Hz=float(1/np.median([x['period_s'] for x in r])) if r else None)
 k=int(sense.argmax())
 out=dict(scope='Cycle extraction only; not demagnetization safety/zero-current detector qualification',
  detection='Actual VGS upward6V cycle edges; examine IL only where actual VGS<1V. Positive off-min>20mA excludes zero crossing; a crossing alone does not prove a stable demagnetized idle interval.',
  windows=[group(.002,.01),group(.01,.04),group(.05,.06)],
  worst_sense_event=dict(time_s=float(t[k]),SENSE_V=float(sense[k]),source_V=float(c['v(src)'][k]),
    source_shunt_current_Vsrc_over62mohm_A=float(c['v(src)'][k]/.062),IL_A=float(il[k]),rectifier_current_A=float(c['i(drec)'][k])),
  conclusion='Positive off-current startup cycles require CCM/cross-mode review. IL peak alone does not bound shunt/CS stress; diode/capacitive/gate currents must be separated with additional current observations. No hard current-limit delay or guaranteed demagnetization claimed.')
 (d/'cycle_review.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(out,indent=2))
