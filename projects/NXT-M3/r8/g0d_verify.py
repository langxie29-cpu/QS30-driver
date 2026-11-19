"""Recheck the G0D checkpoint and passive energy evidence without provider calls."""
import argparse
import csv
from pathlib import Path

from g0d_residual_energy import CONFIG, OLD, WAVEFORM_READER, effective_cases, integrate, traces
from orchestrate import HERE, bounded_path, dry_run, eligible, load_catalog, read_json, sha256, validate_decision

RUN = HERE / "evidence/runs/g0d-offline"
TEST = RUN / "round_02/RESIDUAL_ENERGY_FAULT_TEST"
TASKS = {
    "g0d_archive_qualification": {"kind": "research", "stage": 0, "depends": []},
    "residual_energy_fault_test": {"kind": "spice", "stage": 0, "depends": ["g0d_archive_qualification"]},
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def scheduler_preview(frozen):
    limits = frozen["limits"]
    config, _ = load_catalog()
    version = dict(config, baseline_sha=frozen["baseline_sha"],
                   entry_task_ids=[name for name in TASKS if eligible(name, TASKS, set(), set())],
                   max_rounds=limits["max_decision_rounds"], max_worker_calls=limits["max_worker_calls"])
    check(not limits["billable_calls_authorized_for_g0d"] and frozen["manufacturing"] == "ENGINEERING HOLD",
          "Current G0D receipt must retain offline-only mode and ENGINEERING HOLD")
    check(not eligible("residual_energy_fault_test", TASKS, set(), set()),
          "Bounded LTspice study must depend on original waveform review")
    return {**dry_run(version, TASKS), "dispatch": "offline host only", "tasks": TASKS,
            "authorization": "not confirmed for G0D"}


def audit():
    frozen = read_json(CONFIG)
    receipt = read_json(RUN / "run_summary.json")
    check(receipt["dry_run"] == scheduler_preview(frozen), "Dry-run receipt changed")
    check(receipt["worker_requests"] == 0 and receipt["worker_tokens"] == 0, "Unexpected Worker consumption")
    for relative, expected in read_json(RUN / "sha256.json").items():
        path = bounded_path(HERE, relative)
        check(path.is_file() and sha256(path) == expected, f"Evidence changed: {relative}")
    reader = read_json(RUN / "sources.json")["integration_reader"]
    check(sha256(WAVEFORM_READER) == reader["sha256"], "Frozen R7 raw reader changed")
    recorded = read_json(TEST / "preregister.json")
    check(recorded["cfg"] == frozen and recorded["input_config_sha256"] == sha256(CONFIG),
          "Frozen acceptance criteria changed")
    raw = TEST / "circuit.raw"
    metrics = read_json(TEST / "metrics.json")
    check(read_json(TEST / "process.json")["exit_code"] == 0 and metrics["raw_sha256"] == sha256(raw)
          and metrics["log_sha256"] == sha256(TEST / "circuit.log")
          and recorded["generated_deck_sha256"] == sha256(TEST / "circuit.cir"), "Solver file mismatch")
    with traces(raw) as (_, datum, count, _):
        check(count == metrics["grid"]["points"] and datum(count-1)[0] == frozen["limits"]["endpoint_s"],
              "Incomplete native waveform")
    cases = {case["id"]: case for case in effective_cases(frozen)}
    cases["archived_halfon"] = dict(cases["f3half"], id="archived_halfon",
                                   role="Existing fixed resistors, reread original raw")
    archived = OLD / "circuit.raw"
    check(sha256(archived) == read_json(TEST / "round_01_archive.json")["archived_raw_sha256"],
          "Historical native waveform hash mismatch")
    with (HERE / "FAULT_ENERGY_DISTRIBUTION.csv").open(newline="", encoding="utf-8") as stream:
        table = list(csv.DictReader(stream))
    windows = frozen["limits"]["endpoint_s"]
    wanted = {(case, window) for case in cases if case != "archived_halfon" for window in (1, windows)}
    wanted.add(("archived_halfon", 1))
    check(len(table) == len(metrics["results"]) == len(wanted) and
          {(row["case"], int(row["window_s"])) for row in table} == wanted
          and (HERE / "FAULT_ENERGY_DISTRIBUTION.csv").read_bytes() == (TEST / "energy_distribution.csv").read_bytes(),
          "Review CSV does not exactly reproduce raw integration output")
    for row in metrics["results"]:
        name = row["case"]
        raw_path, node = (archived, "faultbus") if name == "archived_halfon" else (raw, name)
        actual = integrate(raw_path, node, cases[name], row["window_s"], frozen["criteria"]["residual_comparison_V"])
        check(actual == row, f"Independent reintegration differs: {name}")
        for field in ("bus_balance_error_mJ", "input_balance_error_mJ"):
            check(abs(actual[field]) <= frozen["limits"]["balance_abs_mJ"], f"Energy balance failed: {name}")
    config, _ = load_catalog()
    check(config["manufacturing"] == "ENGINEERING HOLD", "Manufacturing disposition changed")
    reviewed = {"g0d_archive_qualification"}
    first = read_json(RUN / "round_01/decision.json")
    second = read_json(RUN / "round_02/decision.json")
    validate_decision(first, TASKS, reviewed, reviewed, 1, 4)
    validate_decision(second, TASKS, set(TASKS), set(TASKS), 0, 4)
    check(first["decision"] == "CONTINUE" and second["decision"] == "HOLD", "Unexpected decisions")
    for forbidden in ("four_channel_fixture", "thirty_channel_eda", "manufacture"):
        check(not eligible(forbidden, TASKS, set(TASKS), set()), f"Forbidden task became eligible: {forbidden}")
    print(f"PASSED G0D hashes, 2 decisions, 0 provider calls, {len(table)} energy windows, ENGINEERING HOLD")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        import json

        print(json.dumps(scheduler_preview(read_json(CONFIG)), indent=2))
    else:
        audit()
