"""Principal replacement for rejected draft pulse logic; observed OUT, no inferred PWM."""
import argparse,json
from pathlib import Path
import numpy as np
import lab
def crossings(t,y,rising=True,threshold=6.):
 ids=np.flatnonzero(((y[:-1]<threshold)&(y[1:]>=threshold)) if rising else ((y[:-1]>=threshold)&(y[1:]<threshold)))
 times=t[ids]+(threshold-y[ids])/(y[ids+1]-y[ids])*(t[ids+1]-t[ids]);result=[]
 for x in times:
  if not result or x-result[-1]>=5e-6:result.append(float(x))
 return np.array(result)
def scalar(t,y,x):
 k=np.searchsorted(t,x)
 if k==len(t):return float(y[-1])
 if t[k]==x:return float(y[k])
 return float(y[k-1]+(y[k]-y[k-1])*(x-t[k-1])/(t[k]-t[k-1]))
def analyze(raw,start=.055,end=.060):
 c=lab.native(raw);t=c['time'];mask=(t>=start-20e-6)&(t<=end+20e-6)
 tt=t[mask].copy();vv=c['v(out)'][mask].copy();rise=crossings(tt,vv);fall=crossings(tt,vv,False)
 R=1/(1/5200+2/(2*90900)+1/(200000+1900.6))
 cap=c['v(hv)']-.1*(c['i(drec)']+c['i(rsnub)']-c['v(hv)']/R)
 rows=[]
 for a,b in zip(rise[:-1],rise[1:]):
  if a<start or b>end:continue
  k=np.searchsorted(fall,a)
  if k==len(fall) or fall[k]>=b:continue
  f=float(fall[k]);il=lab.stats(c,a,b,'i(lpower)');hv=lab.stats(c,a,b)
  rows.append(dict(start_s=float(a),end_s=float(b),fall_s=f,frequency_Hz=float(1/(b-a)),OUT_duty=float((f-a)/(b-a)),IL_min_A=il['minimum'],IL_max_A=il['maximum'],IL_at_OUT_fall_A=scalar(t,c['i(lpower)'],f),SENSE_at_OUT_fall_V=scalar(t,c['v(sense)'],f),SENSE_max_V=lab.stats(c,a,b,'v(sense)')['maximum'],HV_raw_Vpp=hv['pp'],HV_mean_V=hv['mean'],ideal_cap_diagnostic_Vpp=lab.stats(dict(time=t,cap=cap),a,b,'cap')['pp']))
 def summary(key):
  v=np.array([r[key] for r in rows]);return dict(minimum=float(v.min()),median=float(np.median(v)),maximum=float(v.max())) if len(v) else None
 return dict(raw=str(raw),raw_sha256=lab.sha(raw),window_s=[start,end],cycles=len(rows),OUT_threshold_V=6,separation_s=5e-6,statistics={k:summary(k) for k in ['frequency_Hz','OUT_duty','IL_min_A','IL_max_A','IL_at_OUT_fall_A','SENSE_at_OUT_fall_V','HV_raw_Vpp','ideal_cap_diagnostic_Vpp']},rows=rows,classification='INCONCLUSIVE',scope='Observed OUT-defined cycles only. No silicon worst-case blanking/propagation or fault current-limit qualification. Ideal-cap voltage is not delivered output.')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('raw');a.add_argument('out');a.add_argument('--start',type=float,default=.055);a.add_argument('--end',type=float,default=.060);v=a.parse_args()
 if Path(v.out).exists():raise FileExistsError('Never overwrite an analysis result')
 m=analyze(Path(v.raw),v.start,v.end);lab.dump(v.out,m);print(json.dumps({k:m[k] for k in ['cycles','statistics','classification']},indent=2))
