"""Run preregistered cold-start fixtures using the existing R11 ngspice DLL host."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
KICAD = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin"))
DLL_RUN = HERE.parent / "r11/sim/dll_run.py"
INPUTS = {
    "a": {"uccx813-3.lib": "A/SimCalcFiles/uccx813-3.lib"},
    "b": {name: "B/ltspice/" + name for name in (
        "LM3488_TRANS.LIB", "irfh7185pbf.spi", "ES3J.lib", "SMDJxxxCA.lib")},
}
ROUTE_FILE = {"a": "a_boost.inc", "b": "b_flyback.inc"}
SOURCES = {
    "A": "https://github.com/drkmsmithjr/NixiePowerSupply/blob/14d6dbdf172b5c5d0535d9fe728d953f2daf0fe2/",
    "B": "https://github.com/esynr3z/nixie-ps/blob/9df409c9770b6c32111396fc9dea318ff907d41d/",
}


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def circuit(case):
    route = case["route"]
    target = case.get("hv_set", 170)
    ref = case.get("vref", 2 if route == "a" else 1.22)
    fb_top = 645120 if route == "a" else 1200000
    fb_bottom = fb_top * ref / (target - ref)
    power = (HERE / "sim" / ROUTE_FILE[route]).read_text()
    power = power.replace("R_FB2 fb 0 7.68k", f"R_FB2 fb 0 {fb_bottom:.9g}")
    power = power.replace("R_FB2 fb 0 8674.0", f"R_FB2 fb 0 {fb_bottom:.9g}")
    if case.get("sense_filter"):
        power = power.replace("fb source 0 vin LM3488_TRANS", "fb isen 0 vin LM3488_TRANS")
        power += "\nR_FILTER source isen 100\nC_FILTER isen 0 100p\n"
    common = (HERE / "sim/common.inc").read_text()
    if "ramp_s" in case:
        common = common.replace("300u", f"{.0001 + case['ramp_s']}")
    params = {
        "VIN":case["vin"], "RPATH":case["rpath"], "PLV":case["plv"], "IHV":case["ihv"],
        "CEFF":case.get("ceff","2u"), "CT":case.get("ct","430p"),
        "LMAG":case.get("lmag", "33u" if route == "a" else "10u"),
        "RATIO":case.get("ratio",14.5), "COUPLING":case.get("coupling",.95),
        "SHUNT":case.get("shunt","33m"), "RFA":case.get("rfa","47k"),
        "RFB_SUM":fb_top + fb_bottom,
    }
    p = ".param " + " ".join(f"{k}={v}" for k, v in params.items())
    method = case.get("method", "gear")
    return f"""R13 {case['id']} isolated fixture
{p}
{power}
{common}
.options method={method} reltol=0.003 abstol=1n {case.get("extra_options", "")}
.tran 100n {case['duration']} 0 100n uic
.end
"""


def metrics(path, case):
    header = {}
    names = []
    with path.open("rb") as file:
        for line in file:
            if line.strip() == b"Binary:":
                break
            line = line.decode("ascii", "replace")
            if line.startswith("\t") and len(line.split()) >= 3:
                names.append(line.split()[1].lower())
            if ":" in line:
                key, value = line.split(":", 1)
                header[key] = value.strip()
        else:
            raise ValueError("No binary plot")
        offset = file.tell()
    size = int(header["No. Points:"])
    data = np.memmap(path, dtype="<f8", offset=offset, mode="r", shape=(size, len(names)))
    vectors = dict(zip(names, data.T))
    t = vectors["time"]
    if not np.all(np.isfinite(data)) or np.any(np.diff(t) < 0):
        raise ValueError("Non-finite or unordered waveform")
    final = t >= case["duration"] - min(.003, .2 * case["duration"])
    hv = vectors["v(hv)"]
    initial = float(vectors["v(hvc)"][0])
    end = float(t[-1])
    output = {"last_s":end, "samples":size, "initial_cap_v":initial,
              "initial_magnetic_current_a":float(vectors["i(lpower)"][0]),
              "peak_v":float(np.max(hv)), "peak_vds":float(np.max(vectors["v(vds)"])),
              "peak_vgs":float(np.max(vectors["v(vgs)"])),
              "peak_inductor_a":float(np.max(vectors["i(lpower)"])),
              "peak_switch_a":float(np.max(vectors["i(vq)"])),
              "peak_input_a":float(-np.min(vectors["i(v_in)"])), "waveform_sha256":sha(path)}
    reached = np.flatnonzero(hv >= .95 * case.get("hv_set",170))
    if reached.size:
        output["first_95pct_s"] = float(t[reached[0]])
    if end >= case["duration"] - 1e-8 and np.count_nonzero(final) > 1:
        tf = t[final]
        dt = np.diff(tf)
        def average(name):
            y = vectors[name][final]
            return float(np.dot(dt, (y[1:] + y[:-1])*0.5) / (tf[-1] - tf[0]))
        output.update(hv_avg_v=average("v(hv)"), hv_ripple_vpp=float(np.ptp(hv[final])),
                      hv_min_v=float(np.min(hv[final])), hv_max_v=float(np.max(hv[final])),
                      vin_avg_v=average("v(vin)"), switch_net_w=average("v(p_sw)"),
                      hv_load_w=average("v(p_hv)"), source_w=average("v(p_in)"))
        if output["source_w"] > 0:
            output["source_to_hv_ratio_including_lv"] = output["hv_load_w"]/output["source_w"]
    indices = set(np.linspace(0, size-1, min(size, 121), dtype=int))
    if np.any(final):
        window = np.flatnonzero(final)
        indices.update(np.linspace(max(window[0],size-1800),size-1,min(window.size,241),dtype=int))
    with (path.parent / "waveform_sample.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(names)
        writer.writerows(np.round(data[sorted(indices)], 12))
    return output


def run(case, out, timeout):
    folder = out / case["id"]
    folder.mkdir()
    model_sources = {}
    for name, source_path in INPUTS[case["route"]].items():
        local = HERE / ".local" / source_path
        digest = sha(local)
        pinned = json.loads((HERE / "sim/model_pins.json").read_text())
        if pinned[source_path] != digest:
            raise ValueError(f"Input SHA mismatch: {source_path}")
        shutil.copyfile(local, folder / name)
        upstream, rel = source_path.split("/", 1)
        model_sources[name] = {"source":SOURCES[upstream]+rel, "sha256":digest,
                               "local_only":True}
    target = folder / "circuit.cir"
    target.write_text(circuit(case), encoding="ascii")
    write_json(folder / "model_sources.json", model_sources)
    command = [str(KICAD / "python.exe"), "-u", str(DLL_RUN), str(target)]
    status = "SOLVER_ERROR"
    code = None
    with (folder / "run.log").open("wb") as log:
        try:
            code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
    report = {"case":case, "command":command, "solver_dll_sha256":sha(KICAD/"ngspice.dll"),
              "host_sha256":sha(DLL_RUN), "netlist_sha256":sha(target), "exit_code":code}
    raw = folder / "waveform.raw"
    if raw.is_file():
        report.update(metrics(raw, case))
        report["waveform_local_path"] = str(raw)
    if code == 0:
        status = "INCOMPLETE_WAVEFORM"
        if "hv_avg_v" in report:
            target_hv = case.get("hv_set", 170)
            regulated = (target_hv-5 <= report["hv_min_v"] <= report["hv_max_v"] <= target_hv+5
                         and report["hv_ripple_vpp"] <= 1 and abs(report["initial_cap_v"]) < 1e-3
                         and abs(report["initial_magnetic_current_a"]) < 1e-3)
            status = "FIXTURE_REGULATION_ONLY" if regulated else "FIXTURE_REWORK"
    report["status"] = status
    write_json(folder / "measurement.json", report)
    return case["id"], status, report.get("hv_avg_v")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", action="append")
    parser.add_argument("--registry", type=Path, default=HERE/"sim_cases.json")
    parser.add_argument("--timeout-s", type=int, default=100)
    args = parser.parse_args()
    cases = json.loads(args.registry.read_text())
    selected = [x for x in cases if args.case is None or x["id"] in args.case]
    if not selected or (args.case and set(args.case) != {x["id"] for x in selected}):
        parser.error("Unknown case")
    args.out.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run, case, args.out.resolve(), args.timeout_s) for case in selected]
        for future in futures:
            print(*future.result(), flush=True)


if __name__ == "__main__":
    main()
