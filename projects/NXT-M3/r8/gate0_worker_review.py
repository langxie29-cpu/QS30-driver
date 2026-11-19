"""Two response-only Gate 0 reviews using the installed Harness transport."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from orchestrate import HERE, ROOT, audit_worker_result, git, load_catalog, read_json, run_process, sha256, write_json

RUN = HERE / "evidence/runs/authorized-g0-review"
WORK = {
    1: ("g0_device_evidence_challenge", "g0_device_evidence_challenge.md"),
    2: ("g0_fault_bounds_challenge", "g0_fault_bounds_challenge.md"),
}


def run(args):
    cfg, _ = load_catalog()
    actual_head = git("rev-parse", "HEAD")
    if git("branch", "--show-current") != cfg["branch"]:
        raise ValueError("R8 worktree branch mismatch")
    base = args.install.resolve()
    node = base / "runtime/node-v24.19.0-win-x64/node.exe"
    launcher = HERE / "harness_review.mjs"
    process = run_process([str(node), str(launcher), str(base), "probe"], cwd=ROOT,
                          timeout=30, cap=cfg["max_output_bytes"])
    if process["rc"] or process["failure"]:
        print(process["stdout"].decode("utf-8", errors="replace"))
        return 2
    if args.round is None:
        print(process["stdout"].decode("utf-8").strip())
        return 0
    if not args.accept_model_costs:
        raise ValueError("Billable review requires --accept-model-costs")
    if args.round == 2:
        previous = RUN / "round_01"
        decision = read_json(previous / "codex_review.json")
        prior = previous / WORK[1][0]
        if (decision["decision"], decision["next_task"]) != ("CONTINUE", WORK[2][0]):
            raise ValueError("Second round requires independent approval of the first")
        if decision["reviewed_evidence_sha256"] != sha256(prior / "provider.json"):
            raise ValueError("Prior raw evidence changed")
    task_id, filename = WORK[args.round]
    folder = RUN / f"round_{args.round:02}" / task_id
    folder.mkdir(parents=True, exist_ok=False)
    prompt = HERE / "prompts" / filename
    input_path = folder / "task_input.md"
    input_path.write_bytes(prompt.read_bytes())
    started = datetime.now(timezone.utc).isoformat()
    write_json(folder / "input.json", dict(task_id=task_id, started_utc=started, git_head=actual_head,
        baseline=cfg["baseline_sha"], config_sha256=sha256(HERE / "config.json"), tasks_sha256=sha256(HERE / "tasks.json"),
        adapter_sha256=sha256(launcher), prompt_sha256=sha256(input_path), probe=json.loads(process["stdout"]),
        max_requests=1, timeout_s=cfg["worker_timeout_s"], manufacturing=cfg["manufacturing"]))
    out = run_process([str(node), str(launcher), str(base), "call", str(input_path)], cwd=folder,
                      timeout=cfg["worker_timeout_s"], cap=cfg["max_output_bytes"])
    for stream in ("stdout","stderr"):
        (folder / (stream + ".txt")).write_bytes(out.pop(stream))
    provider_path = folder / "provider.json"
    try:
        provider = json.loads((folder / "stdout.txt").read_bytes())
    except (OSError, ValueError):
        provider = dict(failure="NO_PROVIDER_RECEIPT")
    write_json(provider_path, provider)
    text = "".join(row["text"] for row in provider.get("events", []) if row["type"] == "text-delta").strip()
    evidence = ["provider.json"]
    if text:
        (folder / "analysis.md").write_text(text + "\n", encoding="utf-8", newline="\n")
        evidence.append("analysis.md")
    out["head_after"] = git("rev-parse", "HEAD")
    if out["head_after"] != actual_head:
        out["failure"] = "WORKTREE_DRIFT"
    write_json(folder / "process.json", out)
    write_json(folder / "result.json", dict(task_id=task_id, status="INCONCLUSIVE",
        notes="Model engineering review. Independent review and device qualification required.",
        evidence_files=evidence, source_urls=[], solver="none", model_hashes={},
        blocking_issues=[provider.get("failure", "Engineering gate requires independent review")]))
    task = dict(id=task_id, kind="analysis", expected=[])
    audit = audit_worker_result(task, folder, cfg["max_evidence_bytes"])
    audit["process_exit"] = out["rc"]
    audit["process_failure"] = out["failure"]
    write_json(folder / "audit.json", audit)
    print(f"{task_id}: {audit['grade']}; evidence at {folder.relative_to(HERE)}")
    return 0 if out["rc"] == 0 and not out["failure"] and not provider.get("failure") else 2


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--install", required=True, type=Path)
    cli.add_argument("--round", type=int, choices=WORK)
    cli.add_argument("--accept-model-costs", action="store_true")
    raise SystemExit(run(cli.parse_args()))
