"""Run low-energy numerical fixtures using KiCad's bundled ngspice."""
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence/simulation"
DLL_RUN = HERE.parent / "r11/sim/dll_run.py"
CONDITIONS = {
    # bus, assumed tube drop, upstream sustained, drive mode, C-E ohms, C-B ohms, parallel digits
    "off": (170, 0, True, "off", 1e12, 1e12, 1),
    "on": (170, 130, True, "on", 1e12, 1e12, 1),
    "half_170_sustain": (170, 0, True, "off", 19800, 1e12, 1),
    "half_195_sustain": (195, 0, True, "off", 19800, 1e12, 1),
    "half_195_isolated": (195, 0, False, "off", 19800, 1e12, 1),
    "half_195_tube130": (195, 130, True, "off", 19800, 1e12, 1),
    "ce_short": (195, 0, True, "off", .1, 1e12, 1),
    "cb_10meg": (195, 0, True, "off", 1e12, 1e7, 1),
    "cb_1meg": (195, 0, True, "off", 1e12, 1e6, 1),
    "cb_100k": (195, 0, True, "off", 1e12, 1e5, 1),
    "cb_10k": (195, 0, True, "off", 1e12, 1e4, 1),
    "cb_short": (195, 0, True, "off", 1e12, .1, 1),
    "leak_ce_1meg": (195, 0, True, "off", 1e6, 1e12, 1),
    "leak_ce_100k": (195, 0, True, "off", 1e5, 1e12, 1),
    "leak_ce_10k": (195, 0, True, "off", 1e4, 1e12, 1),
    "open_cathode": (170, 0, True, "on", 1e12, 1e12, 0),
    "erroneous_on": (195, 0, True, "on", 1e12, 1e12, 1),
    "three_half": (195, 0, True, "off", 19800, 1e12, 3),
    "logic_off_cb_short": (195, 0, True, "dead", 1e12, .1, 1),
    "highz_cb_short": (195, 0, True, "highz", 1e12, .1, 1),
    "intermediate_output": (195, 0, True, "mid", 1e12, 1e12, 1),
}
COLUMNS = ("time", "v(hv)", "v(vce)", "v(vbe)", "v(ib)", "v(ic)", "v(ianode)",
           "v(pq)", "v(pce)", "v(pcb)", "v(pdut)", "v(eback)", "v(isupply)")


def cathode(config):
    bus, tube, powered, drive, rce, rcb, count = config
    drv = {"off": (0, 50), "on": (3.3, 50), "dead": (0, 50),
           "highz": (0, 1e12), "mid": (.82, 50)}
    volts, rout = drv[drive]
    power_feed = f"VSOURCE src 0 {bus}\nVSENSE src hv 0" if powered else "VNO src 0 0\nVSENSE src spare 0\nRSPARE spare 0 1e12"
    fixture = [f"R14 cathode proxy, {config}", power_feed,
               f"CHV hv 0 3.63u ic={bus}", "RBLEED1 hv 0 500960", "RBLEED2 hv 0 500960",
               # Vendor device model and breakdown/SOA data are unavailable.
               ".model QPROXY NPN(IS=1e-14 BF=60 VAF=80 BR=2 IKF=.05)",
               ".model DPLASMA D(IS=1e-8 N=1 RS=1)",
               ".model DCLAMP D(IS=1e-12 N=1 RS=2)",
               "VLOGIC logic 0 0"]
    for i in range(1, max(1, count)+1):
        ballast = 19800 if count else 1e12
        dead_clamp = f"Doff{i} out{i} logic DCLAMP" if drive in {"dead", "highz"} else ""
        fixture.extend([
            f"RA{i} hv ta{i} {ballast}", f"VTA{i} ta{i} ti{i} {tube}", f"DT{i} ti{i} tk{i} DPLASMA",
            f"VIAN{i} tk{i} c{i} 0",
            f"VDRV{i} d{i} 0 {volts}", f"ROUT{i} d{i} out{i} {rout}", dead_clamp,
            f"RBASE{i} out{i} b{i} 3000", f"RPD{i} b{i} 0 10000",
            f"VB{i} b{i} bq{i} 0", f"VC{i} c{i} cq{i} 0", f"Q{i} cq{i} bq{i} 0 QPROXY",
            f"RCE{i} c{i} 0 {rce}", f"RCB{i} c{i} b{i} {rcb}",
        ])
    fixture.extend([
        "BVCE vce 0 V=v(c1)", "BVBE vbe 0 V=v(bq1)", "BIB ib 0 V=i(VB1)",
        "BIC ic 0 V=i(VC1)", "BIA ianode 0 V=i(VIAN1)",
        "BPQ pq 0 V=v(c1)*i(VC1)+v(bq1)*i(VB1)",
        f"BPCE pce 0 V=v(c1)*v(c1)/{rce}",
        f"BPCB pcb 0 V=(v(c1)-v(b1))*(v(c1)-v(b1))/{rcb}",
        "BP pdut 0 V=v(pq)+v(pce)+v(pcb)", "BBK eback 0 V=i(VLOGIC)",
        "BIS isupply 0 V=i(VSENSE)", ".tran 2m 4 0 2m uic",
        ".save " + " ".join(COLUMNS[1:]), ".end",
    ])
    return "\n".join(fixture) + "\n"


