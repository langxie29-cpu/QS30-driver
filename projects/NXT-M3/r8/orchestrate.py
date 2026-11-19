"""Bounded NXT-M3 R8 scheduler, defaulting to provider-free dry-run."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import tempfile
from threading import Event, Lock, Thread
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = HERE / "evidence/runs"
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
CONTROLS = ("config.json", "tasks.json", "acceptance.json", "decision.schema.json",
            "prompts/FLASH_WORKER.md", "prompts/CODEX_DECISION.md", "orchestrate.py",
            "evidence/source_manifest.json")
DECISION_KEYS = {"decision", "rationale", "next_task_ids", "issues", "controlling_assumptions"}
RESULT_KEYS = {"task_id", "status", "notes", "evidence_files", "source_urls", "solver",
               "model_hashes", "blocking_issues"}
GATE_REQUIREMENTS = {
    "G0": ("ACCEPT_CANDIDATE", {"bjt_qualification", "logic_qualification", "reference_v3_review", "base_drive_bound"}),
    "G1": ("LIMITED_PASS", {"four_channel_fixture", "four_channel_fault_validation"}),
    "G2": ("LIMITED_PASS", {"thirty_channel_eda"}),
}
SPICE_FILES = {"circuit.cir", "run.log", "waves.txt", "metrics.json", "model_sources.json"}


def now():
    return datetime.now(timezone.utc).isoformat()


def fail(message):
    raise ValueError(message)


def read_json(path, cap=2_000_000):
    if not path.is_file() or path.stat().st_size > cap:
        fail(f"Missing or oversized JSON: {path.name}")
    def object_pairs(pairs):
        if len({key for key, _ in pairs}) != len(pairs):
            fail("Duplicate JSON key")
        return dict(pairs)
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=object_pairs,
                      parse_constant=lambda value: fail(f"Invalid JSON number: {value}"))


def write_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    temp.replace(path)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bounded_path(base, rel):
    if not isinstance(rel, str) or not rel or any(x in rel for x in ("\\", ":", "\x00")):
        fail("Evidence paths must be relative POSIX paths")
    parts = rel.split("/")
    if any(x in ("", ".", "..") or x.endswith((".", " ")) or PureWindowsPath(x).is_reserved()
           for x in parts):
        fail("Path traversal or reserved evidence name")
    base = base.resolve()
    cursor = base
    for section in parts:
        cursor /= section
        if cursor.is_symlink() or cursor.resolve() != cursor:
            fail("Evidence path contains a link or junction")
    if not cursor.is_relative_to(base):
        fail("Evidence outside task directory")
    return cursor


def string_list(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def load_catalog():
    cfg = read_json(HERE / "config.json")
    rows = read_json(HERE / "tasks.json")
    if cfg["manufacturing"] != "ENGINEERING HOLD" or cfg["hardware_high_voltage"] is not False:
        fail("Manufacturing and physical HV are permanently disabled")
    if (cfg["worker_model"], cfg["worker_provider"], cfg["worker_profile"], cfg["decision_model"],
        cfg["decision_provider"]) != ("deepseek-v4-flash", "deepseek-official", "headless", "gpt-6.1-sol", "openai"):
        fail("Unexpected identity configuration")
    for key, cap in (("max_rounds", 4), ("max_worker_calls", 12), ("worker_timeout_s", 900),
                     ("decision_timeout_s", 900), ("max_output_bytes", 2_000_000),
                     ("max_evidence_bytes", 512 * 1024**2)):
        if type(cfg[key]) is not int or not 0 < cfg[key] <= cap:
            fail(f"Outside resource limit: {key}")
    tasks = {t["id"]: t for t in rows}
    if len(rows) != len(tasks):
        fail("Duplicate task ID")
    stage0 = {x for x, t in tasks.items() if t["stage"] == 0}
    if set(cfg["entry_task_ids"]) != stage0 or len(cfg["entry_task_ids"]) != len(stage0):
        fail("Entry tasks must be all Stage 0 tasks")
    seen = set()
    for t in sorted(rows, key=lambda row: row["stage"]):
        kind, stage, task_id = t["kind"], t["stage"], t["id"]
        if not SAFE_ID.fullmatch(task_id) or kind not in ("analysis", "spice", "codex") or stage not in range(5):
            fail("Invalid task identity, stage or kind")
        if not set(t["depends"]) <= seen or any(tasks[x]["stage"] > stage for x in t["depends"]):
            fail("Unknown dependency, cycle, or unsorted same-stage tasks")
        if not string_list(t["acceptance"]) or not t["acceptance"]:
            fail("Missing preregistered acceptance assertions")
        expected = {"inventory.md", "sources.json"} if kind == "analysis" else SPICE_FILES if kind == "spice" else set()
        if set(t["expected"]) != expected:
            fail("Required evidence cannot be weakened")
        if kind == "spice" and not all(
            type(t[k]) in (int, float) and math.isfinite(t[k]) and t[k] > 0
            for k in ("target_end_s", "maxstep_s")
        ):
            fail("Missing SPICE time preregistration")
        seen.add(task_id)
    return cfg, tasks


def eligible(task_id, tasks, reviewed, history, worker=True, gates=None):
    if task_id not in tasks or task_id in history:
        return False
    t = tasks[task_id]
    if worker != (t["kind"] != "codex"):
        return False
    stage0 = {k for k, v in tasks.items() if v["stage"] == 0}
    required = set(t["depends"]) | (stage0 if t["stage"] else set())
    gate_ids = list(GATE_REQUIREMENTS)[:t["stage"]]
    return required <= reviewed and all(
        (gates or {}).get(g) == GATE_REQUIREMENTS[g][0] for g in gate_ids
    )


def validate_decision(dec, tasks, reviewed, history, remaining_rounds, remaining_calls, gates=None):
    if not isinstance(dec, dict) or set(dec) != DECISION_KEYS or dec["decision"] not in ("CONTINUE", "HOLD", "STOP"):
        fail("Invalid Codex decision")
    if not isinstance(dec["rationale"], str) or not dec["rationale"].strip():
        fail("Missing rationale")
    for k in ("next_task_ids", "issues", "controlling_assumptions"):
        if not string_list(dec[k]):
            fail(f"Invalid {k}")
    nxt = dec["next_task_ids"]
    if dec["decision"] != "CONTINUE":
        if nxt:
            fail("Terminal disposition cannot select work")
        return
    if not remaining_rounds or not 0 < len(nxt) <= remaining_calls:
        fail("Round or call budget exhausted")
    if len(nxt) != len(set(nxt)) or not all(eligible(k, tasks, reviewed, history, gates=gates) for k in nxt):
        fail("Duplicate, unavailable, or dependency-blocked task")


def audit_worker_result(task, folder, cap):
    try:
        result = read_json(bounded_path(folder, "result.json"), 131072)
        if set(result) != RESULT_KEYS or result["task_id"] != task["id"]:
            fail("Worker result contract or identity mismatch")
        status = result["status"]
        if status not in ("PASS", "FAIL", "INCONCLUSIVE"):
            fail("Invalid worker status")
        for key in ("notes", "solver"):
            if not isinstance(result[key], str) or not result[key].strip():
                fail(f"Missing {key}")
        for key in ("evidence_files", "source_urls", "blocking_issues"):
            if not string_list(result[key]):
                fail(f"Invalid {key}")
        if any(not url.startswith("https://") for url in result["source_urls"]):
            fail("Only HTTPS source URLs are accepted")
        models = result["model_hashes"]
        if not isinstance(models, dict) or any(not isinstance(v, str) or not SHA.fullmatch(v) for v in models.values()):
            fail("Invalid model digest")
        evidence = {}
        for name in result["evidence_files"]:
            p = bounded_path(folder, name)
            if name in evidence or not p.is_file() or not 0 < p.stat().st_size <= cap:
                fail("Duplicate, absent, empty or oversized evidence")
            evidence[name] = sha256(p)
        expected = set(task["expected"])
        if task["kind"] == "spice" and "waves.txt" not in evidence:
            if any(Path(p).suffix.lower() in (".raw", ".tr0") for p in evidence):
                expected.remove("waves.txt")
        if status == "PASS" and (not expected <= evidence.keys() or result["blocking_issues"]):
            fail("PASS lacks required evidence or has blocking issues")
        if status == "PASS" and task["kind"] == "analysis":
            sources = read_json(folder / "sources.json")
            if not isinstance(sources, list) or not sources or not all(
                isinstance(s, dict) and isinstance(s.get("source"), str) and
                isinstance(s.get("assertion"), str) and s["assertion"].strip() for s in sources
            ):
                fail("Missing verifiable source assertions")
        if status == "PASS" and task["kind"] == "spice":
            m = read_json(folder / "metrics.json")
            prereg = read_json(folder / "preregister.json")
            def positive(k):
                return type(m[k]) in (int, float) and math.isfinite(m[k]) and m[k] > 0
            if (m["solver"] != result["solver"] or result["solver"] == "none" or type(m["exit_code"]) is not int
                    or m["exit_code"] != 0 or m["endpoint_reached"] is not True or m["evaluation_status"] != "LIMITED_PASS"
                    or not all(positive(k) for k in ("endpoint_s", "target_end_s", "maxstep_s"))
                    or m["endpoint_s"] < m["target_end_s"] - m["maxstep_s"]
                    or m["target_end_s"] != prereg.get("target_end_s") or m["maxstep_s"] != prereg.get("maxstep_s")):
                fail("Incomplete solver process, time or preregistration mismatch")
            if {a["name"] for a in m["assertions"] if a["passed"] is True} != set(prereg["acceptance"]):
                fail("Preregistered assertions were not all satisfied")
            if any(a["passed"] is not True for a in m["assertions"]):
                fail("Failed SPICE assertion")
            provenance = read_json(folder / "model_sources.json")
            if not models or set(models) != set(provenance):
                fail("Missing model provenance")
            for name, src in provenance.items():
                for k in ("source", "version", "license"):
                    if not isinstance(src[k], str) or not src[k].strip():
                        fail("Missing model metadata")
                if evidence.get(src["file"]) != models[name]:
                    fail("Original model bytes do not match hash")
        return dict(task_id=task["id"], worker_claim=status, grade=(
            "CLAIMED_PASS_AUDITED_FILES" if status == "PASS" else status), evidence_sha256=evidence)
    except (ValueError, KeyError, IndexError, AttributeError, OSError, TypeError) as error:
        return dict(task_id=task["id"], grade="INCONCLUSIVE", reason=str(error))


def run_process(argv, cwd, timeout, cap):
    """Limit retained output across both pipes; stop on timeout or cap."""
    started = now()
    timer = time.monotonic()
    if os.name == "nt" and Path(argv[0]).suffix.lower() in (".cmd", ".bat"):
        return dict(rc=None, failure="UNSAFE_SHELL_WRAPPER", started=started, stdout=b"", stderr=b"", seconds=0)
    try:
        process = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, shell=False)
    except OSError:
        return dict(rc=None, failure="EXECUTION_FAIL", started=started, stdout=b"", stderr=b"", seconds=0)
    overflow = Event()
    lock = Lock()
    captured = [bytearray(), bytearray()]

    def drain(pipe, buffer):
        with pipe:
            while chunk := pipe.read1(65536):
                with lock:
                    remaining = cap - sum(map(len, captured))
                    buffer.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        overflow.set()

    readers = [Thread(target=drain, args=(pipe, buffer), daemon=True)
               for pipe, buffer in zip((process.stdout, process.stderr), captured)]
    for reader in readers:
        reader.start()
    failure = None
    while process.poll() is None or any(reader.is_alive() for reader in readers):
        if overflow.is_set() or time.monotonic() - timer >= timeout:
            failure = "OUTPUT_CAP" if overflow.is_set() else "PROCESS_TIMEOUT"
            if process.poll() is None:
                process.kill()
            break
        time.sleep(0.025)
    process.wait(timeout=2)
    with lock:
        stdout, stderr = map(bytes, captured)
    return dict(rc=process.returncode, failure=failure or (
        "OUTPUT_CAP" if overflow.is_set() else None if process.returncode == 0 else "EXECUTION_FAIL"),
        started=started, seconds=round(time.monotonic()-timer, 3), stdout=stdout, stderr=stderr)


def effective_identity(payload, cfg):
    """Only a structured host receipt can demonstrate the effective model and confinement."""
    if (payload.get("model"), payload.get("provider"), payload.get("endpoint")) != (
            cfg["worker_model"], cfg["worker_provider"], "https://api.deepseek.com"):
        fail("Effective worker model, provider or endpoint mismatch")
    # A worker can read project inputs and write this job's artifacts through
    # mediated file access. Only a preregistered simulator can be invoked.
    expected = {"repository": "read-only", "writes": "task-directory", "execution": "registered-engineering-tools-only",
                "network": "read-only-sources", "manufacturing": False, "hardware": False,
                "background_model_requests": False}
    policy = payload.get("policy")
    if policy != expected or policy.get("manufacturing") is not False or policy.get("hardware") is not False:
        fail("Worker confinement or background-call policy is unverified")
    return {k: payload[k] for k in ("model", "provider", "endpoint", "policy")}


def preflight(cfg, command):
    receipt = run_process([*command, "--profile", cfg["worker_profile"], "--dump-config"], ROOT, 45,
                          cfg["max_output_bytes"])
    if receipt["failure"]:
        known = b"exists and is not a symlink" in receipt["stderr"]
        return {"status": "HOLD", "exit_code": receipt["rc"], "failure": receipt["failure"],
                "diagnostic": ("Harness profile dependency exists as a regular directory, expected symlink"
                               if known else "Harness read-only configuration dump did not complete")}
    try:
        identity = effective_identity(json.loads(receipt["stdout"]), cfg)
    except (ValueError, TypeError, AttributeError):
        return {"status": "HOLD", "diagnostic": "Dump does not establish effective model/provider and worker confinement"}
    return {"status": "VERIFIED", "configuration_sha256": hashlib.sha256(receipt["stdout"]).hexdigest(), **identity}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, encoding="utf-8").strip()


def verify_checkout(cfg):
    if git("branch", "--show-current") != cfg["branch"]:
        fail("R8 branch mismatch")
    subprocess.run(["git", "merge-base", "--is-ancestor", cfg["baseline_sha"], "HEAD"],
                   cwd=ROOT, check=True, capture_output=True)
    if git("diff", "--name-only", cfg["baseline_sha"], "HEAD", "--", ":!projects/NXT-M3/r8"):
        fail("Unexpected committed changes outside R8")
    if git("status", "--porcelain", "--untracked-files=all"):
        fail("Live checkpoints require a clean committed worktree")


def input_snapshot():
    snapshot = dict(head=git("rev-parse", "HEAD"),
                    controls={f: sha256(HERE / f) for f in CONTROLS})
    available = {}
    for item in read_json(HERE / "evidence/source_manifest.json"):
        if not item.get("archived_path"):
            continue
        p = bounded_path(HERE, item["archived_path"])
        if sha256(p) != item["sha256"]:
            fail("Archived source digest mismatch")
        available[item["archived_path"]] = item["sha256"]
    snapshot["archived_source_bytes"] = available
    return snapshot


def inventory(run, cap):
    files = {}
    for path in sorted(run.rglob("*")):
        name = path.relative_to(run).as_posix()
        if name in ("checkpoint.json", "run.lock"):
            continue
        p = bounded_path(run, name)
        if p.is_file():
            if p.stat().st_size > cap:
                fail(f"Raw evidence exceeded cap: {name}")
            files[name] = sha256(p)
        elif not p.is_dir():
            fail("Non-regular file in run")
    return files


def checkpoint(run, state, cfg):
    state["evidence_sha256"] = inventory(run, cfg["max_evidence_bytes"])
    write_json(run / "checkpoint.json", state)


def verify_resume(run, state, cfg, snapshot, identity):
    if (state["snapshot"], state["identity"], state["baseline"]) != (snapshot, identity, cfg["baseline_sha"]):
        fail("Configuration, provider, model bytes or commit drift")
    if state["evidence_sha256"] != inventory(run, cfg["max_evidence_bytes"]):
        fail("Historical evidence drift or interrupted checkpoint")
    if state["status"] == "RUNNING":
        fail("Interrupted invocation requires reconciliation; automatic replay is forbidden")


def usage_from_host(path, cfg):
    """A launcher-side receipt is distinct from any worker-authored artifact."""
    unknown = dict(requests=None, failed_requests=None, tokens=None, cost="COST_UNKNOWN")
    if not path.is_file():
        return unknown
    try:
        data = read_json(path)
        if (data["model"], data["provider"]) != (cfg["worker_model"], cfg["worker_provider"]):
            fail("Execution receipt identity mismatch")
        if not all(type(data[k]) is int and data[k] >= 0 for k in ("requests", "failed_requests", "tokens")):
            fail("Malformed usage counters")
        if data["failed_requests"] > data["requests"]:
            fail("Failed requests exceed total")
        cost = data.get("cost", "COST_UNKNOWN")
        if cost != "COST_UNKNOWN" and (
            not isinstance(cost, dict) or type(cost.get("amount")) not in (int, float)
            or not math.isfinite(cost["amount"]) or cost["amount"] < 0 or not cost.get("currency")
            or not cost.get("receipt_reference")
        ):
            fail("Malformed actual cost receipt")
        return {k: data[k] for k in ("requests", "failed_requests", "tokens")} | {"cost": cost}
    except (ValueError, TypeError, KeyError, OSError):
        return unknown


def do_worker(task, run, round_dir, cfg, command, cfg_identity):
    folder = round_dir / task["id"]
    folder.mkdir()
    write_json(folder / "preregister.json", dict(task_id=task["id"], acceptance=task["acceptance"],
                                                research_limits=read_json(HERE / "acceptance.json")))
    if task["kind"] == "spice":
        prereg = read_json(folder / "preregister.json")
        prereg.update({k: task[k] for k in ("target_end_s", "maxstep_s")})
        write_json(folder / "preregister.json", prereg)
    host_usage = round_dir / (task["id"] + ".host-usage.json")
    prompt = (HERE / "prompts/FLASH_WORKER.md").read_text(encoding="utf-8-sig")
    prompt += "\n" + json.dumps(dict(task=task, repo=str(ROOT), output_dir=str(folder),
                                     result_path=str(folder / "result.json")), ensure_ascii=False)
    (folder / "task_prompt.txt").write_text(prompt, encoding="utf-8")
    # Snapshot outside the task directory. The verified host policy must
    # mediate tools and put usage in its separate receipt.
    before = inventory(run, cfg["max_evidence_bytes"])
    prefix = folder.relative_to(run).as_posix() + "/"
    if preflight(cfg, command) != cfg_identity:
        return dict(task_id=task["id"], grade="INCONCLUSIVE", failure="IDENTITY_DRIFT")
    previous = os.environ.get("NXT_R8_HOST_USAGE")
    os.environ["NXT_R8_HOST_USAGE"] = str(host_usage)
    try:
        out = run_process([*command, "--profile", cfg["worker_profile"], prompt], folder,
                          cfg["worker_timeout_s"], cfg["max_output_bytes"])
    finally:
        if previous is None:
            del os.environ["NXT_R8_HOST_USAGE"]
        else:
            os.environ["NXT_R8_HOST_USAGE"] = previous
    after = inventory(run, cfg["max_evidence_bytes"])
    if any(after.get(k) != v for k, v in before.items()) or any(
            not k.startswith(prefix) and k not in before and k != host_usage.relative_to(run).as_posix()
            for k in after):
        fail("Worker changed preregistration or evidence outside its own scope")
    for file in ("dsh_stdout", "dsh_stderr"):
        data = out.pop(file.removeprefix("dsh_"))
        with (folder / (file + ".txt")).open("xb") as stream:
            stream.write(data)
    audit = audit_worker_result(task, folder, cfg["max_evidence_bytes"])
    if out["failure"]:
        audit["grade"] = "INCONCLUSIVE"
    audit.update(out, usage=usage_from_host(host_usage, cfg), identity=cfg_identity)
    return audit


def new_state(cfg, snapshot, identity):
    return dict(snapshot=snapshot, identity=identity, baseline=cfg["baseline_sha"],
                status="READY", created_utc=now(), pending=cfg["entry_task_ids"][:], calls=0, rounds=0, decisions=0,
                history={}, approved=[], gates={}, manufacturing=cfg["manufacturing"])


def apply_external(run, state, cfg, tasks, review_path, decision_path):
    if state["status"] not in ("AWAITING_CODEX", "HOLD"):
        fail("Checkpoint is not accepting a decision")
    if state["decisions"] >= cfg["max_rounds"]:
        fail("Decision budget exhausted")
    review = read_json(review_path)
    if (review.get("model"), review.get("provider")) != (cfg["decision_model"], cfg["decision_provider"]):
        fail("Independent reviewer identity not asserted")
    if not isinstance(review.get("independent_evidence_review"), str) or not review["independent_evidence_review"].strip():
        fail("Missing independent evidence review")
    approved = set(state["approved"])
    for k, digest in review["approved_audits"].items():
        rel = state["history"].get(k)
        if not rel:
            fail("Review refers to an unexecuted task")
        p = bounded_path(run, rel)
        if sha256(p) != digest or read_json(p)["grade"] != "CLAIMED_PASS_AUDITED_FILES":
            fail("Review requires the exact audited worker evidence")
        approved.add(k)
    gates = dict(state["gates"])
    for gate, result in review.get("gate_decisions", {}).items():
        if gate not in GATE_REQUIREMENTS:
            fail("Unknown engineering gate")
        accepted, prerequisites = GATE_REQUIREMENTS[gate]
        if result not in {accepted, "REWORK", "REJECT", "INCONCLUSIVE"}:
            fail("Invalid engineering gate decision")
        if result == accepted and not prerequisites <= approved:
            fail("Engineering gate lacks independently reviewed task evidence")
        gates[gate] = result
    for g, prior in (("G1", "G0"), ("G2", "G1")):
        if gates.get(g) == GATE_REQUIREMENTS[g][0] and gates.get(prior) != GATE_REQUIREMENTS[prior][0]:
            fail("Upstream engineering gate is unqualified")
    dec = read_json(decision_path)
    # This decision consumes one decision slot, including terminal dispositions.
    remaining_rounds = min(cfg["max_rounds"] - state["rounds"], cfg["max_rounds"] - state["decisions"] - 1)
    validate_decision(dec, tasks, approved, set(state["history"]), remaining_rounds,
                      cfg["max_worker_calls"] - state["calls"], gates=gates)
    state["decisions"] += 1
    write_json(run / f"codex_decision_{state['decisions']:02}.json",
               dict(accepted_utc=now(), decision=dec, independent_review=review))
    state.update(status="READY" if dec["decision"] == "CONTINUE" else dec["decision"],
                 pending=dec["next_task_ids"], approved=sorted(approved), gates=gates)
    checkpoint(run, state, cfg)


def execute_round(run, state, cfg, tasks, command, identity):
    if state["status"] != "READY":
        return
    if state["rounds"] >= cfg["max_rounds"] or not state["pending"] or (
            state["calls"] + len(state["pending"]) > cfg["max_worker_calls"]):
        state.update(status="STOP", terminal_reason="BUDGET_OR_NO_PENDING_TASKS")
        checkpoint(run, state, cfg)
        return
    state["rounds"] += 1
    directory = run / f"round_{state['rounds']:02}"
    directory.mkdir()
    state["status"] = "RUNNING"
    checkpoint(run, state, cfg)
    for task_id in state["pending"]:
        if not eligible(task_id, tasks, set(state["approved"]), set(state["history"]), gates=state["gates"]):
            fail("Scheduler dependency or repeat violation")
        verify_checkout(cfg)
        state["calls"] += 1
        checkpoint(run, state, cfg)
        audit = do_worker(tasks[task_id], run, directory, cfg, command, identity)
        path = directory / task_id / "audit.json"
        path.parent.mkdir(exist_ok=True)
        write_json(path, audit)
        state["history"][task_id] = path.relative_to(run).as_posix()
        if audit.get("failure") == "IDENTITY_DRIFT":
            state.update(status="STOP", terminal_reason="IDENTITY_DRIFT", pending=[])
            checkpoint(run, state, cfg)
            return
        checkpoint(run, state, cfg)
    verify_checkout(cfg)
    state.update(status="AWAITING_CODEX", pending=[])
    write_json(directory / "decision_input.json", dict(
        audits=state["history"], gates=state["gates"], snapshot=state["snapshot"], decision_model=cfg["decision_model"],
        decision_provider=cfg["decision_provider"], calls=state["calls"], rounds=state["rounds"],
        calls_remaining=cfg["max_worker_calls"] - state["calls"],
        rounds_remaining=cfg["max_rounds"] - state["rounds"], manufacturing=cfg["manufacturing"]))
    checkpoint(run, state, cfg)


def resource_summary(run, state):
    rows = [read_json(bounded_path(run, p)) for p in state["history"].values()]
    usage = [r.get("usage", {}) for r in rows]
    counters = {}
    for k in ("requests", "failed_requests", "tokens"):
        counters[k] = (sum(u[k] for u in usage) if all(type(u.get(k)) is int for u in usage) else None)
    costs = [u.get("cost") for u in usage]
    known_costs = {}
    for c in costs:
        if isinstance(c, dict):
            known_costs[c["currency"]] = known_costs.get(c["currency"], 0) + c["amount"]
    return dict(rounds=state["rounds"], worker_slots_reserved=state["calls"], decision_records=state["decisions"],
                worker_failures=sum(bool(r.get("failure")) for r in rows),
                worker_claims_inconclusive=sum(r["grade"] == "INCONCLUSIVE" for r in rows),
                provider_usage=counters, actual_cost_by_currency=known_costs if costs and
                all(isinstance(c, dict) for c in costs) else "COST_UNKNOWN")


def dry_run(cfg, tasks):
    return dict(status="DRY_RUN", baseline=cfg["baseline_sha"], entry_task_ids=cfg["entry_task_ids"],
                task_count=len(tasks), max_rounds=cfg["max_rounds"], max_worker_calls=cfg["max_worker_calls"],
                worker=dict(model=cfg["worker_model"], provider=cfg["worker_provider"], profile=cfg["worker_profile"]),
                decision=dict(model=cfg["decision_model"], provider=cfg["decision_provider"],
                              mode="external-decisions"),
                model_requests=0, manufacturing=cfg["manufacturing"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--accept-model-costs", action="store_true")
    parser.add_argument("--external-decisions", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--dsh", nargs="+", default=[shutil.which("dsh") or "dsh"])
    args = parser.parse_args()
    cfg, tasks = load_catalog()
    if args.doctor:
        result = preflight(cfg, args.dsh)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "VERIFIED" else 2
    if not args.live:
        print(json.dumps(dry_run(cfg, tasks), ensure_ascii=False, indent=2))
        return 0
    if not args.accept_model_costs or not args.external_decisions or not args.run_id:
        parser.error("Live requires --accept-model-costs --external-decisions --run-id live-<id>")
    if not args.run_id.startswith("live-") or not SAFE_ID.fullmatch(args.run_id):
        parser.error("Invalid live run ID")
    if bool(args.decision) != bool(args.review) or (args.decision and not args.resume):
        parser.error("Applying a decision requires --resume --decision FILE --review FILE")
    try:
        verify_checkout(cfg)
        identity = preflight(cfg, args.dsh)
        if identity["status"] != "VERIFIED":
            print(json.dumps(identity))
            return 2
        snapshot = input_snapshot()
        RUNS.mkdir(exist_ok=True)
        run = bounded_path(RUNS, args.run_id)
        if not args.resume:
            run.mkdir()
        elif not run.is_dir():
            fail("Unknown checkpoint")
        lock = run / "run.lock"
        lock.touch(exist_ok=False)
        try:
            if args.resume:
                state = read_json(run / "checkpoint.json", 8_000_000)
                verify_resume(run, state, cfg, snapshot, identity)
            else:
                state = new_state(cfg, snapshot, identity)
                checkpoint(run, state, cfg)
            if args.decision:
                apply_external(run, state, cfg, tasks, args.review, args.decision)
            execute_round(run, state, cfg, tasks, args.dsh, identity)
            write_json(run / "run_summary.json", dict(updated_utc=now(), status=state["status"],
                       resources=resource_summary(run, state), manufacturing=cfg["manufacturing"]))
            checkpoint(run, state, cfg)
            print(json.dumps(dict(status=state["status"], run=str(run), rounds=state["rounds"],
                                  calls=state["calls"], decisions=state["decisions"])))
        finally:
            lock.unlink()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps(dict(status="HOLD", reason=str(error), manufacturing=cfg["manufacturing"])))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
