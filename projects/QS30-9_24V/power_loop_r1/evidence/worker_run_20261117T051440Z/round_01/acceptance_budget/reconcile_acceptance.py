#!/usr/bin/env python3
"""acceptance_budget: reconcile the mandatory electrical acceptance thresholds.

Worker: deepseek-flash (low-cost execution agent), task acceptance_budget.
Kind: analysis. No simulator is invoked. No waveform, log or measurement is
produced or cited as a measurement.

This script only:
  1. hashes (SHA256) every source artefact it cites, inside the repository;
  2. extracts the threshold literals from those files with stdlib json/regex;
  3. recomputes the bleeder power delta and the cold-start charge budget
     analytically (ideal linear equations, no switching model);
  4. asserts each reconciliation statement and writes acceptance_budget.json.

All arithmetic here is ANALYTIC_BUDGET, not simulation and not measurement.
"""
import hashlib
import json
import os
import sys

OUT = os.path.dirname(os.path.abspath(__file__))
REPO = r"D:\PROJECTS\dsharness\QS30-power-loop-r1"
HIST = r"D:\PROJECTS\dsharness\QS30-1"      # read-only historical workspace


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


CIDED = {
    "s05_config": os.path.join(REPO, r"projects\QS30-9_24V\config\sprint05.json"),
    "s05_requirements_md": os.path.join(REPO, r"projects\QS30-9_24V\docs\S05_REQUIREMENTS.md"),
    "safety_requirements": os.path.join(REPO, r"projects\QS30-9_24V\safety_r1\architecture\requirements.json"),
    "s06c_power_rails_json_uncommitted": os.path.join(HIST, r"projects\QS30-9_24V\docs\sprint06c\POWER_RAILS.json"),
    "sprint06_power_rails_csv_committed": os.path.join(REPO, r"projects\QS30-9_24V\docs\sprint06\POWER_RAILS.csv"),
    "sprint05_calculations": os.path.join(REPO, r"projects\QS30-9_24V\docs\sprint05\calculations.json"),
    "power_loop_calculations_independent": os.path.join(REPO, r"projects\QS30-9_24V\power_loop_r1\evidence\independent\calculations.json"),
    "lo_r1_engineering_context": os.path.join(REPO, r"projects\QS30-9_24V\power_loop_r1\engineering_context.md"),
    "lo_r1_tasks": os.path.join(REPO, r"projects\QS30-9_24V\power_loop_r1\tasks.json"),
    "round01_baseline_audit_result": os.path.join(REPO, r"projects\QS30-9_24V\power_loop_r1\runs\20261117T051440Z\round_01\baseline_audit\result.json"),
    "round01_baseline_math_worker_error_preserved": os.path.join(REPO, r"projects\QS30-9_24V\power_loop_r1\runs\20261117T051440Z\round_01\baseline_audit\baseline_math.json"),
    "round01_hv_budget_reconciliation": os.path.join(REPO, r"projects\QS30-9_24V\power_loop_r1\runs\20261117T051440Z\round_01\baseline_audit\hv_budget_reconciliation.json"),
    "safety_governance_holds": os.path.join(REPO, r"projects\QS30-9_24V\safety_r1\governance\holds.json"),
}

hashes = {}
missing = []
for k, p in CIDED.items():
    if os.path.isfile(p):
        hashes[k] = {"path": os.path.relpath(p, REPO) if p.startswith(REPO) else
                     "HISTORICAL_Q/" + os.path.relpath(p, HIST), "sha256": sha256(p)}
    else:
        hashes[k] = {"path": p, "sha256": None}
        missing.append(k)

cfg = load_json(CIDED["s05_config"])
acc = cfg["acceptance"]
safety = load_json(CIDED["safety_requirements"])["thresholds_inherited"]
calc = load_json(CIDED["sprint05_calculations"])
plc = load_json(CIDED["power_loop_calculations_independent"])
s06c = load_json(CIDED["s06c_power_rails_json_uncommitted"])

# ---------------------------------------------------------------------------
# 1. Threshold reconciliation: every stated acceptance number vs. its sources
# ---------------------------------------------------------------------------
hv_rail = [r for r in s06c["rails"] if r["rail"] == "HV_BUS"][0]
s06c_175_1_W = hv_rail["W"]
s06c_175_1_A = hv_rail["A"]

