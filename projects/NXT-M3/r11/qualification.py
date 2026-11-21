"""Build qualification tables and independently check saved raw evidence."""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
INPUT = HERE/"evidence/r2"
FINAL = HERE/"evidence/r5"
BOOK = {
    "dnp_open": ("R40 open, 5 V boundary", "HV remains below 1 V with link open"),
    "nominal": ("5 V, 7.65 mA", "165–175 V at 28–30 ms; ripple <= 1 V"),
    "maxload": ("5 V, 9.9 mA", "nominal screen"),
    "lowline": ("4.4 V, 9.9 mA", "nominal screen"),
    "highline": ("5.5 V, 7.65 mA", "nominal screen"),
    "noload": ("5 V, zero tube load, passive bleeders present", "nominal screen"),
    "light": ("5 V, 2.55 mA", "nominal screen"),
    "load_step": ("5 V, 7.65 to 9.9 mA at 21 ms", "nominal screen by 28 ms"),
    "line_step": ("5→4.4→5.5 V, 7.65 mA", "nominal screen by 28 ms; interim behavior separate"),
    "restart": ("5 V, 7.65 mA, ARM off 15–20 ms", "nominal screen by 30 ms; exploratory window"),
    "cutoff": ("170 V initial, 5.5 V downstream path", "distinguish PWM-off from imposed input opening"),
    "residual": ("195 V, 3.63 uF, worst bleeders", "evaluate t60 and transient/sustained Q dissipation"),
    "thresholds": ("external 0→200 V and 140 mV sense ramp", "nominal OVP/OCP/residual threshold arithmetic"),
    "cathode_drive": ("3.3 V / 165 ohm source, 27 C", "3.3 mA nominal branch with bounded forced beta"),
    "cathode_hot_weak": ("2.27 V source / BF 25, 85 C", "run weak-source countercase; verify actual part separately"),
    "ovp_feedback_fault": ("5 V, normal load, feedback shunt at 18 ms", "OVP threshold crossing plus independent cutoff"),
    "ovp_feedback_fault_r4": ("5 V, normal load, feedback shunt at 18 ms", "record latch directly if threshold crossed"),
    "ovp_feedback_fault_noload": ("5 V, empty load, feedback shunt at 18 ms", "trip and bus peak below 195 V in proxy"),
    "ocp_sense_fault": ("5 V, current-sense stimulus at 18 ms", "trip observation, instrumented in R4"),
    "ocp_sense_fault_r4": ("5 V, imposed 150 mV sense at 18 ms", "trip and latch response with proxy"),
    "layout_10nh": ("5 V, 7.65 mA, 10 nH switch branch", "screen peak sensitivity"),
    "layout_50nh": ("5 V, 7.65 mA, 50 nH switch branch", "screen peak sensitivity"),
}


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)


def classify(name, item):
    if item["exit"] != 0 or not item["raw_points"]:
        return "UNKNOWN", "INCONCLUSIVE: simulator/model did not complete"
    if name in {"lowline","restart","residual"}:
        return "REWORK", "Regulation or sustained-power closure remains open"
    if name in {"ovp_feedback_fault","ovp_feedback_fault_r4"}:
        return "REWORK", "Nominal-loaded trace never crossed comparator threshold in 30 ms"
    if name == "ocp_sense_fault":
        return "UNKNOWN", "R2 trace lacks direct trip instrumentation; see R4 rerun"
    return "LIMITED_PASS", "Measured behavior applies to the selected proxy and window"


