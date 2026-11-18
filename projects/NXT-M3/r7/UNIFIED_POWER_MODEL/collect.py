"""Preserve repeatable summaries and original raw hashes for R7 native calls."""
from collections import Counter
import csv
import gzip
import json
import os
from pathlib import Path
import re
import shutil

from raw_metrics import metrics, span, trace
from run import log_text

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "evidence" / "runs"

CASES = {
    "exact": ("R1", ((.035,.037),(.049,.057))),
    "sparse": ("R1", ()),
    "gear": ("R1", ((.035,.037),(.049,.057))),
    "nominal": ("R1", ((.035,.037),(.050,.058))),
    "r6_alt": ("R1", ((.035,.037),(.049,.057))),
    "r6_gate_diag": ("R1", ((.035,.037),(.049,.057))),
    "low_clip": ("R2", ((.030,.032),(.050,.058))),
    "p1_vendor_nominal": ("R2", ((.030,.032),(.050,.058))),
    "p1_vendor_low_max": ("R2", ((.030,.032),(.050,.058))),
    "p1_vendor_high_off": ("R2", ((.030,.032),(.050,.058))),
    "p1_vendor_bias_loss": ("R2", ((.031,.032),(.033,.034))),
    "p1_vendor_release": ("R2", ((.045,.047),(.050,.058))),
    "protection": ("R2", ()),
    "isolation": ("R2", ()),
    "efuse_compat": ("R2", ()),
    "p2_tps40210_low_max": ("R4", ((.030,.032),(.050,.058))),
    "p2_tps40210_direct_low_max": ("R4", ((.030,.032),(.050,.058))),
    "p2_tps40210_nominal": ("R4", ((.030,.032),(.050,.058))),
    "p2_ucc28c43_probe": ("R4", ()),
    "p3_24v_screen": ("R4", ((.030,.032),(.050,.058))),
    "p1_compat_low": ("R2", ()),
    "p1_compat_nominal": ("R2", ()),
    "p1_compat_off": ("R2", ()),
    "p2_compat_low": ("R4", ()),
    "p2_compat_direct": ("R4", ()),
    "protection_armed": ("R2", ()),
    "p1_final_nominal": ("R2", ((.006,.008),(.050,.058))),
    "p1_final_low": ("R2", ((.006,.008),(.050,.058))),
    "p1_final_off": ("R2", ((.006,.008),(.050,.058))),
    "p2_final_low": ("R4", ((.027,.030),(.050,.058))),
    "precharge_ramp": ("R2", ()),
    "nominal_trap": ("R2", ((.035,.037),(.050,.058))),
    "low_max_trap": ("R2", ((.035,.037),(.050,.058))),
    "high_off_trap": ("R2", ((.035,.037),(.050,.058))),
    "p2_ucc_fixed": ("R4", ()),
}


def startup_peaks(path):
    with trace(path) as (names, datum, n, _):
        currents = [k for k in ("i(lpower)", "i(vinput)", "i(vpasssense)") if k in names]
        wanted = [(names.index(name), -1 if name=="i(vinput)" else 1) for name in currents]
        if not wanted:
            return {}
        peaks = [(-1.0,None)]*len(wanted)
        for index in range(n):
            data = datum(index)
            for j,(k, sign) in enumerate(wanted):
                value = data[k]*sign
                if value > peaks[j][0]:
                    peaks[j] = (value, data)
        inspect = [name for name in ("v(hv)","v(in)","v(src)","v(sense)","v(gate)","v(pwm)", "v(aux)",*currents) if name in names]
        return {name: dict(time_s=row[0], peak_A=peak, values={k:row[names.index(k)] for k in inspect})
                for name,(peak,row) in zip(currents,peaks)}


