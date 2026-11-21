"""Execute and record independent R11 SPICE cases with timeout and measurements."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import zipfile
import io

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent / "evidence/r2"
KICAD = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin"))
VENDOR_URL = "https://www.ti.com/lit/mo/snvmbl2h/snvmbl2h.zip"
VENDOR_SHA = "b1fee2be86929ab8f0b8a6f856aad7f27c166398efabe2c899fb718caba40bf8"
MEMBER = "LM5155-Q1_PSPICE_TRANS/LM5155-Q1_TRANS.LIB"


def vendor_bytes(vendor_zip):
    package = Path(vendor_zip).read_bytes() if vendor_zip else urllib.request.urlopen(VENDOR_URL, timeout=25).read()
    if hashlib.sha256(package).hexdigest() != VENDOR_SHA:
        raise ValueError("TI model archive differs from the reviewed SHA-256")
    return zipfile.ZipFile(io.BytesIO(package)).read(MEMBER)


def template(mode):
    circuit = (HERE / "boost.cir").read_text()
    if mode == "proxy":
        circuit = re.sub(r"(?m)^\.include LM5155-Q1_TRANS.LIB\n", "", circuit)
        circuit = re.sub(r"(?m)^X17 .*", (HERE / "controller_proxy.inc").read_text().strip(), circuit)
    elif mode == "vendor_op":
        circuit = circuit.replace("150n uic", "150n")
    return circuit


def raw_points(raw):
    if not raw.is_file():
        return 0
    with raw.open("rb") as stream:
        header = stream.read(4096).split(b"Binary:")[0]
    match = re.search(rb"No\. Points:\s*(\d+)", header)
    return int(match[1]) if match else 0


def run(name, circuit, model, lib=None):
    dest = CASE_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    raw = dest / "waveform.raw"
    raw.unlink(missing_ok=True)
    (dest / "circuit.cir").write_text(circuit, encoding="ascii")
    if lib:
        (dest / "LM5155-Q1_TRANS.LIB").write_bytes(lib)
    command = [str(KICAD / "python.exe"), "-u", "sim/dll_run.py",
               str(dest.relative_to(HERE.parent) / "circuit.cir")]
    start = time.monotonic()
    with (dest / "run.log").open("wb") as log:
        try:
            process = subprocess.run(command, cwd=HERE.parent, stdout=log, stderr=subprocess.STDOUT, timeout=55 if name.startswith("vendor") else 110)
            code = process.returncode
        except subprocess.TimeoutExpired:
            code = "TIMEOUT"
    body = (dest / "run.log").read_text(encoding="utf-8", errors="replace")
    values = {key: float(val) for key, val in re.findall(
        r"(?m)^stdout ([a-z][a-z_0-9]+)\s*=\s*([-+0-9.eE]+)", body)}
    record = {"case": name, "model": model, "command": command, "exit": code,
              "seconds": round(time.monotonic() - start, 3), "measurements": values, "raw_points": raw_points(raw),
              "waveform_sha256": hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None,
              "vendor_model_sha256": hashlib.sha256(lib).hexdigest() if lib else None}
    (dest / "measurement.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(name, code, record["raw_points"], values.get("hv_final"), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("group", choices=("vendor", "proxy", "fault", "layout", "protection"))
    parser.add_argument("--vendor-zip")
    parser.add_argument("--case")
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()
    base = template("proxy")
    cases = []
    if args.group == "vendor":
        lib = vendor_bytes(args.vendor_zip)
        patched = re.sub(rb"(?im)^\.IC\s+V\(COMP\s*\)\s*=.*$",
                         b"* COMP starts from zero in this fixture; skip incompatible nested directive.", lib)
        cases = [("vendor_pristine", template("vendor"), "TI PSpice archive with proxies", lib),
                 ("vendor_nominal", template("vendor"), "TI model excluding incompatible COMP .IC, UIC", patched),
                 ("vendor_op", template("vendor_op"), "TI model excluding incompatible COMP .IC, zero DC bias", patched)]
    if args.group == "proxy":
        for label, vin, load in (("nominal", 5, 7.65), ("maxload", 5, 9.9), ("lowline", 4.4, 9.9),
                                 ("highline", 5.5, 7.65), ("noload", 5, 0), ("light", 5, 2.55)):
            circuit = base.replace("100u 5 35m 5", f"100u {vin} 35m {vin}")
            circuit = circuit.replace("VLOAD REQUEST 0 7.65m", f"VLOAD REQUEST 0 {load}m")
            cases.append((label, circuit, "current-mode/controller and peripheral proxies"))
        for label, old, new in (
            ("load_step", "VLOAD REQUEST 0 7.65m", "VLOAD REQUEST 0 PWL(0 7.65m 21m 7.65m 21.01m 9.9m)"),
            ("line_step", "100u 5 35m 5", "100u 5 21m 5 21.01m 4.4 27m 4.4 27.01m 5.5 35m 5.5"),
            ("restart", "310u 3.3 35m 3.3", "310u 3.3 15m 3.3 15.01m 0 20m 0 20.01m 3.3 35m 3.3"),
            ("dnp_open", "RLINK=1m", "RLINK=1T"),
        ):
            cases.append((label, base.replace(old, new), "current-mode/controller and peripheral proxies"))
    if args.group == "fault":
        cases = [(path.stem, path.read_text(), "bounded proxy; see deck header")
                 for path in sorted((HERE / "faults").glob("*.cir"))]
    if args.group == "layout":
        for label, parasitic in (("layout_10nh", "10n"), ("layout_50nh", "50n")):
            cases.append((label, base.replace("VQ SW DRAIN 0", f"LPAR SW SW_LOCAL {parasitic}\nVQ SW_LOCAL DRAIN 0")
                          .replace("v(SW,SNS)", "v(DRAIN,SNS)"),
                          "assumed switch branch inductance, not field extraction"))
    if args.group == "protection":
        test = base.replace("V_ARM ARMED", "V_ARM ARM_REQUEST")
        test = test.replace(".save v(HV)", ".save v(TRIP) v(ARMED) v(CS_FILT) v(HV)")
        logic = (HERE / "protection_proxy.inc").read_text().strip()
        for name, fault in (
            ("ovp_feedback_fault_noload", "V_FAIL FAIL 0 PULSE(0 1 18m 10n 10n 30m 60m)\nS_FB FB 0 FAIL 0 HARD_FAULT"),
            ("ocp_sense_fault", "V_FAIL FAIL 0 PULSE(0 1 18m 10n 10n 30m 60m)\nV_OVER OVER 0 .15\nS_OC OVER CS_FILT FAIL 0 HARD_FAULT"),
        ):
            additions = logic + "\n" + fault + "\n.model HARD_FAULT SW(Ron=1 Roff=1T Vt=.5 Vh=.02)"
            deck = test.replace("VLOAD REQUEST 0 7.65m", "VLOAD REQUEST 0 0") if name.endswith("noload") else test
            cases.append((name, deck.replace(".end", additions + "\n.end"),
                          "dynamically coupled comparator, latch and U11 boundary proxies"))
    if args.case:
        cases = [case for case in cases if case[0] == args.case]
        if not cases:
            raise ValueError(args.case)
    cases = [(case[0] + args.suffix, *case[1:]) for case in cases]
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda case: run(*case), cases))


if __name__ == "__main__":
    main()





