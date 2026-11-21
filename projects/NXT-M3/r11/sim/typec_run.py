"""Run the Type-C ECO front end and cold switching boost with preserved passives."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re

import run as engine

HERE = Path(__file__).resolve().parent
engine.CASE_DIR = HERE.parent/"evidence/typec/runs"
CASES = {
    "nominal_cc1": {},
    "nominal_cc2": {"ORIENT":0},
    "default_usb": {"CRP":"56k"},
    "one_point_five_amp": {"CRP":"22k"},
    "source_4p75_short_cable": {"VIN":4.75,"CABLE":.050,"PLOAD":2.475,"LOAD":9.9},
    "source_4p75_nominal_load": {"VIN":4.75,"CABLE":.190},
    "source_4p75_heavy": {"VIN":4.75, "CABLE":.190,"PLOAD":2.475,"LOAD":9.9},
    "source_5p25_heavy": {"VIN":5.25, "PLOAD":2.475,"LOAD":9.9},
    "detach_at_48ms": {"TDROP":"48m"},
    "downgrade_at_48ms": {"TREVOKE":"48m"},
    "r40_open": {"RLINK":"1T"},
    "slow_slew": {"FRONT_RAMP":320},
    "rearm_at_55ms": {"REARM":True},
    "rearm_extended": {"REARM":True,"STOP":95},
    "all_domains_heavy_5v": {"PLOAD":2.475,"LOAD":9.9},
    "ovp_typec_feedback_open": {"FAULT":"ovp","LOAD":0},
    "ocp_typec_forced_sense": {"FAULT":"ocp"},
}


def deck(case, mode):
    circuit = engine.template("proxy" if mode == "proxy" else "vendor")
    front = (HERE/"typec_front.inc").read_text().strip()
    circuit = re.sub(r"(?m)^V5 VIN.*$", front, circuit)
    circuit = circuit.replace("R40 VIN ISOLATE","R40 PROT ISOLATE")
    circuit = circuit.replace("S11 ISOLATE VHV ARMED 0 EFUSE\n.model EFUSE SW(Ron=28m Roff=1G Vt=1.6 Vh=0.05)",
                              """B_HVON HVON 0 V={0.5+0.5*tanh((v(ARMED)-1.6)*90)}
B_HVSLEW 0 HVSLEW I={v(HVON)*425.532*1u*(v(HVSLEW)<6)-(1-v(HVON))*v(HVSLEW)/50}
C_HVSLEW HVSLEW 0 1u
B_U11 ISOLATE VHV I={v(HVON)*min(1.65,max(0,(min(v(ISOLATE),v(HVSLEW))-v(VHV))/.028))+(v(ISOLATE)-v(VHV))/1G}""")
    arm = ("V_ARM ARMCMD 0 PWL(0 0 14.99m 0 15m 3.3 48m 3.3 48.01m 0 54.99m 0 55m 3.3)"
           if case.get("REARM") else "V_ARM ARMCMD 0 PWL(0 0 14.99m 0 15m 3.3)")
    circuit = re.sub(r"(?m)^V_ARM .*$", arm+"\nB_ARMED ARMED 0 V={min(v(ARMCMD),v(V33))}",circuit)
    circuit = re.sub(r"(?m)^V33 .*$", "", circuit)
    circuit = circuit.replace("PULSE(0 1 330u", "PULSE(0 1 15.05m")
    circuit = circuit.replace("200n 30m", "200n 65m").replace("FROM=28m TO=30m","FROM=62m TO=65m")
    circuit = circuit.replace("VLOAD REQUEST 0 7.65m",f"VLOAD REQUEST 0 {case.get('LOAD',7.65)}m")
    circuit = circuit.replace(".save v(HV)", ".save v(VBUS) v(PROT) v(CC1) v(CC2) v(FRONT_EN) v(A3) v(ARMED) v(V33) v(HV)")
    circuit = circuit.replace(".meas tran adapter_peak MAX par('-i(V5)')","")
    circuit = circuit.replace(".meas tran d_vr MAX par('v(HV)-v(DA)')","")
    if case.get("RLINK") == "1T":
        circuit = circuit.replace("R40 PROT ISOLATE {RLINK}", "R40 PROT ISOLATE {RLINK}\nC27 ISOLATE 0 100n\nR41_42 ISOLATE 0 46.5k")
        circuit = circuit.replace("v(ARMED)/3.3}", "v(ARMED)/3.3*(0.5+0.5*tanh((v(VHV)-1.8)*20))}")
    if case.get("FAULT"):
        protection = re.sub(r"(?m)^B_ARMED ARMED.*$", "", (HERE/"protection_proxy.inc").read_text())
        circuit = circuit.replace("min(v(ARMCMD),v(V33))}", "min(v(ARMCMD),v(V33))*min(1,max(0,v(HOLD)/3.3))}")
        circuit = circuit.replace(".save v(VBUS)", ".save v(TRIP) v(HOLD) v(VBUS)")
        fault = ("V_FAULT FAIL 0 PULSE(0 1 48m 10n 10n 30m 100m)\nS_FAIL FB 0 FAIL 0 BOUND"
                 if case["FAULT"]=="ovp" else
                 "V_FAULT FAIL 0 PULSE(0 1 48m 10n 10n 30m 100m)\nVFORCE FORCED 0 .15\nS_FAIL FORCED CS_FILT FAIL 0 BOUND")
        circuit = circuit.replace(".end", protection+"\n"+fault+
                                  "\n.model BOUND SW(Ron=1 Roff=1T Vt=.5 Vh=.02)\n.end")
    if "STOP" in case:
        end = case["STOP"]
        circuit = circuit.replace("65m",f"{end}m").replace("FROM=62m",f"FROM={end-3}m").replace("FROM=32m",f"FROM={end-3}m")
    for parameter,value in case.items():
        if parameter not in {"LOAD","REARM","STOP","FAULT"}:
            circuit, hits = re.subn(r"(?m)^(\.param .*?\b"+parameter+r"=)[^ \n]+",rf"\g<1>{value}",circuit)
            if hits!=1:
                raise ValueError(f"Expected one value for {parameter}, got {hits}")
    if mode == "vendor":
        circuit = circuit.replace("150n uic","150n").replace("method=gear","method=gear rshunt=1e9")
    return circuit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case",choices=tuple(CASES),action="append")
    parser.add_argument("--workers",type=int,default=2)
    parser.add_argument("--vendor-zip",type=Path)
    args = parser.parse_args()
    if args.vendor_zip:
        model = engine.vendor_bytes(args.vendor_zip)
        model = re.sub(rb"(?im)^\.IC\s+V\(COMP\s*\)\s*=.*$",b"* COMP at zero at unpowered input.",model)
        engine.run("vendor_typec_nominal",deck({},"vendor"),"TI Rev H, compatibility COMP .IC omission, finite Type-C input",model)
        return
    selected = {case:CASES[case] for case in args.case} if args.case else CASES
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda item:engine.run(item[0],deck(item[1],"proxy"),
                            "Type-C/eFuse/buck/current-mode engineering proxies",timeout=210),selected.items()))
    if any(result["exit"] != 0 for result in results):
        print("One or more simulations require numerical follow-up.")


if __name__ == "__main__":
    main()
