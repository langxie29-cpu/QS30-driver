"""Run R14.6 independent evidence reviews via the existing sealed Harness."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "r13"))
from orchestrate import engine, headless, load_catalog


TASKS = {
    "electrical": (
        "Review actual boost, hardware STOP, latch, and residual detection evidence. Separate 170/195 V proxies from the final hardware, state what remains unknown.",
        ["r14_5/R14_5_FINAL_REPORT.md", "r14_3/FAULT_CONTAINMENT_OPTIONS.md",
         "r14_3/evidence/interlock_metrics.csv", "r14_3/evidence/energy_audit.json"]),
    "pcb": (
        "Audit the routing approach and baseline counts. Identify topological obstacles and concrete regression evidence required for all-track DRC, parity, 595 and J6.",
        ["r14_5/R14_5_FINAL_REPORT.md", "r14_5/ROUTING_ARCHITECTURE.md",
         "r14_5/UNCONNECTED_NETS.csv", "r14_5/ROUTING_GATE_RESULTS.json"]),
    "safety": (
        "Audit HV package insulation, switch peaks, and the five external gaps. Identify single-fault and insulation evidence required for release.",
        ["r14_5/R14_5_FINAL_REPORT.md", "r14_4/P01_CLEARANCE_DECISION.md",
         "r14_5/eda/NXT-M3-R14.5.kicad_dru", "r14_3/BREAKDOWN_FAULT_MATRIX.csv"]),
    "manufacturing": (
        "Audit the actual four-layer board and 33 remote harness pads. List the package and fabrication qualification and mechanical evidence needed before EVT.",
        ["r14_5/ROUTING_ARCHITECTURE.md", "r14_5/R14_5_FINAL_REPORT.md",
         "r13/PCB_MANUFACTURING_REVIEW.md", "r14_4/R14_4_FINAL_REPORT.md"]),
    "procurement": (
        "Audit BOM and cost boundaries for one module and three modules. Identify obsolete evidence and missing quote, MOQ, and inventory treatment. No new prices can be inferred.",
        ["r13/evidence/quote_observations.md", "r13/BOM_R13_3PC.csv", "r14_5/R14_5_FINAL_REPORT.md"]),
}


FINAL_TASKS = {
    "electrical": ("Review the R14.6 protection endpoints and model limits. Report notes as a nonempty string. No gate approval.",
                   ["r14_6/ROUTING_GATE_RESULTS.json", "r14_6/POWER_AND_PROTECTION_REVIEW.md",
                    "r14_6/evidence/simulation/commands-and-hashes.json"]),
    "pcb": ("Cross-check the final DRC, opens, parity and independent hash against the metrics. Report notes as a nonempty string.",
            ["r14_6/ROUTING_GATE_RESULTS.json", "r14_6/evidence/reproducibility.json",
             "r14_6/UNCONNECTED_NETS.csv"]),
    "safety": ("Review final insulation and C48 engineering changes. Distinguish screening and release. Report notes as a nonempty string.",
               ["r14_6/ROUTING_GATE_RESULTS.json", "r14_6/INSULATION_REVIEW.md", "r14_6/SWITCH_PACKAGE_ECR.md"]),
    "manufacturing": ("Audit fab and external socket qualifications and remaining unknowns. Report notes as a nonempty string.",
                      ["r14_6/ROUTING_GATE_RESULTS.json", "r14_6/MECHANICAL_ASSEMBLY.md", "r14_6/LV_IC_DFM.md"]),
    "procurement": ("Audit the final coverage and priced subset, MOQ and DNP boundaries. Report notes as a nonempty string.",
                    ["r14_6/evidence/procurement-totals.json", "r14_6/COST_R14_6.md"]),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--accept-model-costs", action="store_true")
    parser.add_argument("--stage", choices=("baseline", "final"), default="baseline")
    parser.add_argument("--role", choices=tuple(TASKS))
    args = parser.parse_args()
    if not args.accept_model_costs:
        parser.error("Live requires --accept-model-costs")

    tasks = TASKS if args.stage == "baseline" else FINAL_TASKS
    if args.role:
        tasks = {args.role: tasks[args.role]}
    config, _ = load_catalog()
    if args.stage == "final":
        config["worker_timeout_s"] = 180
    command = headless.default_command()
    identity = headless.preflight(engine, config, command)
    if identity["status"] != "VERIFIED":
        raise SystemExit(json.dumps(identity))
    run = args.out.resolve()
    run.mkdir(parents=True)
    branch_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    engine.write_json(run / "registration.json", {
        "git_head": branch_head, "identity": identity, "stage": args.stage, "max_worker_invocations": len(tasks),
        "worker_timeout_s": config["worker_timeout_s"], "tasks": list(tasks)})
    audits = []
    for role, (brief, inputs) in tasks.items():
        task = {"id": role, "kind": "analysis", "mode": "sealed_analysis", "brief": brief,
                "inputs": inputs, "acceptance": ["evidence_anchors", "limitations", "next_gate_evidence"],
                "expected": ["inventory.md", "sources.json"]}
        print("Review", role, flush=True)
        audit = headless.worker(engine, task, run, run, config, command, identity)
        audit["provider_usage"] = engine.usage_from_host(run / role / "usage.json", config)
        audits.append(audit)
        engine.write_json(run / "audits.json", audits)
        print(role, audit["grade"], audit.get("failure"), flush=True)


if __name__ == "__main__":
    main()
