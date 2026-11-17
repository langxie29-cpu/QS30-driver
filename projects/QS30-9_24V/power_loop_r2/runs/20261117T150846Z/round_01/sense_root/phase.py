import sys,re,json;sys.path.insert(0,r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2")
import lab,numpy as np,hashlib
from pathlib import Path
H=Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_01/sense_root")
res={}
for n in ["run_gear_2e-7","run_gear_1e-7","run_trap_2e-7"]:
    c=lab.native(H/n/"circuit.raw");t=np.asarray(c["time"]);k={a:np.asarray(v) for a,v in c.items()}
    lg=(H/n/"circuit.log").read_text(encoding="latin-1")
    hd=[float(x) for x in re.findall(r"Heightened Def Con from ([\d.eE+-]+)",lg)]
    # rising gate edges (v(gate) crossing 6V) as crude switching-phase markers
    up=np.searchsorted(t,0.0)+np.flatnonzero((k["v(gate)"][:-1]<6)&(k["v(gate)"][1:]>=6))
    res[n]=dict(n=int(t.size),t_last=float(t[-1]),dt_min=float(np.diff(t).min()),dt_max=float(np.diff(t).max()),
      heightened=len(hd),heightened_last5us=[x for x in hd if x>=t[-1]-5e-6],
      gate_up_edge_last6=[round(float(t[i])*1e6,3) for i in up[-6:]],
      gate_min_mV=float(k["v(gate)"].min()*1e3),
      csnub_int_window_A_s=None)
print(json.dumps(res,indent=1))