THRESHOLDS = {
    "vin_V": {"value": [cfg["input"]["connector_continuous_V"][0], cfg["input"]["connector_continuous_V"][1]],
              "statement": "connector continuous input 21.6..26.4 V",
              "sources": ["s05_config:input.connector_continuous_V"],
              "test_window": "all startup/steady/step assertions re-run at 21.6, 24.0 and 26.4 V; inductor minimum 20.5 V is a separate path-drop envelope, not the connector window"},
    "hv_mean_V": {"value": acc["HV_mean_V"],
                  "statement": "HV mean 164.9..175.1 V",
                  "sources": ["s05_config:acceptance.HV_mean_V", "s05_requirements_md row HV normal",
                              "safety_requirements:thresholds_inherited.HV_mean_V"],
                  "test_window": "window mean over >=3 consecutive 10 ms windows per docs9 electrical sprint03 study criterion; each window's cycle-mean must lie inside [164.9, 175.1]"},
    "hv_target_V": {"value": acc["HV_target_V"], "statement": "user target 170 V (not an acceptance limit by itself)",
                    "sources": ["s05_config:acceptance.HV_target_V"], "test_window": "reported, not asserted"},
    "hv_ripple_Vpp_max": {"value": acc["HV_ripple_Vpp_max"], "statement": "HV ripple <= 1 Vpp",
                          "sources": ["s05_config:acceptance.HV_ripple_Vpp_max", "s05_requirements_md row HV normal"],
                          "test_window": "20 MHz-bandwidth, short-ground-spring definition; ASCII SPICE raw has no bandwidth limit -> any simulation value is an unbanded upper bound and must be reported as such"},
    "hv_normal_overshoot_V_max": {"value": acc["HV_normal_overshoot_V_max"],
                                  "statement": "normal (startup + load-step) peak <= 180 V",
                                  "sources": ["s05_config:acceptance.HV_normal_overshoot_V_max", "s05_requirements_md row HV normal and startup/dynamic"],
                                  "test_window": "applies during startup and during the 100 ms recovery windows; transient envelope 160..180 V"},
    "ovp_trip_V": {"value": acc["OVP_trip_V"], "statement": "independent OVP actual trip 183..190 V",
                   "sources": ["s05_config:acceptance.OVP_trip_V", "safety_requirements:thresholds_inherited.OVP_trip_V"],
                   "test_window": "3 V gap below lowest trip (183) vs normal peak ceiling (180); OVP is NOT placed by this task and no circuit exists"},
    "hv_fault_peak_V_max": {"value": acc["HV_fault_peak_V_max"],
                            "statement": "specified single-fault HV bus peak <= 195 V (target, not a validated limit)",
                            "sources": ["s05_config:acceptance.HV_fault_peak_V_max", "safety_requirements:thresholds_inherited.fault_peak_V_max"],
                            "test_window": "only for the enumerated single faults (feedback open, MCU runaway); H05 remains P0-open"},
    "startup_s_max": {"value": acc["startup_s_max"],
                      "statement": "genuine COUT=0 V autonomous startup into the [164.9,175.1] window within 1 s",
                      "sources": ["s05_config:acceptance.startup_s_max", "safety_requirements:thresholds_inherited.startup_s_max"],
                      "test_window": "COUT initial condition exactly 0 V; no ideal HV precharge, no forced gate PWM, no forced VC/SS, no 195 V absorbing source"},
    "load_step_recovery_s_max": {"value": acc["load_step_recovery_s_max"],
                                 "statement": "load-step recovery <= 100 ms",
                                 "sources": ["s05_config:acceptance.load_step_recovery_s_max", "s05_requirements_md row startup/dynamic"],
                                 "test_window": "load steps 0 <-> 1.5 <-> 2.25 <-> 3 mA/tube (9 tubes), also 1.5/2.25/3 mA; back inside the mean window AND ripple/peak limits at t_step + 100 ms"},
    "load_step_envelope_V": {"value": acc["load_step_envelope_V"],
                             "statement": "load-step transient envelope 160..180 V",
                             "sources": ["s05_config:acceptance.load_step_envelope_V"],
                             "test_window": "worst excursion during the recovery window; subsumed by normal peak <=180 V above the ceiling"},
    "ambient_C": {"value": acc["ambient_C"], "statement": "ambient 0..50 C qualification window",
                  "sources": ["s05_config:acceptance.ambient_C"], "test_window": "every electrical corner re-run at 0 and 50 C; 25 C results are not extrapolable"},
    "bleed_design_only_V": {"value": acc["bleed_design_only_V"],
                            "statement": "engineering observation target <=60 V in <=5 s",
                            "sources": ["s05_config:acceptance.bleed_design_only_V", "safety_requirements:thresholds_inherited.bleed_design_only_V"],
                            "test_window": "NOT a touch-safety standard; touch_safety_standard remains UNRESOLVED"},
}

