"""Consolidate the S06C/D/E/F claim register with explicit provenance labels.

Every row carries: claim, source file, provenance (COMMITTED / UNCOMMITTED),
the source's own stated verdict, and this auditor's classification.
No claim is upgraded; UNCOMMITTED claims are NOT promoted to PASS.
"""
import hashlib
import json
import os

H = r"D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V"
R = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V"
RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"


def sha256(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(base, rel):
    p = os.path.join(base, rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        try:
            return json.load(f)
        except Exception:
            return None


CLAIMS = [
    # (id, sprint, claim, file(relative to historical), key extraction, provenance)
    ("C01", "S06C", "HV_BUS rail allocation 5.71642 W at 175.1 V",
     "docs/sprint06c/POWER_RAILS.json", ("rails", "HV_BUS", "W")),
    ("C02", "S06C", "Bleeder/rail budget basis is an allocation, not a measurement",
     "docs/sprint06c/POWER_RAILS.json", ("mode",)),
    ("C03", "S06C", "LT3757A+ST forced-CS gate cell nominal PASS",
     "docs/sprint06c/NOMINAL_GATE_QUALIFICATION.json", ("pairs",)),
    ("C04", "S06C", "S06C overall status is preservation + scoped unit review, NOT release",
     "docs/sprint06c/final_verification.json", ("status",)),
    ("C05", "S06D", "Real sampling cell still NOT qualified; 0.5->0.25 ns refinement failed",
     "docs/sprint06d/final_verification.json", ("electrical_qualification",)),
    ("C06", "S06D", "Original gear 0.5ns VGS_min / SENSE_peak",
     "docs/sprint06d/observer_control.json", ("cases", "original_gear_0.5ns")),
    ("C07", "S06D", "Original gear 0.25ns VGS_min / SENSE_peak (refinement divergence)",
     "docs/sprint06d/observer_control.json", ("cases", "original_gear_0.25ns")),
    ("C08", "S06E", "Complete comparisons FAIL convergence; SENSE cross-method delta 5.476 mV > 5 mV",
     "docs/sprint06e/final_verification.json", ("research_complete_comparisons",)),
    ("C09", "S06F", "Diode commutation fixture: original vs TT0 both fail/not comparable",
     "docs/sprint06f/diode_unit_results.json", ("cases",)),
    ("C10", "S06F", "TT intervention inconclusive; late-event history divergence",
     "docs/sprint06f/final_verification.json", ("research_comparisons",)),
    ("C11", "S06F", "195V ideal source served ~10.317 uJ in one window (not an absorber only)",
     "docs/SPRINT06F_REPORT.md", ("TEXT",)),
]

STATUS_KEYS = ["24V_07", "24V_08", "manufacturing", "native_generated", "ERC_DRC"]


def dig(obj, path):
    cur = obj
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def main():
    rows = []
    for cid, sprint, claim, rel, path in CLAIMS:
        p = os.path.join(H, rel)
        exists = os.path.exists(p)
        rec = {"id": cid, "sprint": sprint, "claim": claim,
               "source_path": "QS30-1/" + rel, "source_exists": exists,
               "provenance": "UNCOMMITTED",
               "sha256": sha256(p)}
        if not exists:
            rec["value"] = None
            rec["error"] = "SOURCE MISSING"
            rows.append(rec)
            continue
        if path[0] == "TEXT":
            rec["value"] = "see source text"
            rows.append(rec)
            continue
        d = load(H, rel)
        rec["value"] = dig(d, path) if d is not None else None
        rows.append(rec)

    # Per-sprint status block: identical in all four UNCOMMITTED final_verification files.
    status = {}
    for s in ("sprint06c", "sprint06d", "sprint06e", "sprint06f"):
        d = load(H, "docs/%s/final_verification.json" % s)
        if d:
            status[s] = {k: d.get(k) for k in STATUS_KEYS if k in d}

    # Committed counterpart status (S06B, last committed sprint).
    committed = {}
    for s in ("sprint06", "sprint06b"):
        d = load(R, "docs/%s/final_verification.json" % s)
        if d:
            committed[s] = {k: d.get(k) for k in STATUS_KEYS if k in d}

    safety = {}
    d = load(R, "safety_r1/verification/verification_summary.json")
    if d:
        safety = {k: d.get(k) for k in
                  ("24V_07", "24V_08", "24V_09", "24V_10", "manufacturing")}

    out = {"claims": rows,
           "uncommitted_sprint_status": status,
           "committed_sprint_status": committed,
           "safety_r1_status": safety,
           "interpretation": (
               "All four S06C-F sprints are UNCOMMITTED in the historical workspace "
               "and uniformly self-report 24V-07 NOT_PASSED, 24V-08 NOT_ENTERED, "
               "manufacturing HOLD. safety_r1 (committed) additionally reports "
               "24V-09 and 24V-10 NOT_PASSED with the same HOLD.")}
    with open(os.path.join(RUN, "claim_register.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
