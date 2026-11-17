"""Record SHA256 of every artefact this audit cites, from BOTH workspaces.

Read-only over sources; writes only into OUTPUT_DIR.
"""
import hashlib
import json
import os

H = r"D:/PROJECTS/dsharness/QS30-1"
R = r"D:/PROJECTS/dsharness/QS30-power-loop-r1"
RUN = os.path.join(R, "projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit")

# (workspace, relative path)
CITED = [
    # --- prospective repo (worktree) : committed baseline ---
    ("R", "projects/QS30-9_24V/README.md"),
    ("R", "projects/QS30-9_24V/docs/S06C_PLAN.md"),
    ("R", "projects/QS30-9_24V/docs/S06_CIRCUIT_DELTA.md"),
    ("R", "projects/QS30-9_24V/docs/SPRINT06_REPORT.md"),
    ("R", "projects/QS30-9_24V/docs/SPRINT06B_REPORT.md"),
    ("R", "projects/QS30-9_24V/docs/sprint06c/input_snapshot.json"),
    ("R", "projects/QS30-9_24V/docs/TASKS.csv"),
    ("R", "projects/QS30-9_24V/docs/sprint06/POWER_RAILS.csv"),
    ("R", "projects/QS30-9_24V/docs/sprint06/MODEL_QUALIFICATION.csv"),
    ("R", "projects/QS30-9_24V/docs/sprint06/final_verification.json"),
    ("R", "projects/QS30-9_24V/docs/sprint06b/final_verification.json"),
    ("R", "projects/QS30-9_24V/docs/sprint06b/MODEL_SOURCE_MATRIX.md"),
    # --- safety_r1 (committed) ---
    ("R", "projects/QS30-9_24V/safety_r1/README.md"),
    ("R", "projects/QS30-9_24V/safety_r1/governance/BASELINE.md"),
    ("R", "projects/QS30-9_24V/safety_r1/governance/holds.json"),
    ("R", "projects/QS30-9_24V/safety_r1/circuit/bleeder_revision.csv"),
    ("R", "projects/QS30-9_24V/safety_r1/circuit/BLEED_REVISION.md"),
    ("R", "projects/QS30-9_24V/safety_r1/architecture/requirements.json"),
    ("R", "projects/QS30-9_24V/safety_r1/verification/verification_summary.json"),
    ("R", "projects/QS30-9_24V/safety_r1/verification/VERIFICATION_REPORT.md"),
    ("R", "HOLD_REGISTER9.md"),
    # --- prospective repo uncommitted run scaffolding ---
    ("R", "projects/QS30-9_24V/power_loop_r1/engineering_context.md"),
    ("R", "projects/QS30-9_24V/power_loop_r1/tasks.json"),
    # --- historical workspace: UNCOMMITTED S06C-F reports/evidence ---
    ("H", "projects/QS30-9_24V/docs/SPRINT06C_REPORT.md"),
    ("H", "projects/QS30-9_24V/docs/SPRINT06D_REPORT.md"),
    ("H", "projects/QS30-9_24V/docs/SPRINT06E_REPORT.md"),
    ("H", "projects/QS30-9_24V/docs/SPRINT06F_REPORT.md"),
    ("H", "projects/QS30-9_24V/docs/S06C_INTERFACE_CANDIDATES.md"),
    ("H", "projects/QS30-9_24V/docs/S06D_PLAN.md"),
    ("H", "projects/QS30-9_24V/docs/S06E_PLAN.md"),
    ("H", "projects/QS30-9_24V/docs/S06F_PLAN.md"),
    ("H", "projects/QS30-9_24V/docs/BREAKPOINT_S06C_2026-11-15.md"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/POWER_RAILS.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/NEW_CONTROLLER_CORNERS.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/NOMINAL_GATE_QUALIFICATION.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/CURRENT_CELL_REVIEW.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/VISHAY_QG_REVIEW.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/candidate_analysis.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06c/final_verification.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06d/final_verification.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06d/observer_control.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06d/edge_audit.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06e/final_verification.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06e/analysis.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06f/final_verification.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06f/analysis.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06f/diode_unit_results.json"),
    ("H", "projects/QS30-9_24V/docs/sprint06f/baseline_0p25_preliminary.json"),
    # --- historical: vendor SPICE model bytes (must stay immutable) ---
    ("H", "projects/QS30-9_24V/sources/sprint06b/ST_model_cn/unpacked/stp9nk50z.lib"),
    ("H", "projects/QS30-9_24V/sources/sprint06b/Vishay_US1G/us1g.txt"),
    ("H", "projects/QS30-9_24V/sources/sprint06/UCCx8C43_unencrypted/unpacked/UCC28C43_PSPICE_TRANS_UNENCR_18FEB2016/ucc28c43_trans_unencrypted.lib"),
    ("H", "projects/QS30-9_24V/sources/sprint06/UCC28C43_pspice/unpacked/UCC28C43_PSPICE_07NOV2008/UCC28C43_PSPICE_TRANS/ucc28c43.lib"),
    ("H", "projects/QS30-9_24V/sources/sprint06/UCC28C43_startup/unpacked/UCC28C43_TINA_TRANS/UCC28C43_START.LIB"),
    ("H", "projects/QS30-9_24V/sources/sprint06/UCC28C43_pspice/UCC28C43_pspice.zip"),
    # --- LTspice native distribution ---
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspice.exe"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/lib.zip"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/examples.zip"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/License.txt"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/License.pdf"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspiceChangeLog.txt"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspice.json"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/LTspice64.msi"),
    ("H", "projects/QS30-9_24V/toolchain/ltspice26/source.json"),
    # --- ngspice ---
    ("H", "tools/ngspice47/Spice64/bin/ngspice_con.exe"),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    rows = []
    for ws, rel in CITED:
        base = H if ws == "H" else R
        p = os.path.join(base, rel).replace("\\", "/")
        rec = {"workspace": "HISTORICAL_QS30-1" if ws == "H" else "QS30-power-loop-r1",
               "path": rel}
        if os.path.exists(p):
            rec["sha256"] = sha256(p)
            rec["size"] = os.path.getsize(p)
        else:
            rec["sha256"] = None
            rec["size"] = None
            rec["error"] = "MISSING"
        rows.append(rec)
    with open(os.path.join(RUN, "cited_artifact_hashes.json"), "w", encoding="utf-8") as f:
        json.dump({"algorithm": "sha256", "files": rows}, f, indent=1)
    lines = []
    for r in rows:
        lines.append("%s  %-12s %s" % (r["sha256"] or "MISSING",
                                       r["workspace"][:12], r["path"]))
    with open(os.path.join(RUN, "cited_artifact_hashes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