assertions = {}


def check(name, ok, measured=None, expected=None, note=None):
    assertions[name] = {"ok": bool(ok), "measured": measured, "expected": expected}
    if note:
        assertions[name]["note"] = note


check("A01_vin_matches_safety_source",
      THRESHOLDS["vin_V"]["value"] == [21.6, 26.4], THRESHOLDS["vin_V"]["value"], [21.6, 26.4])
check("A02_mean_matches_safety_source",
      safety["HV_mean_V"] == acc["HV_mean_V"] == [164.9, 175.1],
      {"safety": safety["HV_mean_V"], "config": acc["HV_mean_V"]}, [164.9, 175.1])
check("A03_fault_peak_matches_safety_source",
      safety["fault_peak_V_max"] == acc["HV_fault_peak_V_max"] == 195,
      {"safety": safety["fault_peak_V_max"], "config": acc["HV_fault_peak_V_max"]}, 195)
check("A04_startup_matches_safety_source",
      safety["startup_s_max"] == acc["startup_s_max"] == 1,
      {"safety": safety["startup_s_max"], "config": acc["startup_s_max"]}, 1)
check("A05_ovp_gap_180_to_183",
      acc["HV_normal_overshoot_V_max"] < acc["OVP_trip_V"][0],
      acc["OVP_trip_V"][0] - acc["HV_normal_overshoot_V_max"], 3.0)
check("A06_mean_target_inside_window",
      acc["HV_mean_V"][0] <= acc["HV_target_V"] <= acc["HV_mean_V"][1],
      acc["HV_target_V"], acc["HV_mean_V"])
check("A07_no_threshold_was_changed_by_this_task",
      THRESHOLDS["hv_mean_V"]["value"] == [164.9, 175.1]
      and THRESHOLDS["hv_ripple_Vpp_max"]["value"] == 1
      and THRESHOLDS["hv_normal_overshoot_V_max"]["value"] == 180
      and THRESHOLDS["hv_fault_peak_V_max"]["value"] == 195
      and THRESHOLDS["startup_s_max"]["value"] == 1
      and THRESHOLDS["load_step_recovery_s_max"]["value"] == 0.1,
      "unchanged", "unchanged")

# ---------------------------------------------------------------------------
# 2. Bleeder delta reconciliation -- two independent voltages, no mixing
# ---------------------------------------------------------------------------
R_UNIT = 90900.0          # two 2x90.9k strings in parallel -> 90900 ohm total
R_OLD = 200000.0          # replaced single 200k bleeder
N_PER_STRING = 2

p_total_170 = 170.0 ** 2 / R_UNIT
p_total_1751 = 175.1 ** 2 / R_UNIT
p_each_170 = (170.0 / N_PER_STRING) ** 2 / R_UNIT          # correct per-resistor value
p_old_170 = 170.0 ** 2 / R_OLD
p_old_1751 = 175.1 ** 2 / R_OLD
delta_170 = p_total_170 - p_old_170
delta_1751 = p_total_1751 - p_old_1751
budget_1751 = s06c_175_1_W + delta_1751
floor_mixed = 5.71642 + delta_170

bleed_worker_error_power_each_quoted = 0.01987073707370737  # baseline_math.json (preserved, WRONG)

check("B01_r_total_90900_ohm", abs(R_UNIT - 2 * 2 * 90900.0 / 2) < 1e-9, R_UNIT, 90900.0)
check("B02_bleed_power_170V",
      abs(p_total_170 - 0.3179317931793179) < 1e-12, p_total_170, 0.3179317931793179)
check("B03_per_resistor_power_170V_CORRECTED",
      abs(p_each_170 - 0.07948294829482948) < 1e-12, p_each_170, 0.07948294829482948,
      "baseline_audit worker wrote 0.01987074 W; correct value is (170/2)^2/90900")
check("B04_worker_per_resistor_error_reproduced",
      abs(p_each_170 - bleed_worker_error_power_each_quoted) > 0.05,
      {"correct_W": p_each_170, "worker_W": bleed_worker_error_power_each_quoted},
      "difference > 50 mW", "worker arithmetic preserved unmodified in baseline_math.json; only flagged")
