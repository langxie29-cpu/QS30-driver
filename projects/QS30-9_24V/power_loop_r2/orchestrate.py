"""QS30 dual-model *local* orchestration. Stdlib only; safe dry-run default.

No model runs/credentials/physical instruments are invoked unless user passes
--live --accept-model-costs. This tool never signs off hardware or manufacturing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import re
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load_catalog():
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    tasks = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate task IDs")
    table = {t["id"]: t for t in tasks}
    for t in tasks:
        if t["kind"] not in ("analysis", "spice") or t["stage"] not in (0, 1, 2, 3):
            raise ValueError("Invalid task kind/stage")
        if not set(t["depends"]) <= table.keys() or t["id"] in t["depends"]:
            raise ValueError("Invalid dependency")
        expected = ["inventory.md"] if t["kind"] == "analysis" else [
            "circuit.cir", "run.log", "waves.txt", "metrics.json"
        ]
        if t["expected"] != expected:
            raise ValueError("Evidence requirements cannot be weakened")
    if cfg["manufacturing"] != "HOLD" or cfg["hardware_high_voltage"] is not False:
        raise ValueError("Manufacturing/HV must remain HOLD")
    return cfg, table


def sha256(path: Path) -> str:
    dig = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            dig.update(chunk)
    return dig.hexdigest()


def bounded_path(base: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or "\x00" in rel:
        raise ValueError("Invalid evidence path")
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Path traversal in evidence")
    base_resolved = base.resolve()
    full = (base / p).resolve()
    if full == base_resolved or not full.is_relative_to(base_resolved):
        raise ValueError("Evidence outside task directory")
    return full


def audit_worker_result(task: dict, task_dir: Path, size_cap: int) -> dict:
    result_file = task_dir / "result.json"
    if not result_file.exists() or result_file.stat().st_size > 131072:
        return {"task_id": task["id"], "grade": "INCONCLUSIVE",
                "reason": "No valid worker result JSON"}
    try:
        result = json.loads(result_file.read_text(encoding="utf-8"))
        status = result["status"]
        if result["task_id"] != task["id"] or status not in ("PASS", "FAIL", "INCONCLUSIVE"):
            raise ValueError("Bad task identity or status")
        if not isinstance(result["notes"], str) or not isinstance(result["evidence_files"], list):
            raise ValueError("Bad result format")
        evidence = {}
        for rel in result["evidence_files"]:
            p = bounded_path(task_dir, rel)
            if not p.is_file() or p.stat().st_size > size_cap or p.stat().st_size == 0:
                raise ValueError("Missing/empty/large evidence: " + rel)
            evidence[rel] = sha256(p)
        if status == "PASS" and not set(task["expected"]) <= set(evidence):
            raise ValueError("Claimed PASS without required files")
        if status == "PASS" and task["kind"] == "spice":
            m = json.loads((task_dir / "metrics.json").read_text(encoding="utf-8"))
            for k in ("solver", "exit_code", "endpoint_reached", "maxstep_s",
                      "evaluation_status", "assertions"):
                if k not in m:
                    raise ValueError("SPICE metrics missing " + k)
            if m["exit_code"] != 0 or m["endpoint_reached"] is not True:
                raise ValueError("SPICE process/endpoint not complete")
            if m["evaluation_status"] != "LIMITED_PASS" or not isinstance(m["assertions"], list) or not m["assertions"]:
                raise ValueError("SPICE has no actual assertions")
            if not all(isinstance(a, dict) and a.get("passed") is True for a in m["assertions"]):
                raise ValueError("SPICE has failed/malformed assertions")
            if not isinstance(result.get("model_hashes"), dict) or not result["model_hashes"]:
                raise ValueError("SPICE model origin not recorded")
        grade = "CLAIMED_PASS_AUDITED_FILES" if status == "PASS" else status
        return {"task_id": task["id"], "grade": grade, "worker_claim": status,
                "notes": result["notes"][:2400], "evidence_sha256": evidence,
                "warning": "File/protocol audit ONLY; neither physical nor SPICE electrical signoff"}
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        return {"task_id": task["id"], "grade": "INCONCLUSIVE",
                "reason": "Worker result failed deterministic audit: " + str(exc)}


def eligible(task_id: str, tasks: dict, completed: dict, max_stage: int, history: set) -> bool:
    if task_id not in tasks or task_id in history:
        return False
    t = tasks[task_id]
    if t["stage"] > min(3, max_stage + 1):
        return False
    if t["stage"] >= 2 and not any(tasks[k]["stage"] == 1 for k in history):
        return False
    if t['id'] == 'zero_volt_startup' or t["stage"] >= 3:
        # A documented controller reference AND a documented nonlinear device cell
        # are prerequisites for startup/loop exercises; textual model selection is not enough.
        references = ("lt3757a_reference", "ucc28c43_reference")
        if not any(completed.get(k, {}).get("grade") == "CLAIMED_PASS_AUDITED_FILES" for k in references):
            return False
        if completed.get("device_cells", {}).get("grade") != "CLAIMED_PASS_AUDITED_FILES":
            return False
    return all(completed.get(dep, {}).get("grade") == "CLAIMED_PASS_AUDITED_FILES"
               for dep in t["depends"])


def validate_decision(dec: dict, tasks: dict, completed: dict, max_stage: int, history: set):
    if not isinstance(dec, dict) or dec.get("decision") not in ("CONTINUE", "HOLD", "STOP"):
        raise ValueError("Bad Codex decision")
    if not isinstance(dec.get("rationale"), str):
        raise ValueError("No rationale")
    nxt = dec.get("next_task_ids")
    if not isinstance(nxt, list) or not all(isinstance(k, str) for k in nxt) or len(nxt) != len(set(nxt)) or len(nxt) > 4:
        raise ValueError("Bad next-task list")
    if dec["decision"] != "CONTINUE" and nxt:
        raise ValueError("Non-continue cannot schedule work")
    for task_id in nxt:
        if not isinstance(task_id, str) or not eligible(task_id, tasks, completed, max_stage, history):
            raise ValueError("Codex requested unapproved/blocked task: " + str(task_id))
    if dec["decision"] == "CONTINUE" and not nxt:
        raise ValueError("CONTINUE requires next tasks")
    for key in ("issues", "controlling_assumptions"):
        if not isinstance(dec.get(key), list) or not all(isinstance(v, str) for v in dec[key]):
            raise ValueError("Missing issues/assumptions")


def subprocess_record(argv, input_text, timeout_s, cwd):
    import time
    try:
        p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',cwd=str(cwd),shell=False,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            out,err=p.communicate(input_text,timeout=timeout_s)
            return dict(rc=p.returncode,stdout=out,stderr=err)
        except subprocess.TimeoutExpired:
            killed=subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
            out,err=p.communicate()
            return dict(rc=None,stdout=out,stderr=err+'\nPROCESS_TREE_TIMEOUT\n'+killed.stdout)
    except OSError as e:
        return dict(rc=None,stdout='',stderr='EXEC_FAILED: '+str(e))


def worker_argv(cfg: dict):
    """Invoke Node directly on Windows; avoid stale .cmd launchers and shell quoting."""
    node, cli = os.environ.get('QS30_DSH_NODE'), os.environ.get('QS30_DSH_CLI')
    if bool(node) != bool(cli):
        raise RuntimeError('Both QS30_DSH_NODE and QS30_DSH_CLI required')
    argv = [node, cli] if node else [cfg['worker_binary']]
    argv += ['--profile', cfg['worker_profile']]
    if os.environ.get('QS30_DSH_PATCH'):
        argv += ['--patch', os.environ['QS30_DSH_PATCH']]
    if os.environ.get('QS30_DSH_HOME'):
        os.environ['DSH_HOME'] = os.environ['QS30_DSH_HOME']
    return argv


def preflight(cfg: dict):
    if not os.environ.get('QS30_DSH_NODE') and not shutil.which(cfg["worker_binary"]):
        raise RuntimeError("dsh not found in PATH; verify DeepSeek Harness installation")
    if not shutil.which("codex"):
        raise RuntimeError("codex not found in PATH; verify Codex CLI")
    result = subprocess_record(
        worker_argv(cfg) + ["--dump-config"],
        None, 90, ROOT)
    # Never print/dump profile text: it can contain provider configuration.
    if result["rc"] != 0:
        raise RuntimeError("DeepSeek Harness profile dump failed; inspect locally")
    section = re.search(r'(?m)^- id: agent-default-model\s*\n(?:(?!^- id:).|\n)*', result['stdout'])
    model = re.search(r'(?m)^\s+model:\s*[\"\x27]?([^\s\"\x27]+)', section[0]) if section else None
    provider = re.search(r'(?m)^\s+provider:\s*([^\s]+)', section[0]) if section else None
    if not model or model[1] != cfg['expected_worker_model'] or not provider or provider[1] != 'deepseek-official':
        raise RuntimeError("Harness headless profile is not verifiably deepseek-flash; "
                           "do not overwrite the user's global profile. Configure a dedicated headless profile.")
    return "Harness model string verified from profile; Codex GPT access still checked at invocation"


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def do_worker(task: dict, round_dir: Path, cfg: dict):
    task_dir = round_dir / task["id"]
    task_dir.mkdir(parents=True, exist_ok=False)
    result_path = task_dir / "result.json"
    spec = (HERE / "prompts/FLASH_WORKER.md").read_text(encoding="utf-8")
    prompt = (
        spec + "\n\nCURRENT JOB:\n"
        + "TASK_ID: " + task["id"] + "\nROLE: " + task["role"]
        + "\nKIND: " + task["kind"] + "\nDESCRIPTION: " + task["description"]
        + "\nREPO_ROOT: " + str(ROOT) + "\nOUTPUT_DIR: " + str(task_dir)
        + "\nRESULT_PATH: " + str(result_path)
        + "\nREQUIRED_EVIDENCE: " + ", ".join(task["expected"])
        + "\nRead the repo from REPO_ROOT; write ONLY within OUTPUT_DIR."
    )
    context = HERE/'engineering_context.md'
    if context.exists():
        prompt += '\n\nCURRENT VERIFIED LOCAL CONTEXT:\n' + context.read_text(encoding='utf-8')
    (task_dir / "task_prompt.txt").write_text(prompt, encoding="utf-8")
    out = subprocess_record(worker_argv(cfg) + [prompt],
                            None, cfg["worker_timeout_s"], ROOT)
    (task_dir / "dsh_stdout.txt").write_text(out["stdout"][:cfg["max_output_bytes"]], encoding="utf-8")
    (task_dir / "dsh_stderr.txt").write_text(out["stderr"][:cfg["max_output_bytes"]], encoding="utf-8")
    audit = audit_worker_result(task, task_dir, cfg.get('max_evidence_bytes', cfg["max_output_bytes"]))
    audit["process_rc"] = out["rc"]
    if out["rc"] != 0:
        audit["grade"] = "INCONCLUSIVE"
        audit["reason"] = "Harness execution did not complete, irrespective of worker claim"
    write_json(task_dir / "audit.json", audit)
    return audit


def codex_decision(round_dir: Path, cfg: dict, tasks: dict, completed: dict,
                   history: set, remaining_rounds: int):
    summary = {
        "round_results": {k: v for k, v in completed.items()},
        "used_task_ids": sorted(history),
        "remaining_rounds": remaining_rounds,
        "catalog": [dict(id=t["id"], stage=t["stage"], depends=t["depends"],
                         role=t["role"], description=t["description"])
                    for t in tasks.values()],
        "MANDATORY": "Manufacturing HOLD. SPICE evidence must be independently checked."
    }
    prompt = (HERE / "prompts/CODEX_DECISION.md").read_text(encoding="utf-8")
    prompt += "\n\nEVIDENCE AUDIT AND AVAILABLE TASKS:\n" + json.dumps(summary, ensure_ascii=False, indent=2)
    write_json(round_dir / "decision_input.json", summary)
    output_path = round_dir / "codex_decision.json"
    # Explicit OpenAI provider override prevents a DeepSeek configured default provider
    # from silently billing or running the decision on the wrong backend.
    # A named gpt profile does not exist on this machine. Explicit model/provider
    # overrides suffice; never require or overwrite an unrelated global profile.
    argv = ["codex", "exec", "--model",
            cfg["decision_model"], "--config", 'model_provider="openai"',
            "--sandbox", "read-only", "--output-schema",
            str(HERE / "decision.schema.json"), "--output-last-message",
            str(output_path), "-"]
    out = subprocess_record(argv, prompt, cfg["decision_timeout_s"], ROOT)
    (round_dir / "codex_stdout.txt").write_text(out["stdout"][:cfg["max_output_bytes"]], encoding="utf-8")
    (round_dir / "codex_stderr.txt").write_text(out["stderr"][:cfg["max_output_bytes"]], encoding="utf-8")
    if out["rc"] != 0 or not output_path.is_file():
        return {"decision": "HOLD", "rationale": "Codex execution failed or no schema output",
                "next_task_ids": [], "issues": [out["stderr"][-600:]],
                "controlling_assumptions": []}
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"decision": "HOLD", "rationale": "Unparseable Codex output",
                "next_task_ids": [], "issues": [], "controlling_assumptions": []}


def dry_run(cfg: dict, tasks: dict):
    print("DRY RUN / no model calls / no SPICE / no hardware")
    print("DeepSeek:", cfg["worker_binary"], cfg["worker_profile"],
          "(expected:", cfg["expected_worker_model"] + ")")
    print("Codex:", "current-session external review preferred; standalone codex exec --model",
          cfg["decision_model"], 'with explicit OpenAI provider and read-only sandbox')
    print("Initial tasks:", ", ".join(cfg["entry_task_ids"]))
    print("Budget:", cfg["max_rounds"], "rounds and", cfg["max_worker_calls"],
          "worker calls. Neither is a monetary ceiling.")
    print("No automatic vendor-model downloads, git pushes, PCB or hardware operations.")


def run_live(cfg: dict, tasks: dict, rounds: int, external_decisions=False, resume=None):
    preflight(cfg)
    if resume:
        folder = Path(resume).resolve()
        if not folder.is_relative_to((HERE/'runs').resolve()):
            raise ValueError('Resume must be inside runs')
        checkpoint = json.loads((folder/'checkpoint.json').read_text(encoding='utf-8'))
        if checkpoint['rounds'] != rounds or rounds > cfg['max_rounds'] or checkpoint['calls'] > cfg['max_worker_calls']:
            raise ValueError('Cannot change round budget on resume')
        manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        for name, digest in manifest['config_sha256'].items():
            if sha256(HERE/name) != digest:
                raise ValueError('Configuration changed since initial wave: '+name)
        complete = checkpoint['complete']
        history = set(checkpoint['history'])
        max_stage, calls, start_idx = checkpoint['max_stage'], checkpoint['calls'], checkpoint['next_idx']
        dec = json.loads((folder/('round_%02d' % start_idx)/'external_decision.json').read_text(encoding='utf-8'))
        validate_decision(dec,tasks,complete,max_stage,history)
        pending = dec['next_task_ids']
        write_json(folder/('round_%02d' % start_idx)/'validated_decision.json', dec)
        if dec['decision'] != 'CONTINUE' or start_idx >= rounds:
            write_json(folder/'run_summary.json', dict(tasks=complete,worker_calls=calls,rounds_used=start_idx,status='REVIEWED_STOPPED',decision=dec,manufacturing='HOLD',child_codex_calls=0))
            return folder
    else:
        start_idx = 0
    run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not resume:
        folder = HERE / "runs" / run_name
        folder.mkdir(parents=True, exist_ok=False)
    snapshot = {x.name: sha256(x) for x in
                (HERE / "config.json", HERE / "tasks.json",
                 HERE / "decision.schema.json")}
    if not resume: write_json(folder / "manifest.json", {
        "utc": run_name, "config_sha256": snapshot, "manufacturing": "HOLD",
        "physical_HV": "NOT_PERFORMED", "decision_model": cfg["decision_model"],
        "worker_expected_model": cfg["expected_worker_model"]
    })
    if not resume:
        pending = list(cfg["entry_task_ids"])
        complete, history, max_stage, calls = {}, set(), 0, 0
    for idx in range(start_idx, rounds):
        remaining = cfg["max_worker_calls"] - calls
        if remaining <= 0 or not pending:
            break
        current = pending[:remaining]
        round_dir = folder / ("round_%02d" % (idx + 1))
        round_dir.mkdir()
        from concurrent.futures import ThreadPoolExecutor
        for t_id in current:
            if not eligible(t_id, tasks, complete, max_stage, history):
                raise RuntimeError("Blocked task: "+t_id)
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {t_id: pool.submit(do_worker,tasks[t_id],round_dir,cfg) for t_id in current}
            for t_id, future in futures.items():
                result=future.result()
                complete[t_id]=result;history.add(t_id)
                max_stage=max(max_stage,tasks[t_id]['stage']); calls+=1
                print(t_id,result['grade'],flush=True)
        if external_decisions:
            write_json(folder/'checkpoint.json', dict(complete=complete,history=sorted(history),max_stage=max_stage,calls=calls,next_idx=idx+1,rounds=rounds))
            write_json(round_dir/'decision_input.json', dict(round_results=complete,used_task_ids=sorted(history),remaining_rounds=rounds-idx-1))
            write_json(folder/'run_summary.json', dict(tasks=complete,worker_calls=calls,rounds_used=idx+1,status='AWAITING_CURRENT_CODEX_REVIEW',manufacturing='HOLD',child_codex_calls=0))
            print('External Codex review required:', folder, flush=True)
            return folder
        dec = codex_decision(round_dir, cfg, tasks, complete, history,
                             rounds - idx - 1)
        try:
            validate_decision(dec, tasks, complete, max_stage, history)
        except ValueError as e:
            dec = {"decision": "HOLD", "rationale": "Gate rejected decision",
                   "next_task_ids": [], "issues": [str(e)], "controlling_assumptions": []}
        write_json(round_dir / "validated_decision.json", dec)
        print("CODEX:", dec["decision"], dec["rationale"][:300])
        if dec["decision"] != "CONTINUE":
            break
        pending = dec["next_task_ids"]
    write_json(folder / "run_summary.json", {
        "tasks": complete, "worker_calls": calls, "manufacturing": "HOLD",
        "real_170V_testing": "NOT_PERFORMED",
        "note": "Worker claims + file audits + Codex task routing, NOT electrical signoff."
    })
    print("Evidence:", folder)
    return folder


def main():
    ap = argparse.ArgumentParser(description="QS30 DeepSeek/ Codex bounded local workflow")
    ap.add_argument("--doctor", action="store_true", help="Check binaries/profile without model calls")
    ap.add_argument("--live", action="store_true", help="Actually invoke billable configured models")
    ap.add_argument("--accept-model-costs", action="store_true",
                    help="Explicit local consent for DeepSeek/Codex requests")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument('--external-decisions', action='store_true', help='Checkpoint for current Codex review; never launches child Codex')
    ap.add_argument('--resume', help='Resume checkpoint after external_decision.json is supplied')
    args = ap.parse_args()
    cfg, tasks = load_catalog()
    if args.rounds < 1 or args.rounds > cfg["max_rounds"]:
        ap.error("rounds outside configured limit")
    if args.doctor:
        print(preflight(cfg))
        return
    if not args.live:
        dry_run(cfg, tasks)
        return
    if not args.accept_model_costs:
        ap.error("Live model calls require --accept-model-costs")
    if os.environ.get('CODEX_THREAD_ID') and not args.external_decisions:
        ap.error('Inside a Codex session use --external-decisions to prevent nested Codex execution')
    if args.resume and not args.external_decisions:
        ap.error('--resume requires --external-decisions')
    run_live(cfg, tasks, args.rounds, args.external_decisions, args.resume)


if __name__ == "__main__":
    main()
