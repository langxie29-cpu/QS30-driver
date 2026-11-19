"""Verify sealed source references, phase outcomes and deterministic R8 evidence."""
import csv
import hashlib
import subprocess

from gate0_screen import HERE, read_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(name):
    with (HERE / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def verify():
    root = HERE / "evidence/runs/offline-discrete-g0"
    summary = read_json(root / "run_summary.json")
    assert summary["status"] == "HOLD" and summary["G0"] == "REWORK"
    assert summary["worker_calls"] == 0 and summary["formal_decision_rounds"] == 0
    assert len(list(root.glob("round_*/decision.json"))) == summary["local_research_rounds"]
    for folder in sorted(root.glob("round_*/*")):
        if not folder.is_dir():
            continue
        job, receipt = (read_json(folder / name) for name in ("input.json", "receipt.json"))
        assert job["task_id"] == receipt["task_id"] == folder.name
        assert receipt["worker_invoked"] is False
        for filename, expected in (job["configuration"] | receipt["artifacts_sha256"]).items():
            assert digest(HERE / filename) == expected, filename

    baseline = read_json(HERE / "evidence/r7_review_manifest.json")
    assert baseline["baseline_sha"] == summary["baseline"] == baseline["remote_base_sha"]
    for item in baseline["scoped_reviewed_r6_r7_sources"]:
        data = subprocess.check_output(["git", "cat-file", "blob",
                                       f"{baseline['baseline_sha']}:{item['file']}"], cwd=HERE.parents[2])
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["file"]

    mapping = read_csv("30_CHANNEL_PIN_MAPPING.csv")
    assert len(mapping) == 32
    assert {r["cathode_net"] for r in mapping[:-2]} == {f"K{t}_{d}" for t in range(1,4) for d in range(10)}
    assert len({(r["dual_transistor"],r["die"]) for r in mapping[:-2]}) == 30
    assert all(r["status"] == "FORCED_ZERO_IN_FRAME_AND_NO_CONNECTION" for r in mapping[-2:])

    prices = read_csv("DRIVER_COST_COMPARISON.csv")
    assert len(prices) == 16 and {r["sets"] for r in prices} == {"1","3","5","10"}
    assert all(r["FULL_SYSTEM_COST"] == "UNKNOWN" for r in prices)
    assert all(int(r["boards"]) == 3*int(r["sets"]) for r in prices)
    assert len(read_csv("5V_POWER_BUDGET.csv")) == 96
    assert not list(HERE.rglob("*.kicad_pcb"))
    stage = read_json(HERE / "GATE_STATUS.json")
    assert stage["gates"]["G0"]["status"] == "REWORK"
    assert all(stage["gates"][g]["status"] == "NOT_ENTERED" for g in ("G1","G2","G3"))
    print("Verified two offline rounds, exact R7 provenance, 32-bit map and qualification HOLD")


if __name__ == "__main__":
    verify()
