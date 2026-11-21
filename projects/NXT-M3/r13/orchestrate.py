"""R13 adapter using the R12-pinned R8 execution, checkpoint and audit engine."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import headless

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = spec_from_file_location("nxt_r8_engine", HERE.parent/"r8/orchestrate.py")
engine = module_from_spec(spec)
spec.loader.exec_module(engine)

GATES = {
    "G0": ("SOURCE_READY", {"source_power", "source_protection"}),
    "G1": ("ELECTRICAL_VALIDATED", {"protection_faults"}),
    "G2": ("COST_VERIFIED", {"cost_market"}),
    "G3": ("EDA_COMPLETE", {"native_eda"}),
    "G4": ("EVT_RELEASE_CANDIDATE", {"evt_evidence"}),
}
CAPS = {"max_rounds":6, "max_worker_calls":18, "worker_timeout_s":900,
        "decision_timeout_s":900, "max_output_bytes":2000000, "max_evidence_bytes":512*1024**2}


def load_catalog():
    config = engine.read_json(HERE/"config.json")
    if (config["schema"], config["worker_model"], config["worker_provider"], config["worker_profile"],
        config["decision_model"], config["decision_provider"], config["manufacturing"],
        config["hardware_high_voltage"]) != (
        "nxt.m3.r13.v1", "deepseek-v4-flash", "deepseek-official", "headless",
        "codex-main-session", "openai", "ENGINEERING HOLD", False):
        engine.fail("R13 identity or release contract mismatch")
    for key, limit in CAPS.items():
        if type(config[key]) is not int or not 0 < config[key] <= limit:
            engine.fail(f"Outside R13 resource limit: {key}")
    tasks = {}
    for task in engine.read_json(HERE/"tasks.json"):
        key, stage, kind = task["id"], task["stage"], task["kind"]
        if (not engine.SAFE_ID.fullmatch(key) or key in tasks or stage not in range(5)
            or kind not in {"analysis","spice"} or not set(task["depends"]) <= tasks.keys()
            or any(tasks[d]["stage"] > stage for d in task["depends"])):
            engine.fail("Invalid R13 task dependency or identity")
        if not task["acceptance"] or not engine.string_list(task["acceptance"]):
            engine.fail("Missing stage assertions")
        required = engine.SPICE_FILES if kind == "spice" else {"inventory.md", "sources.json"}
        if set(task["expected"]) != required:
            engine.fail("Invalid preregistered output set")
        if kind == "spice" and (task["target_end_s"] != .065 or task["maxstep_s"] != 1e-7):
            engine.fail("Unexpected preregistered simulation time bounds")
        tasks[key] = task
    stage0 = [t for t in tasks if tasks[t]["stage"] == 0]
    if sorted(stage0) != sorted(config["entry_task_ids"]):
        engine.fail("R13 entry set mismatch")
    return config, tasks


def verify_checkout(config):
    if engine.git("branch", "--show-current") != config["branch"]:
        engine.fail("R13 branch mismatch")
    subprocess.run(["git", "merge-base", "--is-ancestor", config["baseline_sha"], "HEAD"],
                   cwd=ROOT, check=True, capture_output=True)
    if engine.git("diff", "--name-only", config["baseline_sha"], "HEAD", "--",
                  ":!projects/NXT-M3/r13/**"):
        engine.fail("Unexpected committed changes outside R13")
    if engine.git("status", "--porcelain", "--untracked-files=all"):
        engine.fail("Live checkpoints require a clean committed worktree")


def apply_external(run, state, config, tasks, review_path, decision_path):
    review = engine.read_json(review_path)
    desired = state["gates"] | review.get("gate_decisions", {})
    approvals = set(state["approved"]) | set(review["approved_audits"])
    if desired.get("G1") == GATES["G1"][0] and not approvals & {"boost_vendor", "flyback_vendor"}:
        engine.fail("G1 needs at least one independently reviewed real-model candidate")
    for gate, required in {"G1":["G0"], "G3":["G0","G1","G2"], "G4":["G3"]}.items():
        if desired.get(gate) == GATES[gate][0] and any(
            desired.get(prior) != GATES[prior][0] for prior in required
        ):
            engine.fail(f"{gate} violates gate dependencies")
    base_apply_external(run, state, config, tasks, review_path, decision_path)


base_apply_external = engine.apply_external
engine.HERE = HERE
engine.ROOT = ROOT
engine.RUNS = HERE/"runs"
engine.CONTROLS += ("sim/model_pins.json", "sim_cases.json", "sim_followup.json", "simulate.py",
                    "sim/common.inc", "sim/a_boost.inc", "sim/b_flyback.inc")
engine.GATE_REQUIREMENTS = GATES
engine.preflight = lambda cfg, command: headless.preflight(engine, cfg, command)
original_worker = engine.do_worker
engine.do_worker = lambda task, run, out, cfg, command, identity: headless.worker(engine, task, run, out, cfg, command, identity)
engine.CONTROLS += ("headless.py", "headless.patch.yml")
engine.load_catalog = load_catalog
engine.verify_checkout = verify_checkout
engine.apply_external = apply_external


if __name__ == "__main__":
    engine.main()
