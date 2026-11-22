"""Run the R14.3 ngspice fault matrix and archive complete sampled traces."""
import argparse
import csv
from dataclasses import asdict, dataclass, replace
import gzip
from itertools import product
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "r14"))
from simulate_faults import read_raw

HERE = Path(__file__).resolve().parent
CAP = 3.63e-6
BASE_R = 3000
BALLAST = 19800
FAULT_AT = .005
OFF = 1e12

CHANNEL = """
Ra{n} hv an{n} {ballast}
Vana{n} an{n} tube{n} 0
Bignition{n} command{n} 0 V=.5+.5*tanh((v(tube{n},k{n})-{strike}+({strike}-{glow}-.12)*v(lit{n}))/.25)
Rstate{n} command{n} lit{n} 10k
Cstate{n} lit{n} 0 2n ic=0
Btube{n} tube{n} k{n} I=v(tube{n},k{n})/1e9+max(v(tube{n},k{n})-{glow}-.35,0)*{lit}/100
Rfloat{n} k{n} 0 1e10
Vup{n} up{n} 0 {up}
Vdown{n} down{n} 0 {down}
Smid{n} middle mdrive{n} {mid_enable} 0 SDRIVE
Vmidmeter{n} mdrive{n} out{n} 0
Sup{n} rail out{n} up{n} 0 SDRIVE
Sdown{n} out{n} 0 down{n} 0 SDRIVE
Vcmon{n} out{n} clamp{n} 0
Dhigh{n} clamp{n} rail DCLAMP
{diode}
Vdrive{n} driven{n} rbase{n} 0
Rbase{n} rbase{n} b{n} {rbase}
Rpd{n} b{n} 0 {rpd}
Rpu{n} b{n} rail {rpu}
Vb{n} b{n} qb{n} 0
Vc{n} k{n} c{n} 0
{transistor}
Rcb{n} k{n} cblink{n} {rcb}
Scb{n} cblink{n} cbmon{n} event 0 SFAULT
Vcbmeter{n} cbmon{n} b{n} 0
Rce{n} k{n} celink{n} {rce}
Sce{n} celink{n} cemon{n} event 0 SFAULT
Vcemeter{n} cemon{n} 0 0
Ssurface{n} k{n} surface{n} {surface_ctrl} 0 SCONTACT
Vsurface{n} surface{n} {surface_to} 0
Bpq{n} pq{n} 0 V=v(c{n})*i(Vc{n})+v(qb{n})*i(Vb{n})
Bpra{n} pra{n} 0 V=v(hv,an{n})*i(Vana{n})
Bptube{n} ptube{n} 0 V=v(tube{n},k{n})*i(Vana{n})
Bprbase{n} prbase{n} 0 V=v(rbase{n},b{n})*i(Vdrive{n})
Bprpd{n} prpd{n} 0 V=v(b{n})^2/{rpd}
Bprcb{n} prcb{n} 0 V=v(k{n},b{n})*i(Vcbmeter{n})
Bprce{n} prce{n} 0 V=v(k{n})*i(Vcemeter{n})
Bpsurface{n} psurface{n} 0 V=v(k{n},surface{n})*i(Vsurface{n})
Bpdiode{n} pdiode{n} 0 V=v(out{n},driven{n})*i(Vdrive{n})
Bpdriver{n} pdriver{n} 0 V=v(rail,out{n})^2/({{50+(1e12-50)*(v(up{n})<.5)}})+v(out{n})^2/({{50+(1e12-50)*(v(down{n})<.5)}})
Bclamp{n} pclamp{n} 0 V=v(out{n},rail)*i(Vcmon{n})+v(out{n})*i(Vlowmeter{n})
Vlowmeter{n} out{n} lower{n} 0
Dreturn{n} 0 lower{n} DCLAMP
Bpmid{n} pmid{n} 0 V=v(middle)*i(Vmidmeter{n})
Bpmidloss{n} pmidloss{n} 0 V=v(middle,mdrive{n})*i(Vmidmeter{n})
Bpleak{n} pleak{n} 0 V=v(k{n})^2/1e10+v(b{n},rail)^2/{rpu}
"""

@dataclass(frozen=True)
class Case:
    name: str
    family: str = "thermal"
    bus: int = 195
    temp: int = 25
    gain: int = 60
    glow: int = 130
    strike: int = 155
    ballast: int = BALLAST
    drive: str = "off"
    middle: float = 0
    loads: int = 1
    ignition: bool = False
    rcb: float = OFF
    rce: float = OFF
    rbase: float = BASE_R
    rpd: int = 10000
    rpu: float = OFF
    diode: str = "none"
    open_q: bool = False
    logic_on: bool = True
    rail_load: int = 10000
    esr: float = .25
    fault_r: float = 10
    surface: str = "none"
    bypass: str = "none"
    supply: str = "sustain"
    stop: float = .005
    source_limit: float = .030
    bleeder_open: bool = False
    end: float = .035
    step: float = .00005


