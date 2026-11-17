import sys,json;sys.path.insert(0,r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2")
import lab,numpy as np
from pathlib import Path
H=Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_01/sense_root")
d={}
for n in ["run_gear_2e-7","run_gear_1e-7","run_trap_2e-7"]:
    c=lab.native(H/n/"circuit.raw");d[n]={k:np.asarray(v,dtype=np.float64) for k,v in c.items()}
out={}
for f in ["v(sense)","i(rsrc)","i(drec)","i(csnub)","i(rsnub)","v(gate)","i(rf)","i(rgs)","i(rneg)","i(lpower)","v(drain)","v(src)"]:
    r={}
    for n in d:
        y=d[n][f];i=np.argmax(np.abs(y));r[n]=dict(abspeak=float(abs(y[i])),t=float(d[n]["time"][i]))
    out[f]=r
res={"abspeaks":out}
# event-time probe values, gear200 vs trap200
i0={}
for n in d:
    t=d[n]["time"];res.setdefault("at_10040718ns",{})[n]={f:float(np.interp(0.010040718423769968,t,d[n][f])) for f in ["v(sense)","v(gate)","v(src)","i(rsrc)","i(rf)","i(rgs)","i(rneg)","i(drec)","i(csnub)","i(lpower)"]}
print(json.dumps(res,indent=1))