def cases():
    cases_by_name = {}
    rows = []
    for path in sorted(INPUT.glob("*/measurement.json")):
        item = json.loads(path.read_text())
        name = item["case"]
        raw = path.parent/"waveform.raw"
        if item["raw_points"]:
            digest = hashlib.sha256()
            with raw.open("rb") as stream:
                while chunk := stream.read(1048576):
                    digest.update(chunk)
            assert digest.hexdigest() == item["waveform_sha256"], name
            wave = json.loads((path.parent/"waveform_metrics.json").read_text())
            assert wave["samples"] == item["raw_points"]
            if "hv_final" in item["measurements"]:
                assert abs(wave["bus_initial_v"]) < 1e-6 and abs(wave["last_s"]-.03) < 1e-8
        else:
            assert not item["waveform_sha256"]
            wave = {}
        status, decision = classify(name,item)
        item["engineering_status"] = status
        item["postprocessed"] = wave
        cases_by_name[name] = item
        condition, acceptance = BOOK.get(name, ("5 V, zero-energy startup", "completed TI transient model"))
        followup = ("Validate actual power path, model fidelity, component tolerances and PCB behavior"
                    if name not in {"residual","cathode_drive","cathode_hot_weak"} else
                    "Review actual hot leakage, SOA, thermal impedance, access interlock and fault isolation")
        rows.append((name,condition,acceptance,item["model"]," ".join(item["command"]),
                     path.parent.relative_to(HERE).as_posix(),item["exit"],item["seconds"],item["raw_points"],
                     json.dumps(item["measurements"],sort_keys=True),json.dumps(wave,sort_keys=True),
                     status,decision,followup))
    assert cases_by_name["nominal"]["measurements"]["hv_final"] > 165
    assert cases_by_name["lowline"]["measurements"]["hv_final"] < 165
    assert cases_by_name["ovp_feedback_fault_noload"]["measurements"]["trip_time"] > .018
    assert cases_by_name["ocp_sense_fault_r4"]["measurements"]["trip_time"] > .018
    write_csv(HERE/"POWER_QUALIFICATION_MATRIX.csv", (
        "case","condition","screening_criterion","model","command","evidence_folder","exit_status",
        "execution_seconds","raw_samples","spice_measurements","waveform_calculations",
        "status","interpretation","bench_validation"),rows)
    return cases_by_name