def cases():
    for bus, temp, gain, glow, middle in product(
            (170, 195), (25, 60, 85), (40, 120, 200), (0, 110, 130, 155),
            (.52, .62, .70, .78, .88)):
        yield Case(f"linear_{bus}_{temp}_{gain}_{glow}_{middle:.2f}",
                   bus=bus, temp=temp, gain=gain, glow=glow, drive="mid",
                   middle=middle, end=.012, step=.0002)
    for bus, temp, diode in product((170, 195), (25, 60, 85), ("none", "block")):
        for drive in ("off", "on"):
            yield Case(f"{drive}_{bus}_{temp}_{diode}", bus=bus, temp=temp, drive=drive,
                       diode=diode, family="normal", rpd=4700 if diode == "block" else 10000)
    for glow, strike, loads in product((110, 130, 155), (150, 176), (1, 3)):
        for bus in (170, 195):
            if strike <= glow + 4:
                continue
            yield Case(f"startup_{bus}_{glow}_{strike}_{loads}", family="normal", bus=bus,
                       glow=glow, strike=strike, loads=loads, supply="start", drive="on",
                       ignition=True, end=.060)
    yield Case("normal_display_switch_1", family="normal", drive="switch", ignition=True)
    yield Case("normal_display_switch_3", family="normal", drive="switch", ignition=True, loads=3)
    yield Case("normal_ballast_20200", family="normal", drive="on", ballast=20200)
    yield Case("normal_candidate_high_drop", family="normal", bus=170, temp=85,
               gain=40, drive="on", diode="drop", rpd=4700)
    special = (
        Case("base_drive_open", drive="highz", rbase=OFF),
        Case("base_pull_down_open", drive="highz", rpd=int(OFF)),
        Case("base_pull_up", drive="highz", rpu=33000),
        Case("underdrive_one", glow=110, drive="mid", middle=.78, temp=85, end=.25),
        Case("underdrive_three", glow=110, drive="mid", middle=.78, loads=3, temp=85, end=.25),
        Case("linear_zero_drop_extended", glow=0, drive="mid", middle=.78, gain=200, temp=85,
             end=4, step=.002),
        Case("q_open", open_q=True, drive="on", ignition=True),
        Case("ce_hard", rce=1, ignition=True, end=.25, step=.0002),
        Case("ce_hard_3", rce=1, loads=3, ignition=True, end=.25, step=.0002),
        Case("ce_partial_10k", rce=1e4),
        Case("ce_partial_100k", rce=1e5),
        Case("ce_partial_1m", rce=1e6),
        Case("contact_on_k_ground", surface="ground", fault_r=50, end=.020, step=1e-5),
        Case("tracking_k_base_bursts", surface="base", fault_r=10000, end=.020, step=1e-5),
        Case("contact_bus_ground", bypass="ground", fault_r=10, end=.020, step=1e-6),
        Case("bypass_bus_base", bypass="base", fault_r=100, end=.020, step=2e-6),
        Case("bypass_bus_base_block", bypass="base", fault_r=100, diode="block", end=.020, step=2e-6),
        Case("bypass_bus_out_block", bypass="out", fault_r=100, diode="block", end=.020, step=2e-6),
        Case("bypass_bus_out_5ohm", bypass="out", fault_r=5, end=.012, step=5e-7),
        Case("legacy_topology_thermal", rce=BALLAST, glow=0, end=4, step=.002),
    )
    for case in special:
        yield replace(case, family="fault")
    for rcb, open_q in product((1, 10000, 100000, 1000000), (False, True)):
        for logic, diode in product((True, False), ("none", "block", "short")):
            yield Case(f"cb_{rcb}_{int(open_q)}_{int(logic)}_{diode}", family="fault",
                       rcb=rcb, open_q=open_q, logic_on=logic, drive="highz",
                       diode=diode, rpd=4700 if diode != "none" else 10000,
                       rail_load=1000 if diode != "none" else 10000,
                       end=.10, step=.0001)
    yield Case("cb_hard_powered_low", family="fault", rcb=1, drive="off")
    yield Case("cb_hard_powered_high", family="fault", rcb=1, drive="on")
    yield Case("cb_hard_open_be_max_path", family="fault", rcb=1, glow=0, open_q=True,
               drive="highz", logic_on=False, end=.5, step=.0002)
    yield Case("cb_block_open_be_reverse_hot_bound", family="fault", rcb=1, glow=0, open_q=True,
               temp=85, diode="leakmax", rpd=4700, rail_load=1000, drive="highz",
               logic_on=False, end=.5, step=.0002)
    for supply, bleed in product(("stop", "stuck", "inhibit"), (False, True)):
        yield Case(f"{supply}_bleed_{int(bleed)}", family="stop", supply=supply,
                   drive="off", bleeder_open=bleed, end=5, step=.001)
    for delay in (0, .0001, .001, .01):
        for diode in ("none", "block"):
            yield Case(f"cut_bypass_{delay:g}_{diode}", family="stop",
                       supply="stop", stop=FAULT_AT+delay, bypass="out", fault_r=100,
                       diode=diode, end=.040, step=2e-6)
        yield Case(f"cut_linear_{delay:g}", family="stop", supply="stop",
                   stop=FAULT_AT+delay, drive="midfault", middle=.78, glow=0, gain=200,
                   temp=85, end=.5, step=.0001)
    yield Case("direct_5ohm_esr_sensitivity", family="fault", bypass="ground", fault_r=5,
               esr=2, end=.012, step=1e-6)
    yield Case("cut_bypass_refined", family="stop", supply="stop", stop=.006,
               bypass="out", fault_r=100, end=.040, step=1e-6)
    yield Case("cut_linear_refined", family="stop", supply="stop", stop=.006,
               drive="midfault", middle=.78, glow=0, gain=200, temp=85, end=.5, step=.00005)
    for resistance in (10000, 100000, 1000000):
        for temp in (25, 85):
            yield Case(f"cb_zero_tube_{resistance}_{temp}", family="fault", rcb=resistance,
                       glow=0, temp=temp, drive="off")
    yield Case("cut_linear_with_blanking", family="stop", supply="stop", stop=.006,
               drive="midblank", middle=.78, glow=0, gain=200, temp=85, end=.5, step=.0001)
    yield Case("shutdown_glow", family="stop", supply="stop", drive="on", ignition=True,
               end=2, step=.0005)


