"""Derive auditable CSVs from ngspice traces and the frozen R14 RAW."""
from collections import Counter
import csv
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from run_scan import BALLAST, CAP, FAULT_AT, HERE, area, cases, read_raw, write_csv

EVIDENCE = HERE / "evidence"
LEGACY = HERE.parent / "r14/evidence/simulation/half_195_sustain/waveform.raw"

FAULTS = (
    ("CE_HARD", "semiconductor; ballasted", "ce_hard ce_hard_3",
     "HV_BUS > two 10k > lit tube > collector-emitter bridge > GND",
     "Uncommanded cathode, ballast; channel power varies with glow drop",
     "Ballast contains this current; OE cannot interrupt a conductive bridge"),
    ("CB_HARD", "semiconductor; ballasted", "cb_hard_powered_low cb_hard_powered_high cb_1_0_0_none cb_1_1_0_none cb_1_1_0_block cb_1_1_0_short cb_hard_open_be_max_path cb_block_open_be_reverse_hot_bound",
     "HV_BUS > ballast > tube > C-B > B-E and RP or R100 > 595 OUT > rail/GND",
     "Q1 B-E, R100/R200, U20 output clamp or FET, U2, all 3V3 loads",
     "Reverse diode reduces sustained injection on the downstream path; displacement and diode short remain"),
    ("CE_LEAK", "partial term; ballasted", "ce_partial_10k ce_partial_100k ce_partial_1m",
     "HV_BUS > ballast > tube > resistive C-E path > GND",
     "Ghosting, ballast and fault site; track power does not quantify die hot spot",
     "Ballast reduces energy; total current has a blind region"),
    ("CB_LEAK", "partial term; ballasted", "cb_10000_0_0_none cb_100000_0_0_none cb_1000000_0_0_none cb_zero_tube_100000_25 cb_zero_tube_100000_85",
     "HV_BUS > ballast > tube > C-B leakage > base; active collector current also flows",
     "False turn-on and Q1 linear dissipation; 595/R100 rail path depends on B-E and OE",
     "Reverse diode protects driver path; does not stop BJT self-bias"),
    ("AIR_RESTRIKE_K", "intermittent conductive contact; ballasted", "contact_on_k_ground",
     "Tube cathode > recurrent conductive contact > GND",
     "Intermittent glow and pulsed local energy; unknown arc physics",
     "Ballast and source inhibition reduce follow-on energy"),
    ("SURFACE_TRACKING_KB", "repetitive resistive contact; ballasted", "tracking_k_base_bursts",
     "Tube cathode > local PCB surface > B node > B-E/R200/driver",
     "Local carbonization not modeled; BJT can be driven into linear operation",
     "Spacing and protected routing reduce propagation; time-varying current is not a material model"),
    ("HV_BYPASS_GND", "conductive bridge; unballasted", "contact_bus_ground direct_5ohm_esr_sensitivity",
     "C47/HV_BUS > ESR and bridge > GND",
     "C47, interconnect, local board and power stage; charging current persists while supplied",
     "Initial stored energy is present before detection; physical segregation and bounded source are necessary"),
    ("HV_BYPASS_BASE", "conductive bridge; unballasted", "bypass_bus_base bypass_bus_base_block",
     "C47/HV_BUS > short path > base > Q1 B-E/GND; potential secondary path to 595",
     "Q1 B-E and return conductors; ideal diode does not limit this whole branch",
     "Reverse diode only closes logic-side propagation path when fault lies downstream"),
    ("HV_BYPASS_OUT", "conductive bridge; unballasted", "bypass_bus_out_block bypass_bus_out_5ohm cut_bypass_0_block cut_bypass_0.001_none",
     "C47/HV_BUS > short path > 595 OUT upstream of blocking diode > FET/clamp and rail",
     "595, U2, MCU and shared rails; computed overstress triggers model validity limit",
     "PCB segregation and source inhibition; reverse diode alone cannot cover this location"),
    ("Q_LINEAR", "semiconductor driven; ballasted", "underdrive_one underdrive_three linear_zero_drop_extended cut_linear_0.001 cut_linear_with_blanking",
     "595 intermediate/base path > Q1 conducts with high VCE; anode ballast carries the collector current",
     "Q1 terminal dissipation; actual thermal/SOA unknown at the same VCE and IC",
     "Enforce valid drive and voltage compliance; test SOA before selecting time limit"),
    ("Q_OPEN", "semiconductor open; ballasted", "q_open",
     "Intended cathode current is interrupted; cathode may float",
     "Missing numeral; alternate digits and display sequence may mask it",
     "Command-correlated no-light or current diagnostic only"),
    ("U11_STUCK", "low-voltage input", "stuck_bleed_0 inhibit_bleed_0",
     "5V_PROT > R40 path if ever authorized > stuck U11 > 5V_HV > boost",
     "STOP clears latch and /OE proxy while input remains powered",
     "U18 IN- inhibit reduces boost energy; diode path still couples 5 V into bus"),
    ("HV_STOP", "stored charge", "stop_bleed_0 stop_bleed_1 shutdown_glow",
     "C47 after source stop > redundant 500.96k chains and any remaining load",
     "Residual voltage, open bleed leg, second source and residual-sense faults",
     "Hard latch and explicit ARM; verify residual and both bleed paths"),
)


