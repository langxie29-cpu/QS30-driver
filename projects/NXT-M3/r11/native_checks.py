"""Run native KiCad checks and record literal commands and return codes."""
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CLI = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin")) / "kicad-cli.exe"
PROJECT = "eda/NXT-M3-R11"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
runs = []

checks = [
    ["version"],
    ["sch", "erc", "--exit-code-violations", "-o", str(out / "ERC_REPORT.txt"), PROJECT + ".kicad_sch"],
    ["sch", "export", "netlist", "--format", "kicadxml", "-o", str(out / "native_netlist.xml"), PROJECT + ".kicad_sch"],
    ["pcb", "drc", "--schematic-parity", "--exit-code-violations", "-o", str(out / "DRC_REPORT.txt"), PROJECT + ".kicad_pcb"],
    ["pcb", "drc", "--schematic-parity", "--format", "json", "--exit-code-violations",
     "-o", str(out / "DRC.json"), PROJECT + ".kicad_pcb"],
]
for args in checks:
    command = [str(CLI), *args]
    proc = subprocess.run(command, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    runs.append({"command": command, "exit": proc.returncode, "output": proc.stdout.decode("utf-8", "replace")})
(out / "commands.json").write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")
data = json.loads((out / "DRC.json").read_text(encoding="utf-8-sig"))
summary = {"violations": dict(Counter(x["type"] for x in data["violations"])),
           "severity": dict(Counter(x["severity"] for x in data["violations"])),
           "unconnected_items": len(data["unconnected_items"]),
           "schematic_parity": dict(Counter(x["type"] for x in data["schematic_parity"]))}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(summary, [item["exit"] for item in runs])