def channel(case, n):
    up, down = {"off": (0, 1), "on": (1, 0), "mid": (0, 0), "highz": (0, 0),
                "midfault": (0, 0), "midblank": (0, 0),
                "switch": ("PWL(0 0 5m 0 5.001m 1 15m 1 15.001m 0)", 0)}[case.drive]
    if not case.logic_on:
        up, down = 0, 0
    diode = {
        "none": f"Vlink{n} out{n} driven{n} 0",
        "block": f"Dblock{n} out{n} driven{n} DBLOCK",
        "drop": f"Dblock{n} out{n} d_internal{n} DBLOCK\nVextra{n} d_internal{n} driven{n} .45",
        "short": f"Rblock{n} out{n} driven{n} .01",
        "leakmax": f"Dblock{n} out{n} driven{n} DBLOCK\n"
                   f"Bleakmax{n} driven{n} out{n} I=200u*min(max(v(driven{n},out{n})/.1,0),1)",
    }[case.diode]
    transistor = f"Q{n} c{n} qb{n} 0 QPROXY"
    if case.open_q:
        transistor = f"Rqopen{n} c{n} 0 1e12\nRbopen{n} qb{n} 0 1e12"
    return CHANNEL.format(n=n, ballast=case.ballast, glow=case.glow, up=up, down=down,
                          mid_enable="miden" if case.drive.startswith("mid") else "0", diode=diode,
                          rbase=case.rbase, rpu=case.rpu, rpd=case.rpd, transistor=transistor,
                          rcb=case.rcb, rce=case.rce,
                          strike=case.strike, lit=f"v(lit{n})" if case.ignition else "1",
                          surface_ctrl="bursts" if case.surface != "none" and n == 1 else "0",
                          surface_to=f"b{n}" if case.surface == "base" else "0")


POWERS = ("pq", "pra", "ptube", "prbase", "prpd", "prcb", "prce", "psurface", "pdiode",
          "pdriver", "pclamp", "pmidloss", "pleak")
SINGLE = ("v(hv)", "v(hcap)", "v(rail)", "i(vfeed)", "i(vreg)", "i(vbusfault)",
          "v(hvpower)", "v(lvpower)", "v(pbleed)", "v(pcaploss)", "v(pbusfault)", "v(prail)")
