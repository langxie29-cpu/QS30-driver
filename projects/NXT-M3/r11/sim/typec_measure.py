"""Verify Type-C RAW hashes and summarize independent supply/boost measurements."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
RUNS = HERE/"evidence/typec/runs"


def load_waveform(path, expect):
    with path.open("rb") as raw:
        header = []
        for line in raw:
            if line.strip()==b"Binary:":
                break
            header.append(line.decode("ascii","replace"))
        offset = raw.tell()
    names = [line.split()[1].lower() for line in header if line.startswith("\t") and len(line.split())>=3]
    points = int(next(x.split(":")[1] for x in header if x.startswith("No. Points:")))
    if expect != points:
        raise ValueError(path)
    data = np.memmap(path,offset=offset,dtype="<f8",mode="r",shape=(points,len(names)))
    if not np.all(np.isfinite(data)) or not np.all(np.diff(data[:,0])>=0):
        raise ValueError(f"Non-finite or unordered samples in {path}")
    return data, names


def measure(path,info):
    filename = path.parent/"waveform.raw"
    with filename.open("rb") as raw:
        assert hashlib.file_digest(raw,"sha256").hexdigest()==info["waveform_sha256"],filename
    data, names = load_waveform(filename,info["raw_points"])
    time = data[:,0]
    traces = {name:data[:,j] for j,name in enumerate(names)}
    result = {"t_start_s":float(time[0]),"t_last_s":float(time[-1])}
    if "v(a3)" in traces:
        active = time>=.00149
        source = -traces["i(v5)"]
        result.update(hv_initial_v=float(traces["v(hv)"][0]),
                      adapter_peak_after_attach_a=float(np.max(source[active])),
                      adapter_hotplug_peak_a=float(np.max(source[~active])),
                      max_reverse_to_source_after_attach_a=float(max(0,-np.min(source[active]))),
                      diode_reverse_peak_v=float(np.max(traces["v(hv)"]-traces["v(da)"])),
                      hv_at_end_v=float(traces["v(hv)"][-1]),
                      arm_end_v=float(traces["v(armed)"][-1]))
        active_transitions = (traces["v(a3)"][:-1] > .5) & (traces["v(a3)"][1:] < .5)
        off = np.flatnonzero(active_transitions)
        if len(off):
            result["typec_permission_off_s"] = float(time[off[0]+1])
        armed_fall = np.flatnonzero((traces["v(armed)"][:-1]>=1.6) & (traces["v(armed)"][1:]<1.6))
        if len(armed_fall):
            result["arm_fall_s"]=float(time[armed_fall[0]+1])
        if time[-1]>.09:
            crossing=np.flatnonzero((time[1:]>.055) & (traces["v(hv)"][:-1]<161.5) &
                                    (traces["v(hv)"][1:]>=161.5))
            if len(crossing):
                result["rearm_t95_s"]=float(time[crossing[0]+1])
        assert abs(result["hv_initial_v"])<1e-6 and time[-1]>=.064999
    decimated = np.linspace(0,len(time)-1,min(601,len(time)),dtype=int)
    with (path.parent/"waveform_sample.csv").open("w",encoding="utf-8",newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(names)
        writer.writerows(np.round(data[decimated],12))
    (path.parent/"waveform_metrics.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result


def assessment(name, values, valid):
    if not valid:
        return "UNKNOWN", "No complete waveform"
    if name in ("detach_at_48ms","downgrade_at_48ms"):
        assert values["a3_at_end"]<.01
        return "LIMITED_PASS", "Run permission removed, substantial residual HV remains"
    if name in ("default_usb","one_point_five_amp","r40_open"):
        assert values["hv_final"]<1
        return "LIMITED_PASS", "Inhibited HV in this boundary model"
    if name in ("ovp_typec_feedback_open","ocp_typec_forced_sense"):
        if "trip_time" not in values or "armed_loss" not in values:
            return "REWORK", "Expected fault trip or latch transition missing"
        return "LIMITED_PASS", "Trip and latch measured in protection proxy"
    if name=="front_ovlo_5p5":
        assert values["typ_ovlo_at_5p5"]>.5 and values["max_ovlo_at_5p5"]<.5
        return "REWORK", "5.5 V input straddles the retained U1 front OVLO threshold"
    if name=="reverse_u1_fault":
        return "LIMITED_PASS", "Distinguishes assumed Roff from hypothetical short; no device qualification"
    if abs(values["hv_final"]-170)>5 or values["hv_ripple"]>1:
        return "REWORK", "Outside 165–175 V and <=1 Vpp final diagnostic window"
    return "LIMITED_PASS", "Proxy regulation passed final diagnostic window"


def main():
    rows=[]
    for path in sorted(RUNS.glob("*/measurement.json")):
        info=json.loads(path.read_text())
        valid=info["exit"]==0 and info["raw_points"]>0
        measurements=info["measurements"]
        waveform=measure(path,info) if valid else {}
        status,reason=assessment(info["case"],measurements,valid)
        rows.append({"case":info["case"],"status":status,"return_code":info["exit"],"seconds":info["seconds"],
                     "model":info["model"],"command":" ".join(info["command"]),
                     "evidence":str(path.parent.relative_to(HERE)).replace("\\","/"),
                     "measurements":json.dumps(measurements,sort_keys=True),
                     "waveform_calculations":json.dumps(waveform,sort_keys=True),"interpretation":reason})
    if not rows:
        raise RuntimeError("No simulator outputs found")
    with (HERE/"TYPEC_POWER_QUALIFICATION.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} current cases, {sum(row['return_code']==0 for row in rows)} completed")


if __name__=="__main__":
    main()
