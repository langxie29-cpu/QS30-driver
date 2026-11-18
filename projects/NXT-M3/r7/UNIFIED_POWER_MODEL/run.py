"""R7 native batch runner. Records termination and never equates a proxy with qualification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / "r6" / "LTSPICE_MODEL" / "runs" / "p1c_full"
BASELINE = json.loads((BASE / "preregister.json").read_text())
WORKSPACES = HERE.parents[4]
EXE = Path(os.getenv("NXT_LTSPICE", str(WORKSPACES / "QS30-1/projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspice.exe")))
MODELS = Path(os.getenv("NXT_R4_MODELS", str(WORKSPACES / "QS30-power-loop-r4/projects/QS30-9_24V/power_loop_r4/experiments/sic_1ns_20261118T034706_c01f9cf2")))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def log_text(path):
    if not path.exists():
        return ""
    data = path.read_bytes()
    return data.decode("utf-16le" if data[1:2] == b"\x00" else "utf-8", "replace").lstrip("\ufeff")


def json_file(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True)
    if not args.no_vendor:
        (out / "models").mkdir()
        for model in BASELINE["models"]:
            source = MODELS / model["file"]
            if sha(source) != model["sha256"]:
                raise ValueError(f"Vendor model differs from R6: {source.name}")
            shutil.copyfile(source, out / "models" / source.name)
    deck = out / "circuit.cir"
    shutil.copyfile(args.deck, deck)
    for lib in args.lib:
        shutil.copyfile(lib, out / lib.name)
    command = [str(EXE), *(["-alt"] if args.alternate else []), "-b", str(deck)]
    receipt = dict(deck=args.deck.name, deck_sha256=sha(deck), engine_sha256=sha(EXE),
                   model_sha256={} if args.no_vendor else {m["file"]:m["sha256"] for m in BASELINE["models"]},
                   additional_libraries={p.name:sha(p) for p in args.lib},
                   engine_switches=command[1:-1], timeout_s=args.timeout, hypothesis=args.purpose)
    json_file(out / "preregister.json", receipt)
    env = {**os.environ, "LOCALAPPDATA": str(out / "cache"), "APPDATA": str(out / "config")}
    for name in ("cache", "config"):
        (out / name).mkdir()
    start = time.monotonic()
    code = None
    try:
        code = subprocess.run(command, cwd=out, env=env, timeout=args.timeout,
                              creationflags=subprocess.CREATE_NO_WINDOW).returncode
        execution = "EXITED"
    except subprocess.TimeoutExpired:
        execution = "TIMEOUT"
    log = log_text(deck.with_suffix(".log"))
    raw = deck.with_suffix(".raw")
    measures = {key: float(value) for key, value in re.findall(
        r"^([a-z0-9_]+):[^=\r\n]*=\s*(-?[0-9]+(?:\.[0-9]*)?(?:e[+-]?\d+)?)",
        log, re.M | re.I) if not key.lower().startswith(("cmp", "driver", "ucmp", "udriver")) and key.lower() not in {"start_160", "fault_time", "icut", "ov_cross", "cut_cmd", "dual_60", "single_60", "aux_uv"}}
    for key in ("start_160", "fault_time", "icut", "ov_cross", "cut_cmd", "dual_60", "single_60", "aux_uv"):
        match = re.search(rf"^{key}:.*?\bAT\s+([0-9.eE+-]+)", log, re.M | re.I)
        if match:
            measures[key] = float(match[1])
    result = dict(execution=execution, exit_code=code, seconds=round(time.monotonic()-start, 3),
                  measures=measures, raw_bytes=raw.stat().st_size if raw.exists() else 0,
                  raw_sha256=sha(raw) if raw.exists() else None)
    if raw.exists():
        from raw_metrics import span
        result["raw_span"] = span(raw)
    json_file(out / "result.json", result)
    (out / "run.log.txt").write_text(log, encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timeout", type=int, default=210)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--alternate", action="store_true")
    parser.add_argument("--no-vendor", action="store_true")
    parser.add_argument("--lib", action="append", type=Path, default=[])
    run(parser.parse_args())
