"""Check the exact authorized review, model accounting and passive scope."""
from orchestrate import HERE, read_json, sha256

R = HERE / "evidence/runs/authorized-g0-review"
TASKS = ["g0_device_evidence_challenge", "g0_fault_bounds_challenge"]


def main():
    summary = read_json(R / "run_summary.json")
    inputs = outputs = cache = count = 0
    for idx, task in enumerate(TASKS, 1):
        d = R / f"round_{idx:02}"
        p = d / task
        metadata = read_json(p / "input.json")
        assert sha256(p / "task_input.md") == metadata["prompt_sha256"]
        assert sha256(HERE / "harness_review.mjs") == metadata["adapter_sha256"]
        assert sha256(HERE / "config.json") == metadata["config_sha256"]
        assert sha256(HERE / "tasks.json") == metadata["tasks_sha256"]
        assert metadata["probe"]["provider_requests"] == 0
        receipt = read_json(p / "provider.json")["receipt"]
        assert receipt["model"] == "deepseek-v4-flash" and receipt["provider"] == "deepseek-official"
        assert receipt["http_status"] == 200 and receipt["requests"] == 1
        assert receipt["finish"] == ("max-tokens" if idx == 1 else "stop")
        usage = receipt["usage"]
        inputs += usage["inputTokens"]
        outputs += usage["outputTokens"]
        cache += usage.get("cacheReadTokens", 0)
        count += receipt["requests"]
        audit = read_json(p / "audit.json")
        assert audit["grade"] == "INCONCLUSIVE"
        for item, digest in audit["evidence_sha256"].items():
            assert sha256(p / item) == digest
        review = read_json(d / "codex_review.json")
        assert review["reviewed_evidence_sha256"] == sha256(p / "provider.json")
    assert count == summary["requests"] == 2
    assert inputs + outputs + cache == summary["total_tokens"] == 3830
    folder = R / "round_02/passive_fault_energy"
    pre = read_json(folder / "preregister.json")
    metrics = read_json(folder / "metrics.json")
    assert pre["circuit_sha256"] == sha256(folder / "circuit.cir")
    assert metrics["raw_sha256"] == sha256(folder / "circuit.raw")
    assert metrics["status"] == "LIMITED_PASS" and all(metrics["assertions"].values())
    assert read_json(R / "round_02/codex_review.json")["solver_metrics_sha256"] == sha256(folder / "metrics.json")
    assert summary["manufacturing"] == "ENGINEERING HOLD"
    print("Two provider receipts, raw wave, model/tool limits, accepted and rejected claims verified.")


if __name__ == "__main__":
    main()