def scan_rows():
    with (EVIDENCE / "scan_metrics.csv").open(encoding="utf-8", newline="") as file:
        return {r["case"]: r for r in csv.DictReader(file)}


def legacy_audit():
    names, samples = read_raw(LEGACY)
    v = dict(zip(names, zip(*samples)))
    t = v["time"]
    power = {
        "q1_terminal": v["v(pq)"],
        "external_RCE": v["v(pce)"],
        "CB_leakage_proxy": v["v(pcb)"],
        "RA": tuple(i*i*BALLAST for i in v["v(ianode)"]),
        "tube_net": tuple((h-i*BALLAST-c)*i for h,i,c in zip(v["v(hv)"], v["v(ianode)"], v["v(vce)"])),
        "both_bleeders": tuple(h*h/250480 for h in v["v(hv)"]),
        "source": tuple(h*i for h,i in zip(v["v(hv)"],v["v(isupply)"])),
    }
    result = {k: dict(peak_W=max(vals), energy_J=area(t, vals)) for k, vals in power.items()}
    result["capacitance"] = dict(initial_J=CAP*v["v(hv)"][0]**2/2, final_J=CAP*v["v(hv)"][-1]**2/2)
    result["unallocated_average_W"] = (
        result["source"]["energy_J"] - sum(result[k]["energy_J"] for k in power if k != "source")
        - (result["capacitance"]["final_J"] - result["capacitance"]["initial_J"]))/(t[-1]-t[0])
    assert .478 < result["external_RCE"]["peak_W"] < .479
    assert result["q1_terminal"]["peak_W"] < 2e-8
    assert abs(result["unallocated_average_W"]) < 1e-8
    (EVIDENCE / "legacy_power.json").write_text(json.dumps(result, indent=2)+"\n")


def thermal(rows):
    results = []
    for bus in (170, 195):
        for temp in (25, 60, 85):
            for glow in (0, 110, 130, 155):
                subset = [r for r in rows.values() if r["family"] == "thermal" and
                          (int(r["bus_V"]), int(r["ambient_C"]), int(r["tube_drop_V"])) == (bus,temp,glow)]
                r = max(subset, key=lambda r: float(r["q1_steady_max_W"]))
                limit = float(r["steady_screen_W"])
                pq = float(r["q1_steady_max_W"])
                envelope = (bus-glow)**2/(4*BALLAST)
                results.append(dict(ambient_C=temp, hv_bus_V=bus, assumed_glow_V=glow,
                                    math_collector_envelope_W=envelope, datasheet_dc_screen_W=limit,
                                    proxy_q1_steady_W=pq, q1_peak_W=r["q1_peak_W"],
                                    peak_VCE_V=r["q1_peak_VCE_V"], peak_IC_A=r["q1_peak_IC_A"],
                                    peak_VBE_V=r["q1_peak_VBE_V"], peak_IB_A=r["q1_peak_IB_A"],
                                    conditional_Tj_C_at_357=temp+357*pq,
                                    theta_max_for_envelope_K_per_W=(150-temp)/envelope,
                                    q1_E_J=r["q1_E_J"], q1_time_above_screen_s=r["q1_over_screen_s"],
                                    exceeds_steady_screen=pq>limit, case=r["case"],
                                    DC_SOA="UNKNOWN", pulse_SOA="UNKNOWN", transient_Ztheta="UNKNOWN",
                                    path=r["path"]))
    write_csv(HERE / "TRANSISTOR_THERMAL_SOA.csv", results)