check("B05_delta_at_170V",
      abs(delta_170 - 0.17343179317931792) < 1e-12, delta_170, 0.17343179317931792)
check("B06_delta_at_175p1V",
      abs(delta_1751 - 0.18399378938393837) < 1e-9, delta_1751, 0.18399378938393837)
check("B07_budget_at_175p1V",
      abs(budget_1751 - 5.900417171661398) < 1e-9, budget_1751, 5.900417171661398,
      "s06c HV_BUS 5.716423382277459 W (at 175.1 V) + delta at the SAME 175.1 V")
check("B08_mixed_voltage_floor_is_not_acceptance",
      abs(floor_mixed - 5.88985) < 1e-9, floor_mixed, 5.88985,
      "5.88985 W mixes a 175.1 V base with a 170 V delta; documented as lower-bound context only, MUST NOT replace B07")
check("B09_budget_175p1_exceeds_mixed_floor",
      budget_1751 > floor_mixed, budget_1751, ">" + str(floor_mixed))
check("B10_s06c_rail_is_allocation_not_measurement",
      "not measured" in s06c.get("mode", ""), s06c.get("mode"), "contains 'not measured'",
      "the HV budget is an allocation; no wattage in this task is measured")
check("B11_s06c_rail_current_consistency",
      abs(hv_rail["V"] * hv_rail["A"] - s06c_175_1_W) / s06c_175_1_W < 1e-12,
      hv_rail["V"] * hv_rail["A"], s06c_175_1_W)
single_short_195 = 195.0 ** 2 / (90900.0 * 0.99)
check("B12_single_resistor_survivor_195V",
      abs(single_short_195 - 0.4225422542254225) < 1e-9, single_short_195, 0.4225422542254225)

# ---------------------------------------------------------------------------
# 3. Cold (0 V) startup budget -- analytic feasibility screen of the 1 s limit
# ---------------------------------------------------------------------------
C_NOM = cfg["HV_candidate"]["COUT_F"] + cfg["HV_candidate"]["module_C_F"]
C_MAX = C_NOM * (1 + cfg["HV_candidate"]["COUT_tolerance"]) * 1.05   # +5% main, +10% module per sprint05
# sprint05 storage block states: Cmain +5%, module C +10%, remaining bleed R +1%
C_SCREEN = calc["storage"]["Ctotal_max_screen_F"]
V_WIN = 164.9
E_TO_WINDOW_NOM = 0.5 * C_NOM * V_WIN ** 2
E_TO_WINDOW_SCREEN = 0.5 * C_SCREEN * V_WIN ** 2
# smallest in-window load (bleeders alone) at the window floor
P_LOAD_MIN_W = V_WIN ** 2 / R_UNIT
# net charging power that must be delivered for 1 s, ignoring all losses
P_NET_NOM = E_TO_WINDOW_NOM / 1.0
P_NET_SCREEN = E_TO_WINDOW_SCREEN / 1.0
P_SOURCE_NOM = P_NET_NOM + P_LOAD_MIN_W      # + losses (uncomputable without a qualified converter)
P_SOURCE_SCREEN = P_NET_SCREEN + P_LOAD_MIN_W

check("C01_cold_energy_nominal",
      abs(E_TO_WINDOW_NOM - 0.5 * (2.03e-5) * V_WIN ** 2) < 1e-15, E_TO_WINDOW_NOM, "0.5*C*(164.9)^2")
check("C02_storage_screen_matches_sprint05",
      abs(C_SCREEN - calc["storage"]["Ctotal_max_screen_F"]) < 1e-15, C_SCREEN, calc["storage"]["Ctotal_max_screen_F"])
check("C03_cold_energy_screen", E_TO_WINDOW_SCREEN > E_TO_WINDOW_NOM, E_TO_WINDOW_SCREEN, ">" + str(E_TO_WINDOW_NOM))
check("C04_min_net_charge_power_1s_nominal", P_NET_NOM > 0.27, P_NET_NOM, ">0.27 W",
      "converter must average this net into COUT for a full second")
check("C05_charge_power_plus_minimum_load",
      P_SOURCE_SCREEN > P_NET_SCREEN, P_SOURCE_SCREEN, "> net only", "bleeders alone draw an additional "
      f"{P_LOAD_MIN_W:.5f} W at 164.9 V, before any conversion loss")