def main():
    tmp = Path(os.environ["TEMP"])
    rows = []
    for name,(round_no, windows) in CASES.items():
        dest = tmp / ("nxt-r7-" + name)
        raw_base = "circuit"
        if name == "exact":
            candidates = sorted(tmp.glob("nxt-r7-exact-*"))
            if candidates:
                dest = candidates[-1]
            raw_base = "boost"
        if not (dest/"result.json").exists():
            continue
        out = RUNS / name
        out.mkdir(parents=True, exist_ok=True)
        for filename in ("preregister.json","result.json"):
            shutil.copyfile(dest/filename, out/filename)
        shutil.copyfile(dest/(raw_base+".cir"),out/"circuit.cir")
        log = log_text(dest/(raw_base+".log"))
        (out/"native.log.txt").write_text(log,encoding="utf-8")
        result = json.loads((dest/"result.json").read_text())
        raw = dest/(raw_base+".raw")
        duration = span(raw) if raw.exists() else {}
        measured = result.get("measures",{}).copy()
        for key in ("ov_cross", "cut_cmd", "dual_60", "single_60", "aux_uv"):
            time_match = re.search(rf"^{key}:.*?\bAT\s+([0-9.eE+-]+)",log,re.M|re.I)
            if time_match:
                measured[key] = float(time_match[1])
        bins = Counter(int(float(entry)*1000)//5*5 for entry in re.findall(r"Heightened Def Con from ([\deE+.\-]+)", log))
        evidence = dict(span=duration, defcon_by_5ms=dict(sorted(bins.items())), windows=[])
        evidence["time_measurements_s"] = {k:measured[k] for k in
                                         ("ov_cross","fault_time","cut_cmd","dual_60","single_60","aux_uv") if k in measured}
        if duration.get("last_s"):
            with trace(raw) as (names, datum, n, _):
                point = datum(n-1)
                relevant = ("v(hv)","v(in)","v(aux)","v(pwm)","v(gate)","v(en)","v(latch)")
                evidence["last_signals"] = {key:point[names.index(key)] for key in relevant if key in names}
            if raw.stat().st_size < 5_000_000:
                (out/"circuit.raw.gz").write_bytes(gzip.compress(raw.read_bytes(),mtime=0))
        for start,end in windows:
            if end <= duration.get("last_s",0):
                evidence["windows"].append(metrics(raw,start,end))
        if name in {"exact","nominal","low_clip","p1_final_nominal","p1_final_low","nominal_trap","low_max_trap","high_off_trap"} and duration.get("last_s"):
            evidence["startup_and_steady_global_peaks"] = startup_peaks(raw)
        (out/"waveform_metrics.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
        rows.append(dict(round=round_no,case=name,execution=result["execution"],seconds=result["seconds"],
                         exit_code=result.get("exit_code"),reached_s=duration.get("last_s","UNKNOWN"),
                         end_hv_raw_V=evidence.get("last_signals",{}).get("v(hv)","UNKNOWN"),points=duration.get("points","UNKNOWN"),
                         defcon_log_lines=sum(bins.values()), hv_avg_V=measured.get("hv_avg","UNKNOWN"),
                         hv_pp_V=measured.get("hv_pp","UNKNOWN"), hv_peak_V=measured.get("hv_peak","UNKNOWN"),
                         start_160_s=measured.get("start_160","UNKNOWN"), peak_inductor_A=measured.get("i_l_peak","UNKNOWN"),
                         avg_input_A=-measured["iin_avg"] if "iin_avg" in measured else "UNKNOWN",
                         peak_pass_A=measured.get("i_pass_pk","UNKNOWN"), mean_pass_A=measured.get("i_pass_avg","UNKNOWN"),
                         vds_peak_V=measured.get("vds_peak","UNKNOWN"), evidence=f"evidence/runs/{name}"))
    if rows:
        with (HERE.parent/"SIMULATION_RESULTS.csv").open("w",encoding="utf-8",newline="") as stream:
            out = csv.DictWriter(stream,fieldnames=list(rows[0]))
            out.writeheader()
            out.writerows(rows)
    print(len(rows), "native calls with recorded outcome")


if __name__ == "__main__":
    main()
