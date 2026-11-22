"""Replay R14.6 copper changes on the released R14.5 project."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "r14_5"
sys.path.insert(0, str(BASE))
from route_board import BoardRouter, gap, pcb, uid, xy
from verify_board import PROTECTION, STOP


SOURCE_STEM = "NXT-M3-R14.5"
STEM = "NXT-M3-R14.6"
CLI = Path(sys.executable).with_name("kicad-cli.exe")


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_schematic_metadata(eda):
    for sheet in sorted(eda.glob("*.kicad_sch")):
        content = sheet.read_text(encoding="utf-8")
        content = content.replace(f'(project "{SOURCE_STEM}"', f'(project "{STEM}"')
        if sheet.stem == STEM:
            content = content.replace("NXT-M3-R14 / Overview", f"{STEM} / Overview")
            content = content.replace("R14 engineering HOLD", "R14.6 engineering HOLD")
            content = content.replace("STATIC DIGITS / R14\"", "STATIC DIGITS / R14.6\"")
            content = content.replace("R14     GATE_0", "R14.6     GATE_0")
        sheet.write_text(content, encoding="utf-8")


def stage(root):
    eda = root / "eda"
    if eda.exists():
        raise FileExistsError(eda)
    shutil.copytree(BASE / "eda", eda, ignore=shutil.ignore_patterns(
        "*.kicad_prl", "*.lck", "*-backups", "fp-info-cache"))
    for suffix in ("pro", "dru", "sch", "pcb"):
        (eda / f"{SOURCE_STEM}.kicad_{suffix}").rename(eda / f"{STEM}.kicad_{suffix}")
    update_schematic_metadata(eda)
    return eda / f"{STEM}.kicad_pcb"


def native(board, report, *, fill=False):
    args = ["pcb", "drc", "--severity-all", "--all-track-errors",
            "--schematic-parity", "--exit-code-violations", "--format", "json"]
    if fill:
        args.extend(("--refill-zones", "--save-board"))
    args.extend(("-o", str(report), str(board)))
    run = subprocess.run([CLI, *args], cwd=board.parent, capture_output=True,
                         encoding="utf-8", errors="replace")
    print(report.name, "exit", run.returncode, run.stdout, run.stderr, flush=True)
    if run.returncode not in (0, 5) or not report.is_file():
        raise RuntimeError((args, run.returncode, run.stderr))
    result = json.loads(report.read_text(encoding="utf-8"))
    write_json(report.with_suffix(".command.json"), {
        "executable": CLI.name, "args": [*args[:-2], report.name, board.name],
        "exit": run.returncode, "stdout": run.stdout, "stderr": run.stderr})
    return result


def compare(board, report, previous):
    current = native(board, report, fill=True)

    def keys(entries):
        return {(v["type"], tuple(sorted(i["uuid"] for i in v["items"]))) for v in entries}

    new = keys(current["violations"]) - keys(previous["violations"])
    opens = len(current["unconnected_items"])
    if new or current["schematic_parity"] or opens > len(previous["unconnected_items"]):
        raise RuntimeError({"new_drc": sorted(new), "opens": opens,
                            "parity": current["schematic_parity"], "report": str(report)})
    return current


def close_native(board, entries):
    router = BoardRouter(board)
    key_register = {"SER2", "SER3", "SR_CLK_BUS", "SR_LATCH_BUS", "HC_CLEAR_N", "HC_OE_N"}
    goals = {}
    for check, left, right in (*PROTECTION, *STOP):
        a, b = router.pads(left), router.pads(right)
        if not router.connected(a, b):
            goals[f"{check} {left} -> {right}"] = (a, b)

    opens = []
    for entry in entries:
        a, b = (router.by_id.get(value["uuid"]) for value in entry["items"])
        if a is None or b is None:
            continue
        net = a.GetNetname()
        xy_a, xy_b = xy(a.GetPosition()), xy(b.GetPosition())
        dist = abs(xy_a[0] - xy_b[0]) + abs(xy_a[1] - xy_b[1])
        opens.append((net not in key_register, gap(net) > 1, dist, uid(a), uid(b)))
    for label, (a, b) in list(goals.items()):
        if a[0].GetNetname() not in key_register:
            continue
        router.route(label, a, b, margin=15, limit=250000, via_size=.50)
    for _, _, _, a, b in sorted(opens):
        router.route(f"native {a} -> {b}", [router.by_id[a]], [router.by_id[b]],
                     margin=12, limit=600000 if router.by_id[a].GetNetname() in {"BIAS_S", "UART_TX"} else 170000,
                     via_size=.50)
    for label, (a, b) in goals.items():
        router.route(label, a, b, margin=14, limit=200000, via_size=.50)
    router.save(board)
    return router.events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root = args.out.resolve()
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    board = stage(root)
    from local_changes import feedback, ovp_capacitor, register_fanout, snubber, ti_dgk_lands

    previous = native(board, evidence / "00-baseline.json")
    feedback_positions = ((150, 94, 0, False), (159, 94, 0, False), (168, 94, 0, False))
    ok, feedback_routes = feedback(board, feedback_positions)
    if not ok:
        raise RuntimeError("Restoration of feedback copper failed")
    write_json(evidence / "01-feedback-routes.json", feedback_routes)
    previous = compare(board, evidence / "01-feedback.json", previous)

    cap_position, cap_routes = snubber(board, [(172.5, 101, 270, True)])
    if cap_position is None:
        raise RuntimeError("C48 replacement or routing failed")
    write_json(evidence / "02-snubber-routes.json", {"placement": cap_position, "routes": cap_routes})
    previous = compare(board, evidence / "02-snubber.json", previous)

    write_json(evidence / "03-register-routes.json", register_fanout(board))
    previous = compare(board, evidence / "03-register.json", previous)

    ti_dgk_lands(board)
    previous = compare(board, evidence / "04-dgk.json", previous)

    write_json(evidence / "05-remaining-routes.json", close_native(board, previous["unconnected_items"]))
    previous = compare(board, evidence / "05-main-routing.json", previous)
    write_json(evidence / "06-ovp-routes.json", ovp_capacitor(board))
    compare(board, evidence / "06-final.json", previous)


if __name__ == "__main__":
    main()
