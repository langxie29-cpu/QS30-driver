import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import headless
import orchestrate
from orchestrate import engine


class Controls(TestCase):
    def setUp(self):
        self.cfg, self.tasks = orchestrate.load_catalog()

    def test_six_round_cap_and_eighteen_call_cap(self):
        for rounds, calls, count in ((6, 17, 2), (5, 18, 1)):
            with TemporaryDirectory() as root:
                state = dict(status="READY", rounds=rounds, calls=calls,
                             pending=list(self.tasks)[:count])
                with patch.object(engine, "do_worker") as worker:
                    engine.execute_round(Path(root), state, self.cfg, self.tasks, [], {})
                worker.assert_not_called()
                self.assertEqual(state["status"], "STOP")

    def test_real_work_allowance_and_no_duplicate(self):
        ids = self.cfg["entry_task_ids"]
        self.assertTrue(all(engine.eligible(x,self.tasks,set(),set()) for x in ids))
        self.assertFalse(engine.eligible(ids[0],self.tasks,set(),{ids[0]}))
        self.assertFalse(engine.eligible("native_eda",self.tasks,set(),set()))

    def test_resume_refuses_interruption_and_evidence_mutation(self):
        with TemporaryDirectory() as root:
            folder = Path(root)
            state = engine.new_state(self.cfg, {"head":"pinned"},{"model":"pinned"})
            engine.checkpoint(folder,state,self.cfg)
            engine.verify_resume(folder,state,self.cfg,state["snapshot"],state["identity"])
            interrupted = copy.deepcopy(state)
            interrupted["status"] = "RUNNING"
            with self.assertRaisesRegex(ValueError,"Interrupted"):
                engine.verify_resume(folder,interrupted,self.cfg,state["snapshot"],state["identity"])
            (folder/"unsolicited").write_text("drift")
            with self.assertRaisesRegex(ValueError,"drift"):
                engine.verify_resume(folder,state,self.cfg,state["snapshot"],state["identity"])

    def test_hold_and_stop_never_launch(self):
        for status in ("HOLD","STOP"):
            with patch.object(engine,"do_worker") as worker:
                engine.execute_round(Path("."),{"status":status},self.cfg,self.tasks,[],{})
                worker.assert_not_called()

    def test_profile_refuses_any_unapproved_plugin(self):
        rows = [f"- id: {k}\n  name: '@deepseek-ai/{v}'" for k,v in headless.ACTIVE.items()]
        for key, value in {"agent-default-model":"provider: deepseek-official\n    model: deepseek-v4-flash",
                           "llm-deepseek":"baseURL: https://api.deepseek.com",
                           "tools":"mode: native"}.items():
            i = list(headless.ACTIVE).index(key)
            rows[i] += "\n  config:\n    " + value
        approved = "\n".join(rows)+"\n"
        headless.validate_config(approved)
        with self.assertRaises(ValueError):
            headless.validate_config(approved+"- id: tool-fs\n  name: '@deepseek-ai/dsh-tool-fs'\n")
        headless.validate_config(approved+"- id: tool-fs\n  disabled: true\n")

    def test_worker_cannot_claim_raw_solver_evidence(self):
        with TemporaryDirectory() as root:
            task = self.tasks["cost_market"]
            data = {"result":{"task_id":task["id"],"status":"PASS","model_hashes":{},"solver":"ngspice",
                              "evidence_files":["inventory.md","sources.json"]},
                    "inventory":"Only static review","sources":[{"locator":"line 1"}]}
            with self.assertRaisesRegex(ValueError,"unsupported evidence"):
                headless.ingest(engine,task,Path(root),json.dumps(data).encode())
            self.assertFalse((Path(root)/"result.json").exists())

    def test_paths_are_restricted(self):
        with self.assertRaises(ValueError):
            headless.audit_inputs(engine,["../.credentials.yaml"])
