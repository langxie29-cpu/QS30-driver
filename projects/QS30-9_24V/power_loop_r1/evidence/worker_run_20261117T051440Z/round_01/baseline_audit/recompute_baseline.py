"""Independent recomputation of the 24V baseline numbers quoted in the run context.

Checks:
  B1. Bleeder topology: two parallel strings of 2 x 90.9k -> 181.8k each.
  B2. 170V mainboard bleed power for revised bleeders.
  B3. Old single 200k bleeder power at 170V, and the delta.
  B4. S06C HV budget + delta.

All arithmetic only; no simulator involved. Results written to baseline_math.json.
"""
import json
import os

RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"
V = 170.0
R_UNIT = 90_900.0       # 90.9k per resistor, from bleeder_revision.csv
N_SERIES = 2            # 2 x 90.9k per string
N_PARALLEL = 2          # two parallel strings (A and B)
R_OLD = 200_000.0

r_string = N_SERIES * R_UNIT
r_total = r_string / N_PARALLEL
p_new = V ** 2 / r_total
p_old = V ** 2 / R_OLD
delta = p_new - p_old

s06c_hv = 5.71642
s06c_updated = s06c_hv + delta

out = {
    "inputs": {
        "V_hv_nominal_V": V,
        "R_unit_ohm": R_UNIT,
        "series_per_string": N_SERIES,
        "parallel_strings": N_PARALLEL,
        "R_old_ohm": R_OLD,
        "s06c_hv_budget_W": s06c_hv,
    },
    "derived": {
        "R_per_string_ohm": r_string,
        "R_total_ohm": r_total,
        "P_new_total_W": p_new,
        "P_per_string_W": (V ** 2 / r_string),
        "P_per_unit_W": (V / (N_SERIES * N_PARALLEL)) ** 2 / R_UNIT,
        "P_old_single_200k_W": p_old,
        "delta_W": delta,
        "s06c_hv_plus_delta_W": s06c_updated,
    },
    "assertions": {},
}

# Vendor-context quoted values (from engineering_context.md) — compare, do not adjust.
assertions = out["assertions"]
assertions["R_per_string_eq_181.8k"] = {
    "expected": 181_800.0,
    "measured": r_string,
    "ok": abs(r_string - 181_800.0) < 1e-6,
}
assertions["P_new_eq_0.31793W"] = {
    "expected": 0.31793,
    "measured": round(p_new, 5),
    "ok": abs(round(p_new, 5) - 0.31793) < 5e-6,
}
assertions["P_old_eq_0.1445W"] = {
    "expected": 0.1445,
    "measured": round(p_old, 4),
    "ok": abs(round(p_old, 4) - 0.1445) < 5e-5,
}
assertions["delta_eq_0.17343W"] = {
    "expected": 0.17343,
    "measured": round(delta, 5),
    "ok": abs(round(delta, 5) - 0.17343) < 5e-6,
}
assertions["s06c_updated_ge_5.88985W"] = {
    "expected_floor": 5.88985,
    "measured": round(s06c_updated, 5),
    "ok": round(s06c_updated, 5) >= 5.88985 - 1e-9,
}
assertions["all_ok"] = all(v["ok"] for v in assertions.values() if isinstance(v, dict))

with open(os.path.join(RUN, "baseline_math.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
