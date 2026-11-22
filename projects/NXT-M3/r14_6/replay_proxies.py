"""Replay archived proxies without changing their topology or interpreting them as hardware."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RUNNER = PROJECT / "r11/sim/dll_run.py"
CASES = {
    "off_170": "r14_3/evidence/spice/off_170_25_none/circuit.cir",
    "off_195": "r14_3/evidence/spice/off_195_25_none/circuit.cir",
    "partial_195": "r14/evidence/simulation/half_195_sustain/circuit.cir",
    "stop_nominal": "r14/evidence/simulation/stop_nominal/circuit.cir",
    "stop_one_bleeder": "r14/evidence/simulation/stop_one_bleeder/circuit.cir",
    "stop_u11_stuck": "r14/evidence/simulation/stop_u11_stuck/circuit.cir",
    "watchdog_proxy": "r14_3/evidence/interlock/watchdog_fault_asserted/circuit.cir",
    "ovp_proxy": "r11/evidence/r2/ovp_feedback_fault_noload/circuit.cir",
}


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def replay(scratch, evidence, case):
    label, source = case
    folder = scratch / label
    folder.mkdir()
    circuit = folder / "circuit.cir"
    original = PROJECT / source
    content = original.read_bytes()
    # Older standalone fixtures own simulator control and terminate the DLL.
    # The existing DLL runner supplies these same console actions for this copy.
    if re.search(rb"(?im)^\s*quit\s*$", content):
        content, n = re.subn(rb"(?ms)^\.control[^\r\n]*\r?\n.*?^\.endc[^\r\n]*\r?\n", b"", content)
        if n != 1:
            raise ValueError(source)
    circuit.write_bytes(content)
    args = [sys.executable, str(RUNNER), str(circuit)]
    run = subprocess.run(args, capture_output=True, cwd=folder, timeout=120)
    (evidence / f"{label}.log").write_bytes(run.stdout + run.stderr)
    raw = folder / "waveform.raw"
    record = dict(case=label, source=source, source_sha256=digest(original), replay_input_sha256=digest(circuit), exit=run.returncode,
                  command=["KiCad 10.0.8 python.exe", "r11/sim/dll_run.py", f"{label}/circuit.cir"],
                  waveform_bytes=raw.stat().st_size if raw.exists() else 0,
                  waveform_sha256=digest(raw) if raw.exists() else "",
                  solver="ngspice-46 DLL", applied_to_final_hardware=False)
    if raw.exists():
        with raw.open("rb") as file:
            head = file.read(4096).split(b"Binary:", 1)[0].decode("utf-8", "replace")
        record["raw_point_rows"] = [line.strip() for line in head.splitlines()
                                    if line.startswith(("No. Points:", "No. Variables:"))]
    return record


if __name__ == "__main__":
    evidence = HERE / "evidence/simulation"
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nxt-r146-sim-") as name, ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda case: replay(Path(name), evidence, case), CASES.items()))
    (evidence / "commands-and-hashes.json").write_text(json.dumps(records, indent=2)+"\n", encoding="utf-8")
    print([(r["case"], r["exit"]) for r in records])