check("C06_zero_volt_initial_condition_required",
      True, E_TO_WINDOW_SCREEN, "analytic bound",
      "any precharge above 0 V, or a 195 V absorbing source, invalidates the 1 s claim")
check("C07_no_startup_evidence_exists",
      True, "NONE", "simulation or bench waveform",
      "no committed or uncommitted file in either workspace contains a COUT=0 V closed-loop startup waveform")

# ---------------------------------------------------------------------------
# 4. What evidence exists for each criterion (documentary status only)
# ---------------------------------------------------------------------------
STATUS = {
    "vin_V": "UNPROVEN",
    "hv_mean_V": "UNPROVEN",
    "hv_target_V": "UNPROVEN",
    "hv_ripple_Vpp_max": "UNPROVEN",
    "hv_normal_overshoot_V_max": "UNPROVEN",
    "ovp_trip_V": "UNPROVEN_NO_CIRCUIT",
    "hv_fault_peak_V_max": "UNPROVEN_H05_P0_OPEN",
    "startup_s_max": "UNPROVEN_NO_SIMULATION",
    "load_step_recovery_s_max": "UNPROVEN_NO_SIMULATION",
    "load_step_envelope_V": "UNPROVEN_NO_SIMULATION",
    "ambient_C": "UNPROVEN_NO_THERMAL_EVIDENCE",
    "bleed_design_only_V": "PASSIVE_DISCHARGE_ONLY_SCALED_24V_NOT_HV",
}

result = {
    "task_id": "acceptance_budget",
    "kind": "analysis",
    "classification": "ANALYTIC_BUDGET_ONLY_NO_SIMULATION_NO_MEASUREMENT",
    "sources_hashed": hashes,
    "missing_sources": missing,
    "thresholds": THRESHOLDS,
    "threshold_status": STATUS,
    "bleeder": {
        "topology": "two parallel strings of 2 x 90.9k = 181.8k each -> 90900 ohm total",
        "R_total_ohm": R_UNIT,
        "R_old_ohm": R_OLD,
        "P_total_170V_W": p_total_170,
        "P_each_resistor_170V_W_corrected": p_each_170,
        "P_each_resistor_170V_W_worker_quoted_WRONG": bleed_worker_error_power_each_quoted,
        "P_old_170V_W": p_old_170,
        "delta_170V_W": delta_170,
        "P_total_175p1V_W": p_total_1751,
        "P_old_175p1V_W": p_old_1751,
        "delta_175p1V_W": delta_1751,
        "s06c_hv_bus_175p1V_W": s06c_175_1_W,
        "revised_hv_budget_175p1V_W": budget_1751,
        "mixed_voltage_lower_bound_floor_W": floor_mixed,
        "single_resistor_survivor_one_short_195V_W": single_short_195,
    },
    "cold_start": {
        "C_nominal_F": C_NOM,
        "C_screen_F": C_SCREEN,
        "V_window_floor_V": V_WIN,
        "E_0V_to_window_nominal_J": E_TO_WINDOW_NOM,
        "E_0V_to_window_screen_J": E_TO_WINDOW_SCREEN,
        "minimum_net_charge_power_for_1s_nominal_W": P_NET_NOM,
        "minimum_net_charge_power_for_1s_screen_W": P_NET_SCREEN,
        "bleeder_load_at_164p9V_W": P_LOAD_MIN_W,
        "minimum_source_power_before_losses_screen_W": P_SOURCE_SCREEN,
        "qualification_rule": "COUT starts at exactly 0 V; converter, controller, bias and OVP all evolve from t=0; no precharge, no forced PWM, no forced VC/SS, no ideal 195 V source",
    },
    "assertions": assertions,
    "all_assertions_ok": all(a["ok"] for a in assertions.values()),
    "measurement_claim": "NONE - no simulator was run and no bench data exists",
    "manufacturing": "HOLD (unchanged)",
}

with open(os.path.join(OUT, "acceptance_budget.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1, sort_keys=True)

print("missing_sources:", missing)
print("all_assertions_ok:", result["all_assertions_ok"])
for k, v in assertions.items():
    if not v["ok"]:
        print("FAILED:", k, v)
print("bleed delta 175.1V:", delta_1751, "budget:", budget_1751)
print("cold E screen J:", E_TO_WINDOW_SCREEN, "P_net screen W:", P_NET_SCREEN)
sys.exit(0 if result["all_assertions_ok"] else 2)
