"""Validate result.json against the worker output contract.

Checks: UTF-8 parse, exact task_id, allowed status, required keys present,
all evidence_files exist INSIDE this output directory, no absolute/escaping paths.
"""
import json
import os

RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"
RESULT = os.path.join(RUN, "result.json")

errors = []
with open(RESULT, encoding="utf-8") as f:
    r = json.load(f)

if r.get("task_id") != "baseline_audit":
    errors.append("task_id mismatch: %r" % r.get("task_id"))
if r.get("status") not in ("PASS", "FAIL", "INCONCLUSIVE"):
    errors.append("bad status: %r" % r.get("status"))
for k in ("task_id", "status", "notes", "evidence_files", "source_urls",
          "solver", "model_hashes", "blocking_issues"):
    if k not in r:
        errors.append("missing key: %s" % k)

missing = []
outside = []
for rel in r.get("evidence_files", []):
    if os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/"):
        outside.append(rel)
        continue
    if not os.path.exists(os.path.join(RUN, rel)):
        missing.append(rel)

if missing:
    errors.append("missing evidence files: %s" % missing)
if outside:
    errors.append("evidence paths escape output dir: %s" % outside)

if "inventory.md" not in r.get("evidence_files", []):
    errors.append("required evidence inventory.md not listed")
if not os.path.exists(os.path.join(RUN, "inventory.md")):
    errors.append("required evidence inventory.md not on disk")

# model_hashes format sanity
for name, h in r.get("model_hashes", {}).items():
    if not (isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)):
        errors.append("bad sha256 for %s: %r" % (name, h))

report = {
    "errors": errors,
    "ok": len(errors) == 0,
    "status": r.get("status"),
    "evidence_count": len(r.get("evidence_files", [])),
    "model_hash_count": len(r.get("model_hashes", {})),
    "blocking_issue_count": len(r.get("blocking_issues", [])),
}
with open(os.path.join(RUN, "validate_result.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1)
