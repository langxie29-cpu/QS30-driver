"""Presence/latitude probe for the ONE suspected artefact in the vendor reference.

The vendor LT3757A.asc carries no input source resistance and no LT3757A SHDN
(VIN/SHDN pin is wired to net IN/VIN by the netlister). The native .op therefore
lands at a degenerate point (~0 V everywhere) and the unmodified .tran run stays
below 0.1 mV. This probe is NOT the unmodified replay: it is a labelled sensitivity
test of the SAME vendor circuit, kept separate in probe_series/.
"""
from pathlib import Path
import os, json, subprocess, time, shutil

HERE = Path(__file__).resolve().parent
EXE = Path(r"D:\PROJECTS\dsharness\QS30-1\projects\QS30-9_24V\toolchain\ltspice26\extracted\LTspice.exe")
PROBE = HERE / "probe_series"
PROBE.mkdir(exist_ok=True)
prof = HERE / "sim_profile"
ltdir = prof / "LTspice"
env = dict(os.environ, APPDATA=str(prof), LOCALAPPDATA=str(prof))

base = (HERE / "LT3757A.original.net").read_bytes().decode("cp1252").splitlines()
idx = max(i for i, l in enumerate(base) if l.lower().startswith(".tran"))

series = {
    # label: (input element replacement, tran card)
    "P1_series100m": ("V1 IN SRC 12\nVSRC SRC 0 0", ".tran 1.5m startup"),
    "P2_series100m_2ms": ("V1 IN SRC 12\nVSRC SRC 0 0", ".tran 2m startup"),
}
rows = {}
for label, (vin, tran) in series.items():
    lines = [vin if l.startswith("V1 IN 0 12") else l for l in base]
    lines[idx] = tran
    lines[idx] = tran
    lines.insert(idx, ".options plotwinsize=0")
    p = PROBE / (label + ".cir")
    p.write_text("\n".join(lines) + "\n", encoding="cp1252", newline="\n")
    start = time.monotonic()
    pr = subprocess.run([str(EXE), "-b", "-ascii", str(p), "-I" + str(ltdir / "lib" / "sub")],
                        cwd=str(PROBE), env=env, capture_output=True, timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW)
    rows[label] = {"rc": pr.returncode, "elapsed_s": time.monotonic() - start,
                   "raw": str((PROBE / (label + ".raw")).relative_to(HERE)) if (PROBE / (label + ".raw")).is_file() else None,
                   "diff_vs_original": {"V1_line": vin, "tran": tran, "added": ".options plotwinsize=0"}}
    print(label, rows[label])
(PROBE / "probe_manifest.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf8", newline="\n")
