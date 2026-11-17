import sys,json;sys.path.insert(0,r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2")
import lab,numpy as np
from pathlib import Path
H=Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_01/sense_root")
A,B=0.010040718423769968-2e-6,0.010040718423769968+2e-6
res={"window_s":[A,B],"rows":{}}
for n in ["run_gear_2e-7","run_gear_1e-7","run_trap_2e-7"]:
    c=lab.native(H/n/"circuit.raw");t=np.asarray(c["time"]);k={a:np.asarray(v) for a,v in c.items()}
    r={}
    for b in ["i(rsrc)","i(rf)","i(rgs)","i(rneg)","i(csnub)","i(rsnub)","i(drec)","i(lpower)","v(gate)","v(src)","v(sense)"]:
        y=k[b];m=(t>=A)&(t<=B);i=np.argmax(np.abs(y[m]));val=y[m][i]/ (1e3 if b=="v(gate)" else 1)
        r[b]=dict(abspeak=(float(abs(y[m]).min()/1e3) if b=="v(gate)" else float(abs(y[m]).max())),t_us=round(float(t[m][i])*1e6,4),
                  charge_C=float(np.trapezoid(y[m],t[m])))
    # src-node KCL from available branches only
    isrc=k["i(rsrc)"];irf=k["i(rf)"];irgs=k["i(rgs)"];irneg=k["i(rneg)"]
    m=(t>=A)&(t<=B)
    r["kcl_src_partial"]={"terms_available":["I(RSRC): src->shunt? sign as-is","I(RF): src->sense","I(RGS): gate->src","I(RNEG): neg->gate"],
      "max_abs_residual_A":float(np.abs(isrc[m]-irf[m]-irgs[m]).max()),
      "mean_residual_A":float((isrc[m]-irf[m]-irgs[m]).mean()),
      "unavailable":["I_XQ:LS (MOS source pin)","I_XQ:LD","I_XQ:LG","I_XNEG:ddio","I_XNEG:dgr"],
      "note":"residual here is NOT a KCL error; it IS the unobserved MOS/normal-clamp port current, because that branch is exactly what is missing from the sum"}
    res["rows"][n]=r
# R1 comparison in same window
s=lab.native(lab.BASE/"circuit.raw");ts=np.asarray(s["time"]);m=(ts>=A)&(ts<=B)
res["rows"]["R1_source"]={"i(drec)":{"charge_C":float(np.trapezoid(np.asarray(s["i(drec)"])[m],ts[m])),"abspeak":float(np.abs(s["i(drec)"][m]).max())},
  "i(lpower)":{"charge_C":float(np.trapezoid(np.asarray(s["i(lpower)"])[m],ts[m]))},
  "v(sense)":{"max":float(np.asarray(s["v(sense)"])[m].max())}}
lab.dump(H/("review_window.json" if False else "window_metrics.json"),res)
print(json.dumps(res["rows"]["R1_source"],indent=1));print({n:(res["rows"][n]["kcl_src_partial"]["max_abs_residual_A"],res["rows"][n]["i(drec)"]["charge_C"]) for n in ["run_gear_2e-7","run_gear_1e-7","run_trap_2e-7"]})

