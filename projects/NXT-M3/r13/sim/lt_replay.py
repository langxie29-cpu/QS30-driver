"""Run unchanged R13 fixtures in the locally available signed ADI simulator."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
EXE = Path("D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspice.exe")
OUTPUT = ROOT / ".local/lt_replay"
SELECTION = {
    "a_low_50k":("round1",170,.065), "a_pin_4v30":("round1",170,.065),
    "b_ref_approx":("round1",180,.01), "b_low_trap_vref126":("round2",170,.012),
    "b_pin_step_vref126":("round2",170,.012),
    "b_low":("round1",170,.065),
}


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file,"sha256").hexdigest()


def run(item):
    case,(batch,nominal,end) = item
    source = ROOT/"evidence/spice"/batch/case
    target = OUTPUT/case
    target.mkdir()
    for infile in source.iterdir():
        if infile.suffix.lower() in {".lib",".spi"}:
            shutil.copyfile(infile,target/infile.name)
    deck = (source/"circuit.cir").read_text()
    t1 = end - min(.003,.2*end)
    measurements = f"""
.options plotwinsize=0 numdgt=15
.meas tran hv_min MIN v(hv) FROM={t1} TO={end}
.meas tran hv_max MAX v(hv) FROM={t1} TO={end}
.meas tran hv_avg AVG v(hv) FROM={t1} TO={end}
.meas tran hv_peak MAX v(hv)
.meas tran startup_hv FIND v(hvc) AT=1n
.meas tran vin_avg AVG v(vin) FROM={t1} TO={end}
.meas tran vds_peak MAX v(vds)
.meas tran vgs_peak MAX v(vgs)
.meas tran i_power_peak MAX i(LPOWER)
.meas tran i_switch_peak MAX i(VQ)
.meas tran first_95 WHEN v(hv)={nominal*.95} RISE=1
.end
"""
    target_file = target/"circuit.cir"
    target_file.write_text(deck.rsplit(".end",1)[0]+measurements,encoding="ascii")
    command = [str(EXE),"-b",str(target_file)]
    env = os.environ.copy()
    for key in ("APPDATA","LOCALAPPDATA"):
        path = target/key.lower()
        path.mkdir()
        env[key] = str(path)
    try:
        done = subprocess.run(command,cwd=target,env=env,capture_output=True,timeout=90,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        code = done.returncode
        (target/"stdout.txt").write_bytes(done.stdout)
        (target/"stderr.txt").write_bytes(done.stderr)
    except subprocess.TimeoutExpired:
        code = None
    log = target/"circuit.log"
    raw = target/"circuit.raw"
    text = ""
    if log.is_file():
        body = log.read_bytes()
        text = body.decode("utf-16" if body.startswith(b"\xff\xfe") else
                           "utf-16le" if body[1:2] == b"\0" else "utf-8", "replace")
    m = {key:float(val) for key,val in re.findall(r"(?mi)^([a-z0-9_]+)\s*:[^=\n]*=([-+e0-9.]+)",text)}
    if "hv_min" in m and "hv_max" in m:
        m["hv_ripple_vpp"] = m["hv_max"]-m["hv_min"]
    report = {"case":case,"nominal_v":nominal,"endpoint_required_s":end,"command":command,
              "exe_sha256":sha(EXE),"exit_code":code,"raw_size":raw.stat().st_size if raw.is_file() else 0,
              "raw_sha256":sha(raw) if raw.is_file() else None,
              "measurements":m,
              "log_errors":[x for x in text.splitlines() if re.search("fatal|timestep too small|error|failed",x,re.I)]}
    (target/"measurement.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(case,code,m,report["log_errors"][:2],flush=True)


if __name__ == "__main__":
    OUTPUT.mkdir()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(run,SELECTION.items()))
