"""Provider-free deterministic tests for workflow controls."""
import json
import tempfile
import unittest
import shutil
import os
import subprocess
from unittest.mock import patch
import orchestrate as orch
from pathlib import Path
from orchestrate import (HERE, load_catalog, audit_worker_result, bounded_path,
                         eligible, validate_decision)


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.cfg, self.tasks = load_catalog()
        self.task = self.tasks["baseline_audit"]

    def test_baseline_never_released(self):
        self.assertEqual(self.cfg["manufacturing"], "HOLD")
        self.assertFalse(self.cfg["hardware_high_voltage"])
        self.assertEqual(self.cfg["decision_provider"], "openai")
        self.assertEqual(self.cfg["expected_worker_model"], "deepseek-flash")

    def test_stage_zero(self):
        self.assertTrue(eligible("baseline_audit", self.tasks, {}, 0, set()))
        self.assertFalse(eligible("zero_volt_startup", self.tasks, {}, 0, set()))

    def test_worker_uses_documented_profile_syntax(self):
        with patch.dict(os.environ, {'QS30_DSH_NODE':'node.exe','QS30_DSH_CLI':'bin.js','QS30_DSH_PATCH':'flash.yml','QS30_DSH_HOME':'private'}):
            self.assertEqual(orch.worker_argv(self.cfg), ['node.exe','bin.js','--profile','headless','--patch','flash.yml'])

    def test_profile_must_be_effective_model_not_catalog_string(self):
        text = '- id: agent-default-model\n  config:\n    provider: deepseek-official\n    model: other\n- id: catalog\n  model: deepseek-flash\n'
        with patch.object(orch.shutil,'which',return_value='binary'), patch.object(orch,'subprocess_record',return_value=dict(rc=0,stdout=text,stderr='')):
            with self.assertRaises(RuntimeError): orch.preflight(self.cfg)

    def test_timeout_retains_partial_evidence(self):
        err = subprocess.TimeoutExpired(['solver'],1,output=b'partial raw',stderr=b'last timestep')
        with patch.object(orch.subprocess,'run',side_effect=err):
            r=orch.subprocess_record(['solver'],None,1,HERE)
        self.assertEqual(r['stdout'],'partial raw')
        self.assertIn('last timestep',r['stderr'])

    def test_startup_requires_reference_and_cell(self):
        base={'power_candidate_review':{'grade':'CLAIMED_PASS_AUDITED_FILES'}}
        self.assertFalse(eligible('zero_volt_startup',self.tasks,base,2,{'lt3757a_reference'}))

    def test_external_review_resumes_with_same_budget_and_no_child_codex(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)
            for name in ('config.json','tasks.json','decision.schema.json'):
                shutil.copy2(HERE/name,fake/name)
            def worker(task,rd,cfg):
                return dict(task_id=task['id'],grade='CLAIMED_PASS_AUDITED_FILES')
            with patch.object(orch,'HERE',fake), patch.object(orch,'preflight'), patch.object(orch,'do_worker',side_effect=worker) as w, patch.object(orch,'codex_decision') as child:
                folder=orch.run_live(self.cfg,self.tasks,2,True)
                dec=dict(decision='CONTINUE',rationale='independent inventory check',next_task_ids=['lt3757a_reference'],issues=[],controlling_assumptions=[])
                orch.write_json(folder/'round_01/external_decision.json',dec)
                orch.run_live(self.cfg,self.tasks,2,True,str(folder))
                self.assertEqual(w.call_count,4)
                child.assert_not_called()
                dec.update(decision='HOLD',next_task_ids=[],rationale='Budget exhausted; electrical evidence incomplete')
                orch.write_json(folder/'round_02/external_decision.json',dec)
                orch.run_live(self.cfg,self.tasks,2,True,str(folder))
                self.assertEqual(w.call_count,4)
                with self.assertRaises(ValueError):
                    orch.run_live(self.cfg,self.tasks,3,True,str(folder))

    def test_requires_dependencies(self):
        done = {}
        self.assertFalse(eligible("lt3757a_reference", self.tasks, done, 0, set()))
        done["vendor_models"] = {"grade": "CLAIMED_PASS_AUDITED_FILES"}
        self.assertTrue(eligible("lt3757a_reference", self.tasks, done, 0, set()))
        self.assertFalse(eligible("lt3757a_reference", self.tasks, done, 0,
                                  {"lt3757a_reference"}))

    def test_reject_fabricated_or_missing_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "result.json").write_text(json.dumps({
                "task_id": self.task["id"], "status": "PASS",
                "notes": "claim", "evidence_files": ["inventory.md"]}), encoding="utf-8")
            audit = audit_worker_result(self.task, root, 100000)
            self.assertEqual(audit["grade"], "INCONCLUSIVE")
            (root / "inventory.md").write_text("evidence", encoding="utf-8")
            audit = audit_worker_result(self.task, root, 100000)
            self.assertEqual(audit["grade"], "CLAIMED_PASS_AUDITED_FILES")

    def test_spice_must_have_metrics(self):
        t = self.tasks["device_cells"]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for f in t["expected"]:
                (root / f).write_text("example", encoding="utf-8")
            (root / "result.json").write_text(json.dumps({
                "task_id": t["id"], "status": "PASS", "notes": "claim",
                "model_hashes": {"D20": "abcd"},
                "evidence_files": t["expected"]}), encoding="utf-8")
            self.assertEqual(audit_worker_result(t, root, 100000)["grade"], "INCONCLUSIVE")
            (root / "metrics.json").write_text(json.dumps({
                "solver": "ngspice", "exit_code": 0, "endpoint_reached": True,
                "maxstep_s": 1e-9, "evaluation_status": "LIMITED_PASS",
                "assertions": [{"name": "end", "passed": True}]}), encoding="utf-8")
            self.assertEqual(audit_worker_result(t, root, 100000)["grade"],
                             "CLAIMED_PASS_AUDITED_FILES")

    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                bounded_path(Path(d), "../../secret")
            with self.assertRaises(ValueError):
                bounded_path(Path(d), "/tmp/secret")

    def test_disallow_codex_arbitrary_task(self):
        dec = {"decision": "CONTINUE", "rationale": "test",
               "next_task_ids": ["delete_repo"], "issues": [],
               "controlling_assumptions": []}
        with self.assertRaises(ValueError):
            validate_decision(dec, self.tasks, {}, 0, set())

    def test_disallow_codex_jump(self):
        dec = {"decision": "CONTINUE", "rationale": "test",
               "next_task_ids": ["closed_loop_corners"], "issues": [],
               "controlling_assumptions": []}
        with self.assertRaises(ValueError):
            validate_decision(dec, self.tasks, {}, 0, set())

    def test_no_repeated_tasks(self):
        dec = {"decision": "CONTINUE", "rationale": "test",
               "next_task_ids": ["baseline_audit", "baseline_audit"],
               "issues": [], "controlling_assumptions": []}
        with self.assertRaises(ValueError):
            validate_decision(dec, self.tasks, {}, 0, set())

    def test_no_unexpected_file(self):
        self.assertTrue((HERE / "prompts" / "MASTER_PROMPT.md").is_file())


    def test_spice_failed_assertion_forbidden(self):
        t = self.tasks["device_cells"]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for f in t["expected"]:
                (root / f).write_text("example", encoding="utf-8")
            (root / "result.json").write_text(json.dumps({
                "task_id": t["id"], "status": "PASS", "notes": "claimed pass",
                "model_hashes": {"MOS": "sha"},
                "evidence_files": t["expected"]}), encoding="utf-8")
            (root / "metrics.json").write_text(json.dumps({
                "solver": "ngspice", "exit_code": 0, "endpoint_reached": True,
                "maxstep_s": 1e-9, "evaluation_status": "LIMITED_PASS",
                "assertions": [{"name": "peak", "passed": False}]}), encoding="utf-8")
            self.assertEqual(audit_worker_result(t, root, 100000)["grade"], "INCONCLUSIVE")

    def test_stage3_requires_model_and_cell_evidence(self):
        base = {x: {"grade": "CLAIMED_PASS_AUDITED_FILES"} for x in
                ["baseline_audit", "vendor_models", "acceptance_budget",
                 "power_candidate_review", "zero_volt_startup"]}
        history = set(base) | {"lt3757a_reference"}
        self.assertFalse(eligible("closed_loop_corners", self.tasks, base, 2, history))
        base["lt3757a_reference"] = {"grade": "CLAIMED_PASS_AUDITED_FILES"}
        self.assertFalse(eligible("closed_loop_corners", self.tasks, base, 2, history))
        base["device_cells"] = {"grade": "CLAIMED_PASS_AUDITED_FILES"}
        self.assertTrue(eligible("closed_loop_corners", self.tasks, base, 2,
                                 history | {"device_cells"}))

    def test_mocked_two_wave_orchestration_without_model_calls(self):
        with tempfile.TemporaryDirectory() as d:
            fake_here = Path(d)
            for fn in ("config.json", "tasks.json", "decision.schema.json"):
                shutil.copy2(HERE / fn, fake_here / fn)
            responses = [
                {"decision": "CONTINUE", "rationale": "model inventory accepted",
                 "next_task_ids": ["lt3757a_reference"], "issues": [],
                 "controlling_assumptions": []},
                {"decision": "HOLD", "rationale": "no electrical proof yet",
                 "next_task_ids": [], "issues": [],
                 "controlling_assumptions": []}
            ]
            def mock_worker(task, round_dir, cfg):
                return {"task_id": task["id"], "grade": "CLAIMED_PASS_AUDITED_FILES"}
            with patch.object(orch, "HERE", fake_here), \
                 patch.object(orch, "preflight", return_value="mocked preflight"), \
                 patch.object(orch, "do_worker", side_effect=mock_worker) as worker, \
                 patch.object(orch, "codex_decision", side_effect=responses) as decision:
                orch.run_live(self.cfg, self.tasks, 2)
                self.assertEqual(worker.call_count, 4)
                self.assertEqual(decision.call_count, 2)
            runs = list((fake_here / "runs").iterdir())
            self.assertEqual(len(runs), 1)
            summary = json.loads((runs[0] / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["worker_calls"], 4)
            self.assertEqual(summary["manufacturing"], "HOLD")
            last = json.loads((runs[0] / "round_02" / "validated_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(last["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
