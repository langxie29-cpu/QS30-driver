"""Cross-check Gate 0 stored-energy bounds using a passive electrical analog."""
import argparse
import importlib.util
import math
import os
from pathlib import Path
import re
import subprocess

from orchestrate import HERE, sha256, write_json


def run(exe, folder):
    folder.mkdir(parents=True, exist_ok=False)
    anode = 19800.0
    capacitor = 5.5e-6
    volts = 195.0
    bleeder = 502980.0
    r_tube_path = anode*2
    equiv = 1/(1/r_tube_path+2/bleeder)
    tau = capacitor*equiv
    power = volts**2/(4*anode)
    measured_to = 1.0
    expected = {
        "preinitial": power*math.exp(-2*.001/tau),
        "fault_60": tau*math.log(volts/60),
        "reservoir_60": capacitor*bleeder/2*math.log(volts/60),
        "fault_energy": power*tau*(1-math.exp(-2*measured_to/tau))/2,
    }
    deck = folder/"circuit.cir"
    deck.write_text(f"""* R8 G0 passive energy diagnostic; resistor analog for one instantaneous partial-on point
* Post-cutoff only. 195 V is assumed residual, not a supply or cold-start test.
Cout faultbus 0 {capacitor} IC={volts}
Rb1 faultbus 0 {bleeder}
Rb2 faultbus 0 {bleeder}
Ranode faultbus q {anode}
Ranalog q 0 {anode}
Cisolated reservoir 0 {capacitor} IC={volts}
Ri1 reservoir 0 {bleeder}
Ri2 reservoir 0 {bleeder}
.tran 0 4 0 100u uic
.opt plotwinsize=0
.meas tran v_at_1ms FIND V(q) AT 1m
.meas tran fault_60 WHEN V(faultbus)=60 FALL=1
.meas tran reservoir_60 WHEN V(reservoir)=60 FALL=1
.meas tran fault_energy INTEG V(q)*V(q)/{anode} FROM 0 TO 1
.end
""",encoding="ascii",newline="\n")
    command = [str(exe), "-b", str(deck)]
    prereg = dict(scope="Constant-resistance passive analog only; no transistor, cutoff timing or SOA modeled.",
                  capacitance_F=capacitor, initial_V=volts, independent_bleed_branch_ohm=bleeder,
                  anode_limiter_and_analog_ohm=anode, requested_end_s=4, maxstep_s=.0001,
                  limit_relative_error=.003, expected=expected, engine_sha256=sha256(exe),
                  circuit_sha256=sha256(deck), command=command,
                  manufacturing="ENGINEERING HOLD")
    write_json(folder/"preregister.json",prereg)
    try:
        result = subprocess.run(command, cwd=folder, timeout=25, capture_output=True,
                                env={**os.environ, "LOCALAPPDATA": str(folder/"cache"),
                                     "APPDATA": str(folder/"settings")},
                                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as failure:
        code, stdout, stderr = None, failure.stdout or b"", failure.stderr or b""
    (folder/"stdout.txt").write_bytes(stdout)
    (folder/"stderr.txt").write_bytes(stderr)
    actual = {}
    span = {}
    raw = folder/"circuit.raw"
    log = folder/"circuit.log"
    if code == 0 and raw.is_file() and 0 < raw.stat().st_size <= 536870912 and log.is_file():
        content = log.read_bytes()
        encoding = "utf-16le" if content[1:2]==b"\0" else "utf-8"
        text = content.decode(encoding,"replace").lstrip("\ufeff")
        (folder/"run.log").write_text(text.replace("\r\n","\n").replace("\r","\n"),encoding="utf-8",newline="\n")
        number = r"([-+0-9.eE]+)"
        for name in ("fault_60","reservoir_60"):
            m = re.search(rf"^{name}:.*?\bAT\s+{number}",text,re.I|re.M)
            if m:
                actual[name]=float(m[1])
        for name in ("v_at_1ms","fault_energy"):
            m = re.search(rf"^{name}:.*?=\s*{number}",text,re.I|re.M)
            if m:
                actual[name]=float(m[1])
        if "v_at_1ms" in actual:
            actual["preinitial"]=actual.pop("v_at_1ms")**2/anode
        module = HERE.parent/"r7/UNIFIED_POWER_MODEL/raw_metrics.py"
        spec = importlib.util.spec_from_file_location("r7_raw",module)
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        span = reader.span(raw)
    assertions={k:k in actual and abs(actual[k]/v-1)<=.003 for k,v in expected.items()}
    assertions["raw_endpoint"]=span.get("last_s",0)>=4-1e-9
    total_allowance=(150-85)/417
    required_anode=volts**2/(4*total_allowance)
    write_json(folder/"metrics.json",dict(
        solver="LTspice 24.0.12 (local executable)",exit_code=code,
        raw_span=span,raw_sha256=sha256(raw) if raw.is_file() else None,
        maxstep_s=.0001,computed_peak_W=power,energy_initial_reservoir_J=.5*capacitor*volts**2,
        fixed_analog_expected=expected,solver_measured=actual,assertions=assertions,
        status="LIMITED_PASS" if all(assertions.values()) and code==0 else "INCONCLUSIVE",
        resistance_only_screen=dict(thermal_budget_85C_W=total_allowance,
            minimum_anode_ohm_for_thermal_screen=required_anode,
            nominal_current_at_170V_125Vsustain_mA=45000/required_anode,
            nominal_current_at_170V_110Vsustain_mA=60000/required_anode,
            scope="Ignores additional secondary breakdown and thermal coupling; not an SOA guarantee."),
        caveat="Physical deenergization, detection time, BJT behavior and allowable pulse/JT remain unknown."))
    return 0 if all(assertions.values()) and code==0 else 2


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--solver",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    raise SystemExit(run(args.solver.resolve(),args.output.resolve()))