PER_CHANNEL = ("v(c{n})", "i(vc{n})", "v(qb{n})", "i(vb{n})", "i(vana{n})", "v(out{n})",
               "i(vcmon{n})", "i(vdrive{n})", "i(vsurface{n})", "v(pmid{n})")


def deck(case):
    initial = case.bus
    target = case.bus
    if case.supply == "start":
        initial, target = 0, f"PWL(0 0 .02 {case.bus})"
    if case.supply in ("stop", "inhibit"):
        residual = 4.4 if case.supply == "inhibit" else 0
        target = f"PWL(0 {case.bus} {case.stop} {case.bus} {case.stop+1e-6} {residual})"
    bypass = {"none": "0", "ground": "0", "base": "b1", "out": "out1"}[case.bypass]
    event = "PWL(0 0 4.999m 0 5m 1)"
    vectors = list(SINGLE)
    for n in range(1, case.loads+1):
        vectors.extend(item.format(n=n) for item in PER_CHANNEL)
        vectors.extend(f"v({name}{n})" for name in POWERS)
    mid_enable = "1"
    if case.drive == "midfault":
        mid_enable = event
    if case.drive == "midblank":
        mid_enable = f"PWL(0 0 4.999m 0 5m 1 {case.stop} 1 {case.stop+1e-6} 0)"
    lines = [f"Vmiden miden 0 {mid_enable}", "Vbursts bursts 0 PULSE(0 1 5m 1u 1u 1m 4m)"]
    lines.extend(channel(case, n) for n in range(1, case.loads+1))
    # Preserve a real OFF branch for topology accounting without loading the bus.
    if case.bypass == "none":
        lines.append("Vnever never 0 0")
    template = (HERE / "cathode.cir.in").read_text()
    result = template.format(**asdict(case), initial=initial, target=target, event=event,
                             regulator=3.3 if case.logic_on else 0,
                             rail_initial=3.3 if case.logic_on else 0,
                             bleed2=OFF if case.bleeder_open else 500960,
                             bypass_node=bypass,
                             channels="\n".join(lines), vectors=" ".join(vectors))
    if case.bypass == "none":
        result = result.replace("hv faultto event", "hv faultto never")
    return result


def area(t, values):
    return sum((b-a)*(x+y)/2 for a,b,x,y in zip(t, t[1:], values, values[1:]))


def time_above(t, values, limit):
    duration = 0
    for a, b, x, y in zip(t, t[1:], values, values[1:]):
        if x > limit and y > limit:
            duration += b-a
        elif (x > limit) != (y > limit):
            duration += (b-a)*(max(x, y)-limit)/abs(y-x)
    return duration