def stop(variant):
    stop_pwl = ("0 0 0.09999 0 0.1 3.3 0.59999 3.3 0.6 0 0.99999 0 1 3.3"
                if variant != "loop_short" else "0 3.3 4.7 3.3")
    # NC loop closes first. The arm pulses represent fresh clock edges only.
    fault_pwl = "0 0 2.29999 0 2.3 3.3 2.39999 3.3 2.4 0"
    logic_pwl = "0 3.3 3.99999 3.3 4 0 4.09999 0 4.1 3.3"
    early_arm = " 0.04999 0 0.05 3.3 0.05002 3.3 0.05003 0" if variant != "loop_short" else ""
    later_arm = " 0.69999 0 0.7 3.3 0.70002 3.3 0.70003 0" if variant != "loop_short" else ""
    return f"""R14 HV STOP latch and discharge proxy: {variant}
VDD dd 0 PWL({logic_pwl})
VMCU mcu 0 PWL({logic_pwl})
VLOOP contact 0 PWL({stop_pwl})
SLOOP loop 0 contact 0 CTRL
R509 loop gate 220
R510 dd gate 3300
C64 gate 0 1n
Bdet det 0 V=(v(gate)>1.6 ? 3.3 : 0)
SSTOP fault 0 det 0 CTRL
VOTHER other 0 PWL({fault_pwl})
SOTHER fault 0 other 0 CTRL
R27 dd fault 10000
Bclear clr 0 V=(v(fault)<1.3 || v(mcu)<2 ? 3.3 : 0)
SCLR armed 0 clr 0 CTRL
Varm edge 0 PWL(0 0{early_arm}
+ 0.19999 0 0.2 3.3 0.20002 3.3 0.20003 0{later_arm}
+ 1.84999 0 1.85 3.3 1.85002 3.3 1.85003 0
+ 3.64999 0 3.65 3.3 3.65002 3.3 3.65003 0)
Bres res 0 V=(v(hv)<54.92 ? v(dd) : 0)
SARM res armed edge 0 SET
CQ armed 0 1n
RQ armed 0 1T
V5 raw 0 5
S11 raw feed {"raw" if variant == "u11_stuck" else "armed"} 0 CTRL
C28 feed 0 22u
R45 feed 0 10k
Bpermit permit 0 V=(v(armed)>1.2 ? v(dd) : 0)
Boe oe 0 V=(v(permit)>1.2 && v(feed)>2.7 ? 0 : v(dd))
Vboost src 0 195
RSTART permit startup 1k
CSTART startup 0 1u
BSTART boost 0 V=(v(permit)>1.2 && v(startup)>1.2 ? 3.3 : 0)
SBOOST src hv boost 0 CTRL
Dpass feed hv PASS
CHV hv 0 3.63u
RB1 hv 0 500960
RB2 hv 0 {1e15 if variant == "one_bleeder" else 500960}
.model CTRL SW(Ron=1 Roff=1e12 Vt=1.2 Vh=.02)
.model SET SW(Ron=1000 Roff=1e13 Vt=1.2 Vh=.02)
.model PASS D(IS=1e-12 N=1 RS=.1)
.tran 1m 4.7 0 1m
.save v(contact) v(gate) v(fault) v(armed) v(oe) v(permit) v(feed) v(hv) v(res)
.end
"""


