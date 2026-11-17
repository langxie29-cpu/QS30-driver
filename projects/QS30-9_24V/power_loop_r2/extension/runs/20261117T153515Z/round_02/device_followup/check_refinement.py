"""device_followup -- refinement-delta check (CODE ONLY; NOT executed by this worker).

Scope: ROUND3_REVIEW.md final task for `device_followup`. Reads ONLY committed
principal evidence (read-only, outside this directory):
  * energy_refinement.json  -- principal record of the 10ps/5ps minimum-cell runs
  * 10ps/st.lib, 5ps/st.lib -- the ORIGINAL STMicroelectronics STP9NK50Z model text
  * 10ps/circuit.cir, 5ps/circuit.cir, 10ps/preregister.json -- provenance/tolerances

It computes, with numpy only, the RELATIVE CHANGE 10ps -> 5ps of
shunt_peak_A, sense_peak_V and Qnegative_DREC_C taken from the actual rows, and
confirms the package inductances LS/LD in st.lib. It is not a simulator: no
solver, shell, network, job or model call. Output is a single JSON written next
to this script (own directory only); no source evidence is mutated.

NO AUTOMATIC SIGN-OFF: status is reported as a worker claim only and the net
inductor-energy identity stays FAIL (see below).
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np

DN = Path(__file__).resolve().parent
R2 = Path("D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2")
EV = R2 / "evidence" / "principal" / "minimum_energy_refine"
TOL_L = 1e-15          # H, exact-match tolerance for the declared package values
TOL_REL = 1e-12        # dimensionless, float-rounding guard on the re-derived deltas

SCALARS = ("shunt_peak_A", "sense_peak_V", "Qnegative_DREC_C")
asserts = {}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def package_L(lib_path):
    """Parse the STP9NK50Z subckt: LG/LS/LD are the ONLY package inductances."""
    text = lib_path.read_bytes().decode("latin-1")      # file itself never written
    ind = {}
    for name, n1, n2, val in re.findall(
            r"(?im)^\s*(LG|LS|LD)\s+(\S+)\s+(\S+)\s+([0-9.]+[eE][+-]?[0-9]+)", text):
        ind[name] = dict(n1=n1, n2=n2, H=float(val))
    mos = re.search(r"(?im)^\s*MOS\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+MOS\b", text)
    assert set(ind) == {"LG", "LS", "LD"}, f"unexpected package-L set {sorted(ind)}"
    return dict(
        inductors=ind, mos_internal_nodes=dict(drain=mos.group(1), gate=mos.group(2), source=mos.group(3)),
        LS_7p5n=bool(np.isclose(ind["LS"]["H"], 7.5e-9, rtol=0.0, atol=TOL_L)),
        LD_4p5n=bool(np.isclose(ind["LD"]["H"], 4.5e-9, rtol=0.0, atol=TOL_L)),
        LS_node_span=f"{ind['LS']['n1']}-{ind['LS']['n2']} (intrinsic source -> Source pin/3)",
        LD_node_span=f"{ind['LD']['n1']}-{ind['LD']['n2']} (intrinsic drain -> Drain pin/1)",
        file=str(lib_path), sha256=sha(lib_path))


rows = json.loads((EV / "energy_refinement.json").read_text(encoding="utf8"))
by_case = {r["case"]: r for r in rows}
assert "10ps" in by_case and "5ps" in by_case, f"missing cases in {sorted(by_case)}"
a, b = by_case["10ps"], by_case["5ps"]
assert a["window_s"] == b["window_s"], "10ps/5ps windows differ -- not a matched cell"
ma, mb = a["metrics"], b["metrics"]

# v5 - v10 and (v5 - v10)/|v10|; both derived from the rows, nothing typed in.
delta = {}
for k in SCALARS:
    v10, v5 = np.float64(ma[k]), np.float64(mb[k])
    delta[k] = dict(v_10ps=float(v10), v_5ps=float(v5), change_5ps_minus_10ps=float(v5 - v10),
                    rel_change=float((v5 - v10) / np.abs(v10)),
                    rel_change_pct=float(100.0 * (v5 - v10) / np.abs(v10)))
# Re-derive the relative change from the printed percent to catch transcription drift.
for k in SCALARS:
    assert np.isclose(delta[k]["rel_change"] * 100.0, delta[k]["rel_change_pct"], rtol=TOL_REL,
                      atol=0.0)
asserts["matched_window_and_monotone_in_points"] = bool(a["points"] < b["points"])

# Net inductor-energy identity: residual/|net| stays near O(1) at BOTH gears.
resid = {g: {L: r["metrics"][L]["relative_to_net"] for L in ("LS", "LD")} for g, r in (("10ps", a), ("5ps", b))}
identity_fail = bool(all(v >= 0.4 for d in resid.values() for v in d.values()))
asserts["net_energy_identity_FAIL"] = identity_fail
converged = {L: np.abs(resid["5ps"][L] - resid["10ps"][L]) for L in ("LS", "LD")}
asserts["residual_not_converging_to_zero"] = bool(all(c > 0.03 for c in converged.values()))

pk = package_L(EV / "5ps" / "st.lib")
pk10 = package_L(EV / "10ps" / "st.lib")
asserts["st_lib_identical_10ps_5ps"] = pk["sha256"] == pk10["sha256"]
asserts["LS_7p5n_AND_LD_4p5n_confirmed_in_st_lib"] = bool(pk["LS_7p5n"] and pk["LD_4p5n"])

reg = json.loads((EV / "10ps" / "preregister.json").read_text(encoding="utf8"))
net_hashes = {}
for g in ("10ps", "5ps"):
    cir = EV / g / "circuit.cir"
    net_hashes[g] = dict(sha256=sha(cir),
                         tran=next(ln for ln in cir.read_text(encoding="utf8").splitlines()
                                   if ln.strip().startswith(".tran")))
# Only maxstep (and its run) separates the pair: .tran start/stop/UIC must match.
tr = {g: net_hashes[g]["tran"].split() for g in net_hashes}
asserts["tran_differs_only_in_step"] = bool(
    tr["10ps"][0] == tr["5ps"][0] == ".tran" and tr["10ps"][2] == tr["5ps"][2]
    and tr["10ps"][3] == tr["5ps"][3] and tr["10ps"][5] == tr["5ps"][5]
    and tr["10ps"][1] != tr["5ps"][1] and tr["10ps"][4] != tr["5ps"][4])

OUT = dict(
    task="device_followup", kind="analysis", scope="ROUND3_REVIEW.md final task; code only",
    executed_by_worker=False,
    source_control=dict(source=str(EV / "energy_refinement.json"), sha256=sha(EV / "energy_refinement.json"),
                        window_s=a["window_s"], points_10ps=a["points"], points_5ps=b["points"],
                        note="Emitted so the principal can confirm on one run that the LS/LD package "
                             "inductances in st.lib are exactly the LS=7.5n / LD=4.5n assumed by the "
                             "committed energy identity."),
    relative_change=dict(delta,
                         formula="(v_5ps - v_10ps)/abs(v_10ps); both values from energy_refinement.json"),
    package_inductance=pk,
    net_energy_identity=dict(
        FAIL=identity_fail, relative_to_net=resid, abs_difference_5ps_minus_10ps=converged,
        LS_J=dict(v10=ma["LS"]["residual_J"], v5=mb["LS"]["residual_J"]),
        LD_J=dict(v10=ma["LD"]["residual_J"], v5=mb["LD"]["residual_J"]),
        statement="Discrete .5*L*i^2 identity remains FAIL at 10ps and 5ps; refining maxstep did "
                  "NOT drive the residual to zero. Cause NOT established here."),
    lt_default_loss_reference=dict(
        claim="LTspice inductors carry a DEFAULT series resistance of 1 mohm when Rser is not "
              "declared (schematic/engine default), which can inject a resistive branch into a "
              "voltage-vs-stored-energy identity.",
        status="NOT PROVEN -- cited only; not validated here and NOT used to explain the residual.",
        why_not_usable="st.lib package inductances LG/LS/LD declare no Rser and the ideal .5Li^2 "
                       "identity ignores any such series loss; no LTspice documentation, manual "
                       "run or model test was performed by this worker."),
    netlists=net_hashes, preregister_solver=reg.get("solver"), preregister_tolerances=reg.get("options"),
    assertions=asserts,
    worker_claim="WorkerPASS = evidence delivery only. No model/physics/hardware sign-off, no "
                 "threshold change, no HOLD change. Net energy identity recorded as FAIL.",
    solver="none (arithmetic over committed JSON/lib text; no simulator invoked)",
    caveats=[
        "relative changes are diagnostics of numerical reproducibility of a local cell, not a device qualification",
        "10ps and 5ps rows come from the principal's committed record; this worker did not verify the raws",
        "st.lib is not UTF-8; it was parsed as latin-1 and never modified (hash recorded)",
    ],
)
(DN / "refinement_check.json").write_text(json.dumps(OUT, indent=2) + "\n", encoding="utf8")
print(json.dumps(dict(assertions=asserts, rel_change={k: v["rel_change"] for k, v in delta.items()}), indent=1))
