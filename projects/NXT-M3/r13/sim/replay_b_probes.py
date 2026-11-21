"""Isolate behavioral voltage probes in the registered LM3488 fixture."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "evidence/spice/round2/b_pin_step_vref126"
PYTHON = Path("C:/Program Files/KiCad/10.0/bin/python.exe")
HOST = ROOT.parent / "r11/sim/dll_run.py"
DECK = (BASE/"circuit.cir").read_text()

for name, drops in (
    ("no_loss_probe", ("B_SW",)),
    ("native_node_probes", ("B_SW","B_VDS","B_VGS","B_PWR","B_HV")),
):
    dst = ROOT/".local"/"b_probes_replay"/name
    dst.mkdir(parents=True)
    for p in BASE.iterdir():
        if p.suffix.lower() in {".lib",".spi"}:
            shutil.copyfile(p,dst/p.name)
    d = re.sub(r"(?m)^(?:"+"|".join(drops)+r") .*\n","",DECK)
    if name == "native_node_probes":
        d = d.replace("v(vds) v(vgs)","v(sw) v(source) v(gate)").replace(
                      " v(p_in) v(p_hv) v(p_sw)","")
    else:
        d = d.replace(" v(p_sw)","")
    target = dst/"circuit.cir"
    target.write_text(d,encoding="ascii")
    command = [str(PYTHON),"-u",str(HOST),str(target)]
    with (dst/"run.log").open("wb") as log:
        try:
            status = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=65).returncode
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
    raw = dst/"waveform.raw"
    digest = None
    if raw.is_file():
        with raw.open("rb") as f:
            digest = hashlib.file_digest(f,"sha256").hexdigest()
    report = {"case":name,"isolation":"No power-stage or TI library changes.",
              "command":command,"exit_code":status,"waveform_sha256":digest,
              "source_deck_sha256":hashlib.sha256((BASE/"circuit.cir").read_bytes()).hexdigest()}
    (dst/"measurement.json").write_text(json.dumps(report,indent=2)+"\n")
    print(name,status,flush=True)
