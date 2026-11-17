"""Reconcile the two HV_BUS power figures and evaluate the bleeder delta interaction.

  COMMITTED   docs/sprint06/POWER_RAILS.csv   HV_BUS 5.71560370189665 W (@175.1 V)
  UNCOMMITTED docs/sprint06c/POWER_RAILS.json HV_BUS 5.716423382277459 W (@175.1 V)

The run context quotes "S06C updated HV budget 5.71642W" which is the UNCOMMITTED
value. Both are evaluated at 175.1 V, NOT 170 V. The +0.17343 W bleeder delta is
a separate mainboard allocation, so the resulting HV budget depends on which base
is adopted. This script states both, and does not choose one.
"""
import csv
import json
import os

R = r"D:/PROJECTS/dsharness/QS30-power-loop-r1"
H = r"D:/PROJECTS/dsharness/QS30-1"
RUN = os.path.join(R, "projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit")

COMMITTED_CSV = os.path.join(R, "projects/QS30-9_24V/docs/sprint06/POWER_RAILS.csv")
UNCOMMITTED_JSON = os.path.join(H, "projects/QS30-9_24V/docs/sprint06c/POWER_RAILS.json")

DELTA = 170.0 ** 2 / (2 * 90900.0 / 2) - 170.0 ** 2 / 200000.0  # 0.17343179317931792


def main():
    with open(COMMITTED_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    c_hv = next(r for r in rows if r["rail"].strip() == "HV_BUS")
    committed_w = float(c_hv["P_W"])

    with open(UNCOMMITTED_JSON, encoding="utf-8") as f:
        u = json.load(f)
    u_hv = next(r for r in u["rails"] if r["rail"] == "HV_BUS")
    uncommitted_w = u_hv["W"]

    out = {
        "quantities_evaluated_at_V": 175.1,
        "note": "Neither figure is at 170 V; both use the 175.1 V upper acceptance bound.",
        "hv_bus_committed": {
            "value_W": committed_w,
            "formatted_W": round(committed_w, 5),
            "source": "COMMITTED projects/QS30-9_24V/docs/sprint06/POWER_RAILS.csv",
            "V": float(c_hv["V_V"]), "A": float(c_hv["I_A"]),
        },
        "hv_bus_uncommitted_s06c": {
            "value_W": uncommitted_w,
            "formatted_W": round(uncommitted_w, 5),
            "source": "UNCOMMITTED QS30-1 docs/sprint06c/POWER_RAILS.json",
            "V": u_hv["V"], "A": u_hv["A"],
        },
        "s06c_minus_committed_W": uncommitted_w - committed_w,
        "bleeder_delta_W": DELTA,
        "context_claim_5p71642_is": "UNCOMMITTED S06C value rounded to 5 dp",
        "context_claim_matches_uncommitted": abs(round(uncommitted_w, 5) - 5.71642) < 5e-6,
        "context_claim_matches_committed": abs(round(committed_w, 5) - 5.71642) < 5e-6,
        "updated_budget_if_committed_base": round(committed_w + DELTA, 5),
        "updated_budget_if_uncommitted_base": round(uncommitted_w + DELTA, 5),
        "context_states_floor_5p88985": 5.88985,
        "assertions": {},
    }
    a = out["assertions"]
    a["committed_base_plus_delta_ge_floor"] = {
        "measured": round(committed_w + DELTA, 5),
        "floor": 5.88985,
        "ok": round(committed_w + DELTA, 5) >= 5.88985,
    }
    a["uncommitted_base_plus_delta_ge_floor"] = {
        "measured": round(uncommitted_w + DELTA, 5),
        "floor": 5.88985,
        "ok": round(uncommitted_w + DELTA, 5) >= 5.88985,
    }
    a["context_5p71642_traces_to_uncommitted"] = out["context_claim_matches_uncommitted"]
    a["context_5p71642_does_NOT_trace_to_committed"] = not out["context_claim_matches_committed"]

    with open(os.path.join(RUN, "hv_budget_reconciliation.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