def read_raw(path):
    import struct
    header, payload = path.read_bytes().split(b"Binary:\n", 1)
    header = header.decode("ascii", "replace")
    count = int(re.search(r"No. Points:\s+(\d+)", header).group(1))
    names = [m.group(1) for m in re.finditer(r"(?m)^\s*\d+\s+(\S+)\s+\S+$", header)]
    samples = list(struct.iter_unpack("<" + "d" * len(names), payload))
    if len(samples) != count:
        raise ValueError(path)
    return names, samples


def run_case(name, circuit):
    case = OUT / name
    case.mkdir(parents=True, exist_ok=True)
    deck = case / "circuit.cir"
    deck.write_text(circuit, encoding="ascii")
    log = case / "run.log"
    with log.open("wb") as stream:
        subprocess.run([sys.executable, str(DLL_RUN), str(deck)], check=True,
                       stdout=stream, stderr=subprocess.STDOUT, timeout=30)
    names, rows = read_raw(case / "waveform.raw")
    return [dict(zip(names, row)) for row in rows]


def measure_cathode(rows):
    time = [r["time"] for r in rows]
    p = [r["v(pdut)"] for r in rows]
    energy = sum((time[i+1] - time[i]) * (p[i] + p[i+1]) / 2 for i in range(len(p)-1))
    result = {f"peak_abs_{name}": max(abs(r[f"v({name})"]) for r in rows)
              for name in ("hv", "vce", "vbe", "ib", "ic", "ianode", "pq", "pce", "pcb", "pdut", "eback", "isupply")}
    result.update(end_hv_V=rows[-1]["v(hv)"], end_t_s=time[-1], energy_J=energy)
    return result


def measure_stop(rows, name):
    closest = lambda t: min(rows, key=lambda r: abs(r["time"] - t))
    stages = {f"{t:.2f}": closest(t) for t in (.075, .3, .62, .8, 1.02, 1.65, 1.86, 2.31, 2.41, 3.66, 4.02, 4.12, 4.69)}
    if name != "loop_short":
        for idx, level in [("0.62", 0), ("1.02", 0), ("1.65", 0), ("2.31", 0), ("4.02", 0), ("4.12", 0)]:
            assert abs(stages[idx]["v(armed)"] - level) < .05, (name, idx, stages[idx])
        assert stages["0.30"]["v(armed)"] > 2, name
        assert stages["0.62"]["v(oe)"] > 2, name
        assert (stages["1.65"]["v(feed)"] > 4.5) == (name == "u11_stuck"), name
        assert (stages["1.86"]["v(armed)"] > 2) == (name != "one_bleeder"), name
    if name == "loop_short":
        assert stages["0.62"]["v(armed)"] > 2, name
    if name == "nominal":
        assert stages["3.66"]["v(armed)"] > 2, name
    shut = next((r["time"] for r in rows if r["time"] >= .6 and r["v(armed)"] < 1.2), None)
    drop = next((r["time"] for r in rows if r["time"] >= .6 and r["v(hv)"] <= 60), None)
    return {"armed_drop_s": shut, "bus_to_60_s": drop, "stages": stages}


def main():
    OUT.mkdir(exist_ok=True)
    rows = {name: measure_cathode(run_case(name, cathode(cfg))) for name, cfg in CONDITIONS.items()}
    with (OUT / "cathode_measurements.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case", *next(iter(rows.values()))])
        writer.writeheader()
        for name, result in rows.items():
            writer.writerow({"case": name, **result})
    results = {name: measure_stop(run_case(f"stop_{name}", stop(name)), name)
               for name in ("nominal", "one_bleeder", "u11_stuck", "loop_short")}
    (OUT / "stop_measurements.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
