"""Run low-line sensitivity cases on the existing Type-C and boost proxies."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import run
from typec_run import deck

HERE = Path(__file__).resolve().parent
run.CASE_DIR = HERE.parent/"evidence/blocker_closure/lowline"
INPUT = {"VIN":4.75,"CABLE":.190,"PLOAD":2.475,"LOAD":9.9}
CASES = {
    "l3_low_tolerance": {"LMAIN":"17.6u"},
    "l3_high_tolerance": {"LMAIN":"26.4u"},
    "cold_nominal_repeat": {},
    "window_18u_minus10": {"LMAIN":"16.2u","LSER":"39.5m"},
    "window_18u_plus10": {"LMAIN":"19.8u","LSER":"39.5m"},
    "candidate_15u_low_at_4p75": {"LMAIN":"12u","LSER":"31m"},
    "candidate_15u_high_at_4p75": {"LMAIN":"18u","LSER":"31m"},
    "diagnostic_80khz_22u": {"DIAG_KHZ":80},
    "diagnostic_80khz_26p4u": {"DIAG_KHZ":80,"LMAIN":"26.4u"},
    "candidate_15u_highline_light": {"LMAIN":"12u","LSER":"31m","VIN":5.25,"LOAD":0,"PLOAD":.76},
}


def case(item):
    name, change = item
    freq=change.get("DIAG_KHZ")
    fixture = deck(INPUT|{k:v for k,v in change.items() if k!="DIAG_KHZ"},"proxy")
    if freq:
        period=1000/freq
        fixture=fixture.replace("95n 10u)","95n %.6gu)"%period)
        fixture=fixture.replace("/10u)*10u",f"/{period:g}u)*{period:g}u")
        fixture=fixture.replace("v(PHASE)>9.25u",f"v(PHASE)>{.925*period:g}u")
    fixture = fixture.replace(".end", """* Rail voltage at the boost terminals, after both eFuses
.meas tran hv_input_avg AVG v(VHV) FROM=62m TO=65m
.end""")
    return run.run(name, fixture, ("Type-C and controller proxy with an explicit clock hypothesis" if freq else
                    "Type-C and switching-controller proxies, L3 tolerance sensitivity"),
                   timeout=200)


if __name__=="__main__":
    selected = {n:CASES[n] for n in sys.argv[1:]} if len(sys.argv)>1 else CASES
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(case,selected.items()))