def mapping():
    with (HERE.parent/"r10/COMPONENT_FOOTPRINT_MAP.csv").open(encoding="utf-8-sig",newline="") as stream:
        source = list(csv.DictReader(stream))
    groups = {
        "U11":("S11","yes","28 mΩ switch with imposed enable; omits slew limiter, dynamic reverse blocking, thermal","Supply-path sensitivity"),
        "U16":("S16 / B_BCTL","yes","TPS61040 timing and feedback proxy; internal peak limit and EN behavior absent","Bias/permission sequencing"),
        "U17":("LM5155-Q1_TRANS / B_GM, S_SET, S_LRST","mixed","TI Q1 Rev H attempted with LM51551=0; all native attempts invalid; functional 100 kHz current-mode proxy","Closed-loop screening with preserved passives"),
        "U18":("S18_H, S18_L","yes","Finite RON gate switches; UVLO, delay variation and supply transfer absent","Switching stress screen"),
        "U12":("VREF","yes","Fixed 1.25 V; no tolerance or fail-low hold","Nominal protection thresholds"),
        "U13":("B_RAW, B_O, B_C","yes","Comparator/RC proxy; no certified latency or power sequencing","Modeled threshold/cutoff"),
        "U14":("residual and bias divider crossings","yes","BIAS_OK proxy; residual monitor voltage only; fail-low and common cause open","Nominal thresholds"),
        "U8":("C_LATCH_A, S_KILL","yes","Interlock approximation; no digital clock, enable or supply-loss proof","Fault latch surrogate"),
        "U9":("B_ARMED","yes","Proxy fault clear gating; no 3.3 V loss-state verification","Fault latch surrogate"),
        "U15":("B_PERMIT","yes","BIAS_OK and ARMED as analog gating; no ramp qualification","Bias gate"),
        "Q32":("M32 ST_PROXY","yes","Level-1 model with assumed capacitances/RDS; no breakdown or thermal network","Switch stress bounds"),
        "D3":("ES1G_PROXY","yes","Generic recovery, capacitance and forward I-V","Reverse spike/current sensitivity"),
        "D2":("SS14_PROXY","yes","Generic Schottky model","Bias charging"),
        "C47":("C47, RESR","mixed","3.3 uF nominal or 3.63 uF discharge; 25 mΩ screen, no ESL","Stored energy/ripple"),
        "L3":("L3, RLD","mixed","22 uH, 39.5 mΩ; no saturation/core loss","Inductor and sense stress"),
        "L2":("L2","mixed","10 uH ideal; no saturation","Bias buildup"),
        "R40":("R40","mixed","Native DNP. 1 mΩ populated equivalent for converter screen, 1 TΩ for open-link case","DNP and populated sensitivity"),
        "U3":("Vin GPIO and active logic levels","yes","Boundary sources only","Logic and back-power screen"),
        "U24":("unmodeled","yes","Native Ioff UART buffer remains outside cathode clamp test","UART requalification"),
        "U6":("unmodeled","yes","No buffer-specific direction, offset or rail loss model","OLED bus requalification"),
        "U5":("unmodeled","yes","OLED load switch QOD timing not modeled","OLED rail requalification"),
        "U1":("V5 upstream boundary","yes","Front switch/fuse/TVS/buck not solved with boost; crest inrush not valid","Power-path boundary only"),
        "U2":("V33 / Crail","yes","No buck regulation/load dynamics; open-loop capacitive bound","3.3 V rail screen")
    }
    passive = {"C28","C31","C35","C36",*(f"C{i}" for i in range(37,49)),
               "R45",*(f"R{i}" for i in range(47,54)),*(f"R{i}" for i in range(60,70)),
               *(f"R{i}" for i in range(70,87)),*(f"R{i}" for i in range(400,408))}
    rows = []
    for part in source:
        ref = part["ref"]
        group = groups.get(ref)
        if ref in passive and not group:
            group = (ref,"no","Nominal ideal passives; tolerance parasitics only as noted in decks","Circuit topology")
        if re.fullmatch(r"U2[0-3]",ref):
            group = ("VOUT / RDRV","yes","Output equivalent and 30-channel current bound; no 3.3 V VOH/IOH guarantee","Digital drive")
        if re.fullmatch(r"Q([1-9]|[12][0-9]|30)",ref):
            group = ("NPN_BOUND / equivalent resistance","yes","Generic BJT and half-on resistance sweep points; no vendor SOA","Per-channel sensitivity")
        if re.fullmatch(r"R[12][0-2][0-9]",ref):
            group = ("RBASE or RPD","no","3 kΩ / 10 kΩ tolerance; representative per-channel fixture","Drive margin")
        if re.fullmatch(r"R30[2-7]",ref):
            group = ("R1, R2 / Rfa, Rfb","mixed","Tubes as 7.65/9.9 mA aggregate for converter; two 10 kΩ resistors in cathode fixture","Load and fault")
        if re.fullmatch(r"V[123]",ref):
            group = ("BLOAD / VSTRIKE","yes","Current envelope with extinction ramp or fixed arc offset; no reignition dynamics","Load sensitivity")
        if group:
            model,proxy,difference,scope = group
            datasheet = part["datasheet"] or "R10 schematic value"
            if ref == "C47":
                datasheet = "https://product.tdk.com/system/files/dam/doc/product/capacitor/film/mkp_mfp/data_sheet/20/20/ds/mkp_b32774m_778m.pdf"
            rows.append((ref,part["mpn"],part["value"],model,datasheet,
                         proxy,difference,scope))
    write_csv(HERE/"SCHEMATIC_TO_SIMULATION_MAP.csv",
              ("reference","MPN","schematic_value","spice_model","model_source_or_part_datasheet",
               "proxy","difference","scope"), rows)