def matrix(rows):
    results = []
    for fault, physics, names, current_path, effects, coverage in FAULTS:
        for case in names.split():
            r = rows[case]
            results.append(dict(fault=fault, physics_and_path_class=physics, case=case,
                                conduction_path=current_path, exposed=effects, protection_scope=coverage,
                                q1_peak_W=r["q1_peak_W"], Q1_E_J=r["q1_E_J"],
                                RCE_E_J=r["prce1_J"], RCB_E_J=r["prcb1_J"],
                                RANODE_E_J=r["pra1_J"], RBASE_E_J=r["prbase1_J"],
                                RPULL_E_J=r["prpd1_J"], surface_E_J=r["psurface1_J"],
                                bypass_E_J=r["pbusfault_J"], anode_peak_A=r["total_anode_peak_A"],
                                injected_bus_contact_peak_A=r["external_bypass_peak_A"],
                                logic_clamp_peak_A=r["clamp_peak_A"], logic_rail_peak_V=r["rail_peak_V"],
                                residual_delay_60V_s=r["stop_to_first_60V_s"], path=r["path"]))
    write_csv(HERE / "BREAKDOWN_FAULT_MATRIX.csv", results)


def detection(rows):
    definitions = {c.name: c for c in cases()}
    fault_ids = {
        "ce_hard", "ce_hard_3", "ce_partial_10k", "ce_partial_100k",
        "ce_partial_1m", "tracking_k_base_bursts", "contact_on_k_ground", "contact_bus_ground",
        "bypass_bus_out_block", "bypass_bus_base", "q_open", "underdrive_one", "underdrive_three",
        "linear_zero_drop_extended", "cb_1_0_0_none", "cb_100000_0_0_none",
    }
    comparison = [r for r in rows.values() if r["family"] == "normal" or r["case"] in fault_ids]
    classifiers = ("sum_gt_6mA", "sum_gt_8mA", "sum_gt_10mA", "command_window", "bus_drop")
    counts = {key: Counter(dict(TP=0, FP=0, FN=0, TN=0)) for key in classifiers}
    results = []
    # Each boolean detector requires at least 1 ms continuous predicate time in the replay.
    for row in comparison:
        name = row["case"]
        case = definitions[name]
        with TemporaryDirectory(prefix="r143-") as temp:
            raw = Path(temp) / "waveform.raw"
            raw.write_bytes(gzip.decompress((HERE / row["path"] / "waveform.raw.gz").read_bytes()))
            headers, samples = read_raw(raw)
        v = dict(zip(headers, zip(*samples)))
        currents = [v[f"i(vana{n})"] for n in range(1, case.loads+1)]
        t = v["time"]
        start = .025 if case.supply == "start" else FAULT_AT
        expected_on = name in {"q_open", "underdrive_one", "underdrive_three", "linear_zero_drop_extended"}
        if case.family == "normal":
            expected_on = case.drive == "on"
        tests = [False] * len(classifiers)
        state = [0.] * len(classifiers)
        for i, (a,b) in enumerate(zip(t, t[1:]), 1):
            if a < start:
                continue
            # Ignore 1 ms around modeled display switching edges in the state-aware rule.
            switched = case.drive == "switch"
            requested = (.005 < b < .015) if switched else expected_on
            eligible = (v["v(hv)"][i] > 165 and
                        (not switched or min(abs(b-.005), abs(b-.015)) > .001))
            current = sum(max(x[i],0) for x in currents)
            flags = [current>x for x in (.006,.008,.010)]
            flags += [eligible and (current<.0005 if requested else current>.0003),
                      v["v(hv)"][i]<150]
            for j, flag in enumerate(flags):
                state[j] = state[j]+b-a if flag else 0
                tests[j] |= state[j] >= .001
        actual = name in fault_ids
        result = dict(case=name, labelled_fault=actual, anode_peak_A=row["total_anode_peak_A"],
                      anode_final_A=row["total_anode_final_A"], power_q1_peak_W=row["q1_peak_W"])
        for key, flag in zip(classifiers, tests):
            result[key] = flag
            counts[key][("T" if flag == actual else "F")+("P" if flag else "N")] += 1
        results.append(result)
    write_csv(EVIDENCE / "detector_metrics.csv", results)
    (EVIDENCE / "detector_summary.json").write_text(json.dumps(counts, indent=2)+"\n")


