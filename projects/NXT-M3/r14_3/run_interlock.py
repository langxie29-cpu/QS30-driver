"""Exercise the R14.1 stop proxy with the R14.3 gate-inhibit circuit."""
from dataclasses import asdict, dataclass, replace
import argparse
import gzip
import json
from pathlib import Path
import subprocess

from run_scan import HERE, read_raw, write_csv

ACTIVE = """
Vbias2 gate_bias 0 11.6
Rpint gate_bias in_minus 200k
Rpext gate_bias in_minus {pullup}
Cinput in_minus 0 {capacitance}
Bpermit permit 0 V={permit}
Rlogic permit gmos 100
Rgate gmos 0 100k
Cgate gmos 0 40p
Spermit in_minus 0 {gate} 0 SWMOS
.model SWMOS SW(Ron=2 Roff=1T Vt=1.5 Vh=.03)
Vrequest pwm 0 PWL(0 0 .015 0 .015001 3.3)
Bstatus gate_out 0 V=(v(pwm)>2 && v(in_minus)<2.1 && v(gate_bias)>4.4 ? 3.3 : 0)
.tran {step} .20 0 {step}
.control
run
set filetype=binary
write waveform.raw v(vdd) v(contact) v(strobe) v(stop_gate) v(fault_n) v(latch_clr_n) v(mcu_en)
+ v(res_ok) v(armed) v(pwm_permit) v(hc_oe_n) v(feed) v(pwm) v(gmos) v(in_minus) v(gate_out)
quit
.endc
.end
"""

@dataclass(frozen=True)
class Interlock:
    name: str
    template: str = "open_reclose_held_arm"
    capacitance: float = 220e-12
    pullup: str = "10k"
    gate: str = "gmos"
    permit: str = "v(pwm_permit)"
    step: str = "20u"


def compile_deck(case):
    source = HERE.parent / "r14/evidence/r14_1/proxy" / case.template / "circuit.cir"
    base = source.read_text(encoding="ascii")
    base = base[:base.index(".tran")].split("\n", 1)[1]
    values = asdict(case)
    if case.name == "stuck_residual_block":
        base = base.replace("VRES res_ok 0 PWL(0 3.3)",
                            "VRES res_ok 0 PWL(0 3.3 .0401 3.3 .04011 0 .14 0 .14001 3.3)")
    if case.name == "control_power_interrupted":
        values["permit"] = "(v(vdd) > 2.6 ? v(pwm_permit) : 0)"
        base = base.replace("VDD vdd 0 3.3", "VDD vdd 0 PWL(0 3.3 .039999 3.3 .04 0)")
        base = base.replace("v(fault_n)>2 && v(mcu_en)>2", "v(vdd)>2.6 && v(fault_n)>2 && v(mcu_en)>2")
    return f"R14.3 low-voltage stop proxy / {case.name}\n" + base + ACTIVE.format(**values)


def metrics(case, path):
    vectors, rows = read_raw(path)
    v = dict(zip(vectors, zip(*rows)))
    t = v["time"]
    if t[-1] < .1999:
        raise ValueError(f"{case.name} aborted at {t[-1]}")
    event = .0399995

    def at(net, target):
        index = min(range(len(t)), key=lambda i: abs(t[i]-target))
        return v[f"v({net})"][index]

    def crossing(net, threshold, up):
        trace = v[f"v({net})"]
        for i, tt in enumerate(t[1:], 1):
            if tt < event - 2e-6:
                continue
            a, b = trace[i-1], trace[i]
            if (up and a < threshold <= b) or (not up and b <= threshold < a):
                return (t[i-1] + (tt-t[i-1])*(threshold-a)/(b-a) - event)*1e6
        return None

    result = dict(case=case.name, points=len(t), t_stop_fault_us=crossing("fault_n", 1.65, False),
                  t_stop_armed_us=crossing("armed", 1.65, False),
                  t_stop_oe_us=crossing("hc_oe_n", 1.65, True),
                  t_stop_gate_us=crossing("gate_out", 1.65, False),
                  armed_after_open=at("armed", .05), oe_after_open=at("hc_oe_n", .05),
                  control_rail_after_open=at("vdd", .05),
                  gate_after_open=at("gate_out", .05), feed_after_open_V=at("feed", .06),
                  armed_reclosed_held=at("armed", .08), armed_arm110=at("armed", .115),
                  armed_arm160=at("armed", .167))
    if case.template != "nc_bridge":
        assert result["armed_after_open"] < .1
        if case.name == "control_power_interrupted":
            assert result["control_rail_after_open"] < .1 and result["oe_after_open"] < .1
        else:
            assert result["oe_after_open"] > 3
        assert result["armed_reclosed_held"] < .1
        assert (result["gate_after_open"] > 3) == (case.gate == "gate_bias")
        if case.template == "u11_stuck":
            assert result["feed_after_open_V"] > 4.9
        else:
            assert result["feed_after_open_V"] < 2
    else:
        assert result["gate_after_open"] > 3 and result["armed_after_open"] > 3
    if case.name == "stuck_residual_block":
        assert result["armed_arm110"] < .1 and result["armed_arm160"] > 3
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--out", type=Path, default=HERE / "evidence")
    args = parser.parse_args()
    nominal = Interlock("healthy_u11_mcu_frozen_high")
    cases = (
        nominal,
        replace(nominal, name="nominal_timestep_refined", step="5u"),
        replace(nominal, name="stuck_u11", template="u11_stuck"),
        replace(nominal, name="watchdog_fault_asserted", template="other_fault"),
        replace(nominal, name="stuck_residual_block", template="u11_stuck"),
        replace(nominal, name="stuck_u11_and_mos_short", template="u11_stuck", gate="gate_bias"),
        replace(nominal, name="contact_bridged", template="nc_bridge"),
        replace(nominal, name="control_power_interrupted"),
        replace(nominal, name="fast_c20p", capacitance=20e-12),
        replace(nominal, name="slow_c1n", capacitance=1e-9),
        replace(nominal, name="pullup_open_c1n", capacitance=1e-9, pullup="1T"),
    )
    rows = []
    for case in cases:
        folder = args.out / "interlock" / case.name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "case.json").write_text(json.dumps(asdict(case), indent=2)+"\n")
        (folder / "circuit.cir").write_text(compile_deck(case), encoding="ascii", newline="\n")
        raw = folder / "waveform.raw"
        raw.unlink(missing_ok=True)
        with (folder / "run.log").open("wb") as log:
            subprocess.run([args.ngspice, "-n", "-b", "circuit.cir"], cwd=folder, stdout=log,
                           stderr=subprocess.STDOUT, timeout=30, check=True)
        rows.append(metrics(case, raw))
        (folder / "waveform.raw.gz").write_bytes(gzip.compress(raw.read_bytes(), mtime=0))
        raw.unlink()
    write_csv(args.out / "interlock_metrics.csv", rows)
    print(f"{len(rows)} low-voltage stop cases completed")
if __name__ == "__main__":
    main()
