"""Provider-free R8 tests. No simulator, credentials, network or hardware."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import orchestrate as o


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.tasks = o.load_catalog()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.initial = self.cfg["entry_task_ids"][0]
        self.later = "four_channel_fixture"
        self.stage0 = set(self.cfg["entry_task_ids"])

    def decision(self, state="CONTINUE", following=()):
        return dict(decision=state, rationale="Independent fixture review",
                    next_task_ids=list(following), issues=[], controlling_assumptions=[])

    def result(self, task_id, files, **other):
        payload = dict(task_id=task_id, status="PASS", notes="Fixture",
                       evidence_files=files, source_urls=["https://example.com/source"], solver="none",
                       model_hashes={}, blocking_issues=[])
        o.write_json(self.root / "result.json", {**payload, **other})

    def test_stage_and_dependencies(self):
        self.assertTrue(o.eligible(self.initial, self.tasks, set(), set()))
        self.assertFalse(o.eligible(self.later, self.tasks, self.stage0 - {self.initial}, self.stage0))
        self.assertFalse(o.eligible(self.later, self.tasks, self.stage0, self.stage0))
        self.assertFalse(o.eligible(self.later, self.tasks, self.stage0, self.stage0, gates={"G0": "REWORK"}))
        self.assertTrue(o.eligible(self.later, self.tasks, self.stage0, self.stage0, gates={"G0": "ACCEPT_CANDIDATE"}))
        self.assertFalse(o.eligible("power_architecture", self.tasks, self.stage0, self.stage0))

    def test_all_prior_engineering_gates_are_required(self):
        all_tasks = set(self.tasks)
        g0_g1 = {"G0": "ACCEPT_CANDIDATE", "G1": "LIMITED_PASS"}
        self.assertTrue(o.eligible("thirty_channel_eda", self.tasks, all_tasks, set(), gates=g0_g1))
        self.assertFalse(o.eligible("power_architecture", self.tasks, all_tasks, set(), gates=g0_g1))
        full = {**g0_g1, "G2": "LIMITED_PASS"}
        self.assertTrue(o.eligible("power_architecture", self.tasks, all_tasks, set(), gates=full))

    def test_repeated_task(self):
        self.assertFalse(o.eligible(self.initial, self.tasks, set(), {self.initial}))
        with self.assertRaises(ValueError):
            o.validate_decision(self.decision(following=[self.initial, self.initial]), self.tasks, set(), set(), 3, 8)

    def test_manufacturing_and_unlisted_actions(self):
        self.assertEqual(self.cfg["manufacturing"], "ENGINEERING HOLD")
        self.assertIs(self.cfg["hardware_high_voltage"], False)
        for task in ("fabricate", "buy_parts", "physical_hv", "final_architecture_decision"):
            self.assertFalse(o.eligible(task, self.tasks, set(self.tasks), set()))
        with self.assertRaises(ValueError):
            o.validate_decision({**self.decision("STOP"), "manufacturing": "APPROVED"},
                                self.tasks, set(), set(), 0, 0)

    def test_unsupported_paths(self):
        for path in ("../../secret", "/tmp/secret", "C:/x", "a\\b", "x//a", "nul", "a/.", "a:name", "log."):
            with self.subTest(path=path), self.assertRaises(ValueError):
                o.bounded_path(self.root, path)

    def test_symlink_escape(self):
        link = self.root / "link"
        with tempfile.TemporaryDirectory() as target:
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                self.skipTest("Host restricts symlink creation")
            with self.assertRaises(ValueError):
                o.bounded_path(self.root, "link/a")

    def test_missing_evidence(self):
        self.result(self.initial, ["inventory.md", "sources.json"])
        self.assertEqual(o.audit_worker_result(self.tasks[self.initial], self.root, 1024)["grade"], "INCONCLUSIVE")

    def test_invalid_json(self):
        for value in ('{', '{"status": "PASS", "status": "FAIL"}', '{"x":NaN}'):
            (self.root / "result.json").write_text(value)
            self.assertEqual(o.audit_worker_result(self.tasks[self.initial], self.root, 1024)["grade"], "INCONCLUSIVE")

    def test_analysis_is_audited_claim_only(self):
        (self.root / "inventory.md").write_text("reconciled")
        o.write_json(self.root / "sources.json", [dict(source="pinned.xml", assertion="count is nine")])
        self.result(self.initial, ["inventory.md", "sources.json"])
        result = o.audit_worker_result(self.tasks[self.initial], self.root, 1024)
        self.assertEqual(result["grade"], "CLAIMED_PASS_AUDITED_FILES")
        self.assertFalse(o.eligible(self.later, self.tasks, set(), self.stage0))

    def test_spice_requires_real_contract(self):
        task = {"id": "fixture_spice", "kind": "spice", "expected": list(o.SPICE_FILES)}
        for name in ("circuit.cir", "run.log", "circuit.raw", "device.lib"):
            (self.root / name).write_text("synthetic test fixture")
        o.write_json(self.root / "preregister.json", dict(acceptance=["end"], target_end_s=.1, maxstep_s=.0001))
        o.write_json(self.root / "model_sources.json", {"controller": dict(
            file="device.lib", source="test", version="v1", license="fixture")})
        self.result(task["id"], ["circuit.cir", "run.log", "circuit.raw", "device.lib", "model_sources.json", "metrics.json"],
                    solver="sim v1", model_hashes={"controller": o.sha256(self.root / "device.lib")})
        metrics = dict(solver="sim v1", exit_code=0, endpoint_reached=True, endpoint_s=.1,
                       target_end_s=.1, maxstep_s=.0001, evaluation_status="LIMITED_PASS",
                       assertions=[dict(name="end", passed=True)])
        o.write_json(self.root / "metrics.json", metrics)
        self.assertEqual(o.audit_worker_result(task, self.root, 5000)["grade"], "CLAIMED_PASS_AUDITED_FILES")
        for change in (dict(exit_code=False), dict(endpoint_s=.05), dict(target_end_s=.05),
                       dict(assertions=[dict(name="other", passed=True)])):
            o.write_json(self.root / "metrics.json", {**metrics, **change})
            self.assertEqual(o.audit_worker_result(task, self.root, 5000)["grade"], "INCONCLUSIVE")
        o.write_json(self.root / "metrics.json", metrics)
        (self.root / "device.lib").write_text("modified library")
        self.assertEqual(o.audit_worker_result(task, self.root, 5000)["grade"], "INCONCLUSIVE")

    def identity(self):
        return dict(model=self.cfg["worker_model"], provider=self.cfg["worker_provider"],
                    endpoint="https://api.deepseek.com", policy={
                        "repository": "read-only", "writes": "task-directory",
                        "execution": "registered-engineering-tools-only", "network": "read-only-sources",
                        "manufacturing": False, "hardware": False, "background_model_requests": False})

    def test_model_and_provider_identity_exact(self):
        good = self.identity()
        self.assertEqual(o.effective_identity(good, self.cfg), good)
        for key, value in (("provider", "openai"), ("endpoint", "https://api.deepseek.com.other"),
                           ("model", "deepseek-flash"), ("policy", {})):
            with self.assertRaises(ValueError):
                o.effective_identity({**good, key: value, "notes": "deepseek-v4-flash"}, self.cfg)

    def test_doctor_no_fallback_or_credentials_output(self):
        probe = dict(rc=1, failure="EXECUTION_FAIL", stderr=b"exists and is not a symlink SECRET")
        with patch.object(o, "run_process", return_value=probe) as call:
            r = o.preflight(self.cfg, ["dsh"])
            self.assertEqual(r["status"], "HOLD")
            self.assertNotIn("SECRET", str(r))
            self.assertEqual(call.call_args.args[0], ["dsh", "--profile", "headless", "--dump-config"])

    def test_timeout(self):
        receipt = o.run_process([sys.executable, "-c", "import time; time.sleep(2)"], self.root, .15, 1000)
        self.assertEqual(receipt["failure"], "PROCESS_TIMEOUT")

    def test_output_budget_combined(self):
        snippet = "import sys; print('a'*30000); print('b'*30000, file=sys.stderr)"
        result = o.run_process([sys.executable, "-c", snippet], self.root, 4, 118)
        self.assertEqual(result["failure"], "OUTPUT_CAP")
        self.assertLessEqual(len(result["stdout"]) + len(result["stderr"]), 118)

    def test_hold_and_stop(self):
        for state in ("HOLD", "STOP"):
            o.validate_decision(self.decision(state), self.tasks, set(), set(), 0, 0)
            with self.assertRaises(ValueError):
                o.validate_decision(self.decision(state, [self.initial]), self.tasks, set(), set(), 4, 12)

    def test_budget_exhausted(self):
        for rounds, calls in ((0, 2), (1, 0)):
            with self.assertRaises(ValueError):
                o.validate_decision(self.decision(following=[self.initial]), self.tasks, set(), set(), rounds, calls)
        state = o.new_state(self.cfg, {}, {})
        state["calls"] = self.cfg["max_worker_calls"]
        with patch.object(o, "do_worker") as work:
            o.execute_round(self.root, state, self.cfg, self.tasks, [], {})
        work.assert_not_called()
        self.assertEqual(state["status"], "STOP")

    def test_resume_seals_history_snapshot_and_identity(self):
        snapshot, identity = {"head": "fixture"}, self.identity()
        state = o.new_state(self.cfg, snapshot, identity)
        (self.root / "previous.txt").write_text("raw")
        o.checkpoint(self.root, state, self.cfg)
        o.verify_resume(self.root, state, self.cfg, snapshot, identity)
        for new in ({"head": "changed"}, {"head": "fixture", "models": {}}):
            with self.assertRaises(ValueError):
                o.verify_resume(self.root, state, self.cfg, new, identity)
        (self.root / "previous.txt").write_text("rewritten")
        with self.assertRaises(ValueError):
            o.verify_resume(self.root, state, self.cfg, snapshot, identity)

    def test_resume_interrupted_attempt_is_not_replayed(self):
        state = o.new_state(self.cfg, {}, {})
        state["status"] = "RUNNING"
        o.checkpoint(self.root, state, self.cfg)
        with self.assertRaises(ValueError):
            o.verify_resume(self.root, state, self.cfg, {}, {})

    def test_no_billing_without_permission(self):
        output = subprocess.run([sys.executable, str(o.HERE / "orchestrate.py"), "--live"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(output.returncode, 2)
        self.assertIn("--accept-model-costs", output.stderr)
        self.assertEqual(o.dry_run(self.cfg, self.tasks)["model_requests"], 0)

    def test_mocked_two_rounds_and_review_binding(self):
        run = self.root / "live-fixture"
        run.mkdir()
        state = o.new_state(self.cfg, {}, self.identity())
        review_path, dec_path = self.root / "review.json", self.root / "decision.json"
        def worker(task, *_):
            return {"task_id": task["id"], "grade": "CLAIMED_PASS_AUDITED_FILES"}
        with patch.object(o, "verify_checkout"), patch.object(o, "do_worker", side_effect=worker) as mock:
            o.execute_round(run, state, self.cfg, self.tasks, [], self.identity())
            self.assertEqual(state["status"], "AWAITING_CODEX")
            self.assertEqual(state["calls"], 4)
            reviewed = {k: o.sha256(run / rel) for k, rel in state["history"].items()}
            review = dict(model="gpt-6.1-sol", provider="openai", approved_audits=reviewed,
                          independent_evidence_review="Read installed mock evidence independently",
                          gate_decisions={"G0": "ACCEPT_CANDIDATE"})
            o.write_json(review_path, {**review, "approved_audits": {self.initial: "bad"}})
            o.write_json(dec_path, self.decision(following=[self.later]))
            with self.assertRaises(ValueError):
                o.apply_external(run, state, self.cfg, self.tasks, review_path, dec_path)
            o.write_json(review_path, {**review, "gate_decisions": {"G0": "REWORK"}})
            with self.assertRaises(ValueError):
                o.apply_external(run, state, self.cfg, self.tasks, review_path, dec_path)
            o.write_json(review_path, review)
            o.apply_external(run, state, self.cfg, self.tasks, review_path, dec_path)
            o.verify_resume(run, state, self.cfg, {}, self.identity())
            o.execute_round(run, state, self.cfg, self.tasks, [], self.identity())
            self.assertEqual(mock.call_count, 5)
            o.write_json(dec_path, self.decision("HOLD"))
            o.apply_external(run, state, self.cfg, self.tasks, review_path, dec_path)
            o.execute_round(run, state, self.cfg, self.tasks, [], self.identity())
            self.assertEqual(mock.call_count, 5)
            self.assertEqual(state["status"], "HOLD")
            self.assertEqual(state["decisions"], 2)

    def test_worker_usage_unknown_and_receipt(self):
        p = self.root / "receipt.json"
        self.assertIsNone(o.usage_from_host(p, self.cfg)["tokens"])
        self.assertEqual(o.usage_from_host(p, self.cfg)["cost"], "COST_UNKNOWN")
        o.write_json(p, dict(requests=2, failed_requests=1, tokens=11, model="deepseek-v4-flash", provider="deepseek-official"))
        self.assertEqual(o.usage_from_host(p, self.cfg)["tokens"], 11)


if __name__ == "__main__":
    unittest.main()
