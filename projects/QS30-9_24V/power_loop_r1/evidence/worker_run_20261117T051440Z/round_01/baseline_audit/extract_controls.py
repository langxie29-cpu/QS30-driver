"""Extract the baseline / control-variant table data from committed + uncommitted sources.

Reads (read-only):
  * QS30-1 historical workspace docs/sprint06{c,d,e,f}/*.json  (UNCOMMITTED)
  * QS30-1 historical workspace config/sprint06{c,d,e,f}.json   (UNCOMMITTED)
Emits control_variants.json: one row per control variant with its provenance
label and the qualification string exactly as the source states it.
No value is invented; every field records where it came from.
"""
import hashlib
import json
import os

H = r"D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V"
RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"


def sha256(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(rel):
    p = os.path.join(H, rel)
    if not os.path.exists(p):
        return None, None
    with open(p, encoding="utf-8", errors="replace") as f:
        return json.load(f), sha256(p)


def main():
    out = {"rows": [], "sources": {}}
    pr = load("docs/sprint06c/POWER_RAILS.json")
    out["sources"]["POWER_RAILS.json"] = pr[1]
    rails = {r["rail"]: r for r in pr[0]["rails"]} if pr[0] else {}

    ncg = load("docs/sprint06c/NEW_CONTROLLER_CORNERS.json")
    out["sources"]["NEW_CONTROLLER_CORNERS.json"] = ncg[1]
    ngq = load("docs/sprint06c/NOMINAL_GATE_QUALIFICATION.json")
    out["sources"]["NOMINAL_GATE_QUALIFICATION.json"] = ngq[1]
    oc = load("docs/sprint06d/observer_control.json")
    out["sources"]["observer_control.json"] = oc[1]
    f_an = load("docs/sprint06f/analysis.json")
    out["sources"]["s06f/analysis.json"] = f_an[1]
    f_pre = load("docs/sprint06f/prestate_trajectory.json")
    out["sources"]["s06f/prestate_trajectory.json"] = f_pre[1]
    f_prelim = load("docs/sprint06f/baseline_0p25_preliminary.json")
    out["sources"]["s06f/baseline_0p25_preliminary.json"] = f_prelim[1]

    # Baseline HV rail (the "5.71642 W" figure) — UNCOMMITTED S06C power rail.
    hv = rails.get("HV_BUS", {})
    out["hv_bus_rail"] = {
        "rail": "HV_BUS", "V": hv.get("V"), "A": hv.get("A"), "W": hv.get("W"),
        "provenance": "UNCOMMITTED docs/sprint06c/POWER_RAILS.json",
        "note": "evaluated at 175.1 V (upper acceptance bound), not 170 V",
    }

    # Control variants actually exercised in S06C: LT3757A candidate vs original TI UCC28C43 linkage.
    rows = []

    def add(**kw):
        rows.append(kw)

    add(ref="BASELINE_S06C_LT3757A_CS_GATE_CELL",
        variant="LT3757AIMSE#PBF native model + original-byte ST STP9NK50Z",
        evidence="docs/sprint06c/NOMINAL_GATE_QUALIFICATION.json",
        provenance="UNCOMMITTED",
        qualification="PASS_NOMINAL_FORCED_CS_GATE_CELL_ONLY",
        scope="forced CS gate cell, 25C, AUX12/12.6V, resistor-load unit",
        caveat="forced gate / resistor unit; NOT closed loop, NOT startup, NOT power stage")

    for e in (pr[0].get("rails") or []):
        add(ref="RAIL_" + e["rail"], variant=e["rail"],
            evidence="docs/sprint06c/POWER_RAILS.json", provenance="UNCOMMITTED",
            qualification="ALLOCATION_NOT_MEASURED",
            value={"V": e.get("V"), "A": e.get("A"), "W": e.get("W")},
            scope=e.get("mode", "allocations not measured"))

    # S06D controls (the real sampling cell failure evidence)
    if oc[0]:
        for c in oc[0].get("cases", []):
            add(ref="S06D_" + c["name"],
                variant="original topology, %s ns maxstep, rc=%s" % (c.get("maxstep_ns"), c.get("rc")),
                evidence="docs/sprint06d/observer_control.json",
                provenance="UNCOMMITTED",
                qualification=c.get("execution"),
                scope="execution only; electrical NOT_PASSED",
                value={k: c.get(k) for k in
                       ("VGS_min_V", "VGS_max_V", "SENSE_peak_V", "gate_peak_A",
                        "IL_peak_A", "snubber_mean_W")})

    payload = {"rows": rows, "sources": out["sources"], "hv_bus_rail": out["hv_bus_rail"]}
    # Also dump the raw structures needed for the markdown table.
    payload["new_controller_corners"] = ncg[0]
    payload["nominal_gate_qualification"] = ngq[0]
    payload["s06f_prestate"] = f_pre[0]
    payload["s06f_preliminary"] = f_prelim[0]
    with open(os.path.join(RUN, "control_variants_raw.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)


if __name__ == "__main__":
    main()
