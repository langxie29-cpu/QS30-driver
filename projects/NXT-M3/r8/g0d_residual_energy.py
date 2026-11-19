"""Reconcile the archived R8 waveform and run one bounded passive G0D deck."""
import argparse
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

from orchestrate import HERE, git, read_json, sha256, write_json

CONFIG = HERE / "g0d_preregister.json"
OLD = HERE / "evidence/runs/authorized-g0-review/round_02/passive_fault_energy"
WAVEFORM_READER = HERE.parent / "r7/UNIFIED_POWER_MODEL/raw_metrics.py"


def effective_cases(cfg):
    p = cfg["params"]
    v = p["initial_V"]
    ra = p["min_anode_ohm"]
    rb = p["bleed_branch_high_ohm"]
    for row in cfg["cases"]:
        case = dict(row, v0=v, ra=ra, rb=rb,
                    c=p["p1_candidate_max_cap_F"] if row["cap"] == "P1" else p["baseline_max_cap_F"],
                    feed_V=p["passive_feed_ref_V"] if row.get("feed") else 0)
        conductance = row["branches"]/rb
        b = ra*conductance
        x = math.sqrt(b*(b+1))-b
        case["f_upper"] = (math.sqrt(1+b)-math.sqrt(b))**2
        if row["q_ohm"] == "energy":
            case["q_ohm"] = ra*(1/x-1)
        if row["q_ohm"] == "match":
            case["q_ohm"] = ra
        yield case


def signals(v, case):
    ra, rq = case["ra"], case["q_ohm"]
    vt, rb = case["tube_V"], case["rb"]
    ic = max(v-vt, 0)/(ra+rq) if rq is not None else 0
    vce = ic*rq if rq is not None else v
    source = max(case["feed_V"]-v, 0)/10 if case["feed_V"] else 0
    return (vce, ic, *(ic**2*r for r in (rq or 0, ra)), ic*vt,
            v*v*case["branches"]/rb, v*source, source*case["feed_V"], source*max(case["feed_V"]-v, 0))


def traces(raw_path):
    spec = importlib.util.spec_from_file_location("r7_trace", WAVEFORM_READER)
    read = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(read)
    return read.trace(raw_path)


SIGNALS = ("vce_V", "ic_A", "q_proxy_W", "anode_W", "tube_W",
           "bleeds_W", "external_net_at_bus_W", "external_source_W", "feed_path_W")
ENERGY = ("q_proxy", "anode", "tube", "bleeds", "external_net_at_bus", "external_source", "feed_path")


def integrate(raw_path, node, case, window, residual_v, timeseries=None):
    """Integrate linear-interpolated voltage and per-path instantaneous powers."""
    v = case["v0"]
    last_t = 0
    previous = signals(v, case)
    initial = .5*case["c"]*v**2
    energies = [0.0]*len(ENERGY)
    peaks = list(previous[:4])
    v_cross = None
    with traces(raw_path) as (names, datum, n, _):
        pos = names.index(f"v({node})")
        endpoint = datum(n-1)[0]
        if endpoint < window-1e-8:
            raise ValueError("Incomplete raw window")
        if timeseries:
            timeseries.writerow([case["id"], 0, v, *previous, *energies])
        for j in range(n):
            row = datum(j)
            t, now_v = row[0], row[pos]
            if t < last_t:
                raise ValueError("Nonmonotonic time")
            if t == last_t:
                continue
            if t > window:
                now_v = v + (now_v-v)*(window-last_t)/(t-last_t)
                t = window
            dt = t-last_t
            sig = signals(now_v, case)
            if v_cross is None and v > residual_v >= now_v:
                v_cross = last_t+dt*(v-residual_v)/(v-now_v)
            for k, (before, after) in enumerate(zip(previous[2:], sig[2:])):
                energies[k] += dt*(before+after)/2
            peaks = list(map(max, peaks, sig[:4]))
            if timeseries and (j % 80 == 0 or t == window):
                timeseries.writerow([case["id"], t, now_v, *sig, *energies])
            last_t, v, previous = t, now_v, sig
            if t == window:
                break
    values = dict(zip((k+"_mJ" for k in ENERGY), (x*1000 for x in energies)))
    remaining = .5*case["c"]*v**2
    error = initial + energies[4] - remaining - sum(energies[:4])
    return {"case":case["id"], "scope":case["role"], "window_s":window,
            "C_uF":case["c"]*1e6, "branches":case["branches"], "v_initial_V":case["v0"], "v_end_V":v,
            "t_to_60V_s":v_cross, "peak_vce_V":peaks[0], "peak_ic_mA":peaks[1]*1000,
            "peak_proxy_W":peaks[2],"peak_anode_W":peaks[3],
            "initial_mJ":initial*1000, **values, "final_cap_mJ":remaining*1000,
            "bus_balance_error_mJ":error*1000,
            "input_balance_error_mJ":(energies[5]-energies[4]-energies[6])*1000}