def energy_checks(rows):
    def value(case, key):
        return float(rows[case][key])
    assert math.isclose(value("stop_bleed_0", "stop_to_first_60V_s"),
                        (500960/2)*CAP*math.log(195/60), abs_tol=.002)
    assert not rows["stuck_bleed_0"]["stop_to_first_60V_s"]
    assert value("ce_hard", "q1_peak_W") < .0001
    assert value("cb_1_1_0_block", "rail_final_V") < .01
    assert value("cb_1_1_0_none", "rail_final_V") > 7
    assert value("bypass_bus_out_block", "clamp_peak_A") > .02
    assert value("linear_zero_drop_extended", "q1_steady_max_W") > .45
    assert value("cut_linear_0", "q1_after_stop_J") > .01
    comparisons = {}
    for ref, refined, keys in (
        ("cut_bypass_0.001_none", "cut_bypass_refined", ("external_bypass_peak_A", "pbusfault_J")),
        ("cut_linear_0.001", "cut_linear_refined", ("q1_peak_W", "q1_after_stop_J"))):
        comparisons[ref] = {k: abs(value(ref,k)-value(refined,k))/abs(value(refined,k)) for k in keys}
    max_error = max(abs(float(r["energy_error_J"])) for r in rows.values())
    for values in comparisons.values():
        assert max(values.values()) < .03
    result = dict(case_count=len(rows), max_absolute_electrical_energy_residual_J=max_error,
                  refined_relative_difference=comparisons,
                  stored_energy_195V_J=CAP*195**2/2, stored_energy_60V_J=CAP*60**2/2,
                  stored_energy_170V_J=CAP*170**2/2)
    (EVIDENCE / "energy_audit.json").write_text(json.dumps(result, indent=2)+"\n")


def package_checks(rows):
    expected = {c.name for c in cases()}
    assert rows.keys() == expected
    with (EVIDENCE / "interlock_metrics.csv").open(newline="", encoding="utf-8") as file:
        interlock_names = {row["case"] for row in csv.DictReader(file)}
    for group, names in (("spice", expected), ("interlock", interlock_names)):
        root = EVIDENCE / group
        assert {p.name for p in root.iterdir() if p.is_dir()} == names
        for name in names:
            folder = root / name
            assert {"circuit.cir", "run.log", "case.json", "waveform.raw.gz"} == {
                p.name for p in folder.iterdir() if p.is_file()}
            log = (folder / "run.log").read_text(encoding="ascii", errors="replace").lower()
            assert not any(mark in log for mark in ("run simulation(s) aborted", "error:", "timestep too small"))
    manifest = EVIDENCE / "package_sha256.json"
    files = {path.relative_to(HERE).as_posix(): sha256(path.read_bytes()).hexdigest()
             for path in sorted(EVIDENCE.rglob("*")) if path.is_file() and path != manifest}
    manifest.write_text(json.dumps(dict(electrical=len(expected), interlock=len(interlock_names),
                                        evidence_files=files), indent=2)+"\n")


if __name__ == "__main__":
    rows = scan_rows()
    legacy_audit()
    thermal(rows)
    matrix(rows)
    detection(rows)
    energy_checks(rows)
    package_checks(rows)
    print(f"Legacy attribution, fault matrix, detector replay and energy regression passed ({len(rows)} cases)")