def stress(data):
    cases = [name for name, r in data.items() if "q_vds" in r["measurements"]]
    quantities = (
        ("L3","il_peak","A","Inductor saturation and thermal loss not modeled"),
        ("Q32","q_vds","V","50 nH case is sensitivity, not extracted"),
        ("Q32","q_current","A","Confirm pulse SOA, no validated avalanche"),
        ("D3","d_if","A","Check forward pulse rating and recovery across temperature"),
        ("D3","d_irev","A","Generic diode recovery, sign retained"),
        ("C47","cap_rms","A","Check vendor frequency/temperature ripple and pulse"),
        ("C47","cap_charge","A","Check actual dV/dt and film part model"),
        ("C47","cap_discharge","A","Check actual dV/dt and film part model"),
        ("Q32","q_loss","W","Electrical device-proxy estimate only"),
        ("D3","d_loss","W","Electrical device-proxy estimate only"),
        ("L3","l_copper","W","Missing core loss"),
        ("R73","sense_loss","W","Verify shunt heating and Kelvin layout"),
        ("R73","cs_peak","V","Verify real shunt and independent/cycle threshold"))
    rows = [(ref,metric,data[name]["measurements"][metric],unit,name,note)
            for ref,metric,unit,note in quantities for name in cases]
    for name in cases:
        row = data[name]["postprocessed"]
        rows.extend([("D3","reverse_voltage",row["diode_reverse_peak_v"],"V",name,"Computed from raw samples"),
                     ("U11","input_peak_after_1ms",row["input_peak_after_1ms_a"],"A",name,"Idealized inrush excluded")])
    rows.extend([("C47","stored_energy",.5*c*v*v,"J","analytic",f"{c*1e6:g} uF, {v} V")
                 for c in (3.3e-6,3.63e-6) for v in (170,195)])
    m = data["residual"]["measurements"]
    rows.extend([("Q1-Q30",field,m[field],unit,"residual","Zero tube drop / 19.8 kΩ half-on proxy")
                 for field,unit in (("fault_vce","V"),("fault_ic","A"),("fault_w","W"),
                                    ("fault_energy","J"),("sustained_w","W"),("sustained_energy","J"))])
    write_csv(HERE/"COMPONENT_STRESS_REVIEW.csv",("reference","quantity","value","unit","case","review"),rows)


def main():
    data = cases()
    mapping()
    stress(data)
    drc = json.loads((FINAL/"DRC.json").read_text(encoding="utf-8-sig"))
    priority = Counter()
    issues = []
    for issue in [*drc["violations"],*drc["unconnected_items"],*drc["schematic_parity"]]:
        level = "P1"
        kind = issue["type"]
        desc = issue["description"]
        if kind == "missing_footprint" or (kind=="clearance" and
             any(text in desc for text in ("HV bus", "Switch node"))):
            level = "P0"
        elif kind == "silk_edge_clearance":
            level = "P2"
        priority[level] += 1
        issues.append((level,kind,issue["severity"],desc,
                       " | ".join(x["description"] for x in issue["items"])))
    write_csv(FINAL/"DRC_TRIAGE.csv",("priority","native_type","native_severity","description","items"),issues)
    residual = data["residual"]["measurements"]
    for valid,bleed in ((residual["dual_t60"],500960/2),(residual["single_t60"],500960)):
        assert math.isclose(valid,bleed*3.63e-6*math.log(195/60),rel_tol=1e-4)
    assert math.isclose(residual["fault_w"],195**2/(4*19800),rel_tol=1e-4)
    report = {"cases":len(data), "completed_waveforms":sum(bool(x["raw_points"]) for x in data.values()),
              "case_statuses":dict(Counter(x["engineering_status"] for x in data.values())),
              "r2_case_keys": [n for n in data if not (n.endswith("_r4") or n.startswith("layout_") or n.endswith("_noload"))],
              "drc_and_parity_triage_counts":dict(priority), "checked_local_raw_sha256":True,
              "residual_and_half_on_recalculated":True, "gate_0":"REWORK", "manufacturing_release":"HOLD"}
    (FINAL/"qualification_review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()