def make_deck(cfg, cases):
    lim = cfg["limits"]
    lines = ["* RESIDUAL_ENERGY_FAULT_TEST: passive cases after ideal removal unless F5",
             "* Fixed resistor and ideal already-lit constant drop. No MMDTA42 junction or SOA model."]
    for case in cases:
        node = case["id"]
        lines.append(f"C{node} {node} 0 {case['c']:.10g} IC={case['v0']:.8g}")
        for k in range(case["branches"]):
            lines.append(f"Rbleed{node}{k+1} {node} 0 {case['rb']:.10g}")
        rq = case["q_ohm"]
        if rq is not None:
            ra = case["ra"]
            if case["tube_V"]:
                lines.append(f"Bload{node} {node} 0 I=max((V({node})-{case['tube_V']})/{ra+rq:.10g},0)")
            else:
                lines.extend([f"Ra{node} {node} q{node} {ra:.10g}", f"Rq{node} q{node} 0 {rq:.10g}"])
        if case["feed_V"]:
            lines.append(f"Bfeed{node} 0 {node} I=max(({case['feed_V']}-V({node}))/10,0)")
    lines.extend([f".tran 0 {lim['endpoint_s']} 0 {lim['max_step_s']} uic",
                  ".opt plotwinsize=0", ".end"])
    return "\n".join(lines)+"\n"


def run(exe, out):
    cfg = read_json(CONFIG)
    if cfg["manufacturing"] != "ENGINEERING HOLD" or cfg["limits"]["billable_calls_authorized_for_g0d"]:
        raise ValueError("Offline G0D run requires fixed HOLD and zero model billing")
    cases = list(effective_cases(cfg))
    out.mkdir(parents=True, exist_ok=False)
    archived = OLD/"circuit.raw"
    if sha256(archived) != read_json(OLD/"metrics.json")["raw_sha256"]:
        raise ValueError("Prior waveform changed")
    old = dict(cases[1],id="archived_halfon",role="Existing fixed resistors, reread original raw")
    r1 = integrate(archived, "faultbus", old, 1, 60)
    if abs(r1["q_proxy_mJ"]-45.1705)>.02:
        raise ValueError("Unexpected archived Q analogue energy")
    write_json(out/"round_01_archive.json",dict(archived_raw_sha256=sha256(archived),archive=r1,
                  source_hashes={name:sha256(OLD/name) for name in ("circuit.cir","circuit.log","metrics.json","preregister.json")}))
    deck = out/"circuit.cir"
    deck.write_text(make_deck(cfg,cases),encoding="ascii",newline="\n")
    executable = exe.resolve()
    command = [str(executable),"-b",str(deck)]
    write_json(out/"preregister.json",dict(input_config_sha256=sha256(CONFIG),git_head=git("rev-parse","HEAD"),
        native_solver_path=str(executable),native_solver_sha256=sha256(executable),command=command,
        generated_deck_sha256=sha256(deck),cfg=cfg))
    flags = getattr(subprocess,"CREATE_NO_WINDOW",0)
    env = {**os.environ,"LOCALAPPDATA":str(out/"cache"),"APPDATA":str(out/"settings")}
    try:
        proc = subprocess.run(command,cwd=out,timeout=cfg["limits"]["solver_wall_s"],capture_output=True,
                              env=env,creationflags=flags,check=False)
        stdout,stderr,code = proc.stdout,proc.stderr,proc.returncode
    except subprocess.TimeoutExpired as error:
        stdout,stderr,code = error.stdout or b"",error.stderr or b"",None
    (out/"stdout.txt").write_bytes(stdout)
    (out/"stderr.txt").write_bytes(stderr)
    write_json(out/"process.json",{"exit_code":code})
    raw = out/"circuit.raw"
    if code != 0 or not (out/"circuit.log").is_file() or not raw.is_file() or not 0<raw.stat().st_size<=536870912:
        raise RuntimeError("INCONCLUSIVE: incomplete native solver evidence")
    lim = cfg["limits"]
    results = [r1]
    with (out/"decimated_traces.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.writer(stream,lineterminator="\n")
        writer.writerow(["case","time_s","vcout_V",*SIGNALS,*(k+"_J" for k in ENERGY)])
        for case in cases:
            results.append(integrate(raw,case["id"],case,1,60))
            results.append(integrate(raw,case["id"],case,lim["endpoint_s"],60,writer))
    for row in results:
        for field in ("bus_balance_error_mJ","input_balance_error_mJ"):
            if abs(row[field]) > lim["balance_abs_mJ"]:
                raise ValueError(f"Energy did not reconcile for {row['case']}")
    for case in cases:
        if case["role"].startswith(("F3 energy envelope","Sensitivity F3","P1 3.3uF")):
            row = next(r for r in results if r["case"]==case["id"] and r["window_s"]==lim["endpoint_s"])
            expected = case["f_upper"]*(row["initial_mJ"]-row["final_cap_mJ"])
            if abs(row["q_proxy_mJ"]/expected-1) > lim["closed_form_rel_error"]:
                raise ValueError("Envelope run and closed form disagree")
    with (out/"energy_distribution.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(results[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    with traces(raw) as (names,datum,n,available):
        span = {"last_s":datum(n-1)[0],"points":n,"records":available}
    output = dict(simulation_status="LIMITED_PASS_PASSIVE_ENERGY_ONLY",grid=span,raw_sha256=sha256(raw),
        log_sha256=sha256(out/"circuit.log"),results=results,
        analytic_envelopes=[{"case":c["id"],"fraction":c["f_upper"],"bound_mJ":c["f_upper"]*.5*c["c"]*c["v0"]**2*1000}
                            for c in cases if c["id"] in ("f3env","f6env","p1env")])
    write_json(out/"metrics.json",output)
    print("Verified passive integration",span,"and",len(results),"windows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    run(args.solver,args.output.resolve())
