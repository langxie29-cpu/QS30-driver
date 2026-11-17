import sys,csv;sys.path.insert(0,r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2")
import lab
from pathlib import Path
H=Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_01/sense_root")
A,B=0.010040718423769968-2e-6,0.010040718423769968+2e-6
for n in ["run_gear_2e-7","run_gear_1e-7","run_trap_2e-7"]:
    c={k:v for k,v in lab.native(H/n/"circuit.raw").items()}
    t=c["time"];names=list(c)
    with (H/n/"waves_event_window.csv").open("w",newline="",encoding="utf8") as f:
        w=csv.writer(f);w.writerow(names)
        for k in range(len(t)):
            if A<=t[k]<=B: w.writerow([f"{c[x][k]:.15g}" for x in names])