def analyze(raw, case):
    headers, samples = read_raw(raw)
    columns = dict(zip(headers, zip(*samples)))
    t = columns["time"]
    if t[-1] < case.end * .99999:
        raise ValueError(f"{case.name} stopped at {t[-1]}")
    expected_cap = 0 if case.supply == "start" else case.bus
    if abs(columns["v(hcap)"][0] - expected_cap) > .05:
        raise ValueError(f"{case.name}: incorrect initial capacitor voltage")
    expected_rail = 3.3 if case.logic_on else 0
    if abs(columns["v(rail)"][0] - expected_rail) > .05:
        raise ValueError(f"{case.name}: incorrect initial logic voltage")
    n = range(1, case.loads+1)
    power = {key: area(t, columns[key]) for key in columns
             if key.startswith(("v(p", "v(hvpower)", "v(lvpower)"))}
    total_supply = power["v(hvpower)"] + power["v(lvpower)"] + sum(power[f"v(pmid{i})"] for i in n)
    losses = sum(value for key, value in power.items()
                 if key not in ("v(hvpower)", "v(lvpower)") and not re.fullmatch(r"v\(pmid\d+\)", key))
    hv_cap = [CAP * v*v / 2 for v in columns["v(hcap)"]]
    lv_cap = [10e-6 * v*v / 2 for v in columns["v(rail)"]]
    delta_storage = hv_cap[-1] - hv_cap[0] + lv_cap[-1] - lv_cap[0]
    error = total_supply - losses - delta_storage
    if abs(error) > 5e-5 + .01*max(abs(total_supply), abs(losses), abs(delta_storage)):
        raise ValueError(f"{case.name} energy mismatch {error:.6g} J")
    limit = min(.350, (150-case.temp)/357)
    anodes = [sum(max(columns[f"i(vana{i})"][k], 0) for i in n) for k in range(len(t))]
    q1 = columns["v(pq1)"]
    peak = max(range(len(t)), key=q1.__getitem__)
    settled = [value for time, value in zip(t, q1) if time >= .8*case.end]
    st = next((i for i, time in enumerate(t) if time >= case.stop), len(t)-1)
    fault_st = next(i for i, time in enumerate(t) if time >= FAULT_AT-1e-12)
    confirm = next((t[i] - case.stop for i in range(st, len(t))
                    if columns["v(hv)"][i] <= 60), None) if case.supply in ("stop", "inhibit", "stuck") else None
    result = dict(case=case.name, family=case.family, bus_V=case.bus,
                  ambient_C=case.temp, BF=case.gain, tube_drop_V=case.glow,
                  drive_V=case.middle, lasts_s=t[-1], points=len(t),
                  steady_screen_W=limit, q1_peak_W=q1[peak], q1_peak_at_s=t[peak],
                  q1_steady_max_W=max(settled), q1_over_screen_s=time_above(t, q1, limit),
                  q1_E_J=power["v(pq1)"], q1_peak_VCE_V=columns["v(c1)"][peak],
                  q1_peak_IC_A=columns["i(vc1)"][peak], q1_peak_VBE_V=columns["v(qb1)"][peak],
                  q1_peak_IB_A=columns["i(vb1)"][peak], max_q_other_W=max(
                      (max(columns[f"v(pq{i})"]) for i in range(2, case.loads+1)), default=0),
                  total_anode_peak_A=max(anodes), total_anode_final_A=anodes[-1],
                  hv_source_peak_A=max(columns["i(vfeed)"]), rail_peak_V=max(columns["v(rail)"]),
                  rail_final_V=columns["v(rail)"][-1], logic_pin_peak_V=max(columns["v(out1)"]),
                  clamp_peak_A=max(0, max(columns["i(vcmon1)"])), reverse_drive_peak_A=max(0, -min(columns["i(vdrive1)"])),
                  rail_injected_J=sum(area(t, [max(i, 0)*v for i,v in
                                            zip(columns[f"i(vcmon{j})"], columns["v(rail)"])]) for j in n),
                  external_bypass_peak_A=max(columns["i(vbusfault)"]),
                  hv_final_V=columns["v(hv)"][-1], cap_at_stop_J=hv_cap[st],
                  cap_last_J=hv_cap[-1], stop_to_first_60V_s=confirm, energy_error_J=error,
                  hv_fed_before_stop_J=area(t[:st+1], columns["v(hvpower)"][:st+1]),
                  hv_fed_after_stop_J=area(t[st:], columns["v(hvpower)"][st:]),
                  bypass_after_stop_J=area(t[st:], columns["v(pbusfault)"][st:]),
                  fault_before_stop_J=area(t[fault_st:st+1], columns["v(pbusfault)"][fault_st:st+1]),
                  q1_after_stop_J=area(t[st:], q1[st:]),
                  q1_fault_before_stop_J=area(t[fault_st:st+1], q1[fault_st:st+1]),
                  path=f"evidence/spice/{case.name}/")
    result.update({f"{key[2:-1]}_J": value for key, value in power.items()})
    return result


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(dict.fromkeys(key for row in rows for key in row)) if fields is None else fields,
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_case(spice, root, case):
    out = root / case.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "case.json").write_text(json.dumps(asdict(case), indent=2)+"\n")
    (out / "circuit.cir").write_text(deck(case), encoding="ascii", newline="\n")
    raw = out / "waveform.raw"
    raw.unlink(missing_ok=True)
    command = [str(spice), "-n", "-b", "circuit.cir"]
    with (out / "run.log").open("wb") as log:
        run = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT,
                             timeout=45, check=False)
    if run.returncode or not raw.exists():
        raise RuntimeError(f"ngspice exit {run.returncode}, see {out / 'run.log'}")
    result = analyze(raw, case)
    (out / "waveform.raw.gz").write_bytes(gzip.compress(raw.read_bytes(), mtime=0))
    raw.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--out", type=Path, default=HERE / "evidence")
    parser.add_argument("--only", default=".*", help="regular expression applied to case IDs")
    args = parser.parse_args()
    chosen = [case for case in cases() if re.search(args.only, case.name)]
    if not chosen:
        parser.error("no matching cases")
    rows = []
    for case in chosen:
        # Keep all waveforms for this task. Split output roots for partial/debug runs.
        rows.append(run_case(args.ngspice, args.out / "spice", case))
    write_csv(args.out / "scan_metrics.csv", rows)
    print(f"{len(rows)} ngspice cases completed; energy-balance assertions passed")


if __name__ == "__main__":
    main()
