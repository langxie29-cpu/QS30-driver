"""Apply the acceptance matrix to archived results without grading proxy as qualification."""
import argparse
import csv
from itertools import product
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT/"evidence"
NORMAL = list(product((4.75,5.0,5.25,4.3),(.76,2.475),(0,7.65,9.9)))
FAULTS = (
    "load_step_recovery","power_down_restart","feedback_open","feedback_short","physical_disconnect",
    "input_backfeed","independent_ovp","independent_ocp","hardware_latch","residual_voltage",
    "one_bleeder_open","false_residual_low","cathode_partial_conduction","thermal_soak",
)
FIELDS = ["Route","Case","Source V","Cable Ohm","LV W","HV mA","Grade","Evidence",
          "HV Average V","Ripple Vpp","Required closure"]


def archived():
    found = {}
    for wave in ("round1","round2"):
        for path in sorted((EVIDENCE/"spice"/wave).glob("*/measurement.json")):
            data = json.loads(path.read_text(encoding="utf8"))
            case = data["case"]
            key = (case["route"].upper(),case["vin"],case["plv"],round(case["ihv"]*1000,3))
            record = {"case":case["id"],"status":data["status"],
                      "file":path.relative_to(ROOT).as_posix(),"avg":data.get("hv_avg_v",""),
                      "ripple":data.get("hv_ripple_vpp","")}
            found.setdefault(key,[]).append(record)
    return found


def main(out):
    tested = archived()
    lines = []
    for route in "ABCD":
        for vin, lv, hv in NORMAL:
            cases = tested.get((route,vin,lv,hv),[])
            base = {"Route":route,"Case":"cold_start","Source V":vin,"Cable Ohm":.19 if vin!=4.3 else 0,
                    "LV W":lv,"HV mA":hv,
                    "Required closure":"170 V ±5 V, ripple ≤1 Vpp, zero-energy start, validated controller and protection"}
            if not cases:
                lines.append(base | {"Grade":"NOT_RUN"} )
            for case in cases:
                lines.append(base | {"Grade":case["status"],"Case":case["case"],"Evidence":case["file"],
                                     "HV Average V":case["avg"],"Ripple Vpp":case["ripple"]})
        for fault in FAULTS:
            lines.append({"Route":route,"Case":fault,"Grade":"NOT_QUALIFIED",
                          "Evidence":"R11 prior proxy evidence only" if route=="D" else "",
                          "Required closure":"Real component model, failure limits, raw evidence and hardware test disposition"})
    lines.extend([
        {"Route":"B","Case":"upstream_180v_reference_approx","Grade":"VENDOR_TIMEOUT",
         "Evidence":"evidence/spice/round1/b_ref_approx/measurement.json"},
        {"Route":"D","Case":"R11_100kHz_replay","Source V":4.75,"Cable Ohm":.19,"LV W":2.475,"HV mA":9.9,
         "Grade":"PROXY_REWORK","HV Average V":155.842763,"Ripple Vpp":1.108349,
         "Evidence":"evidence/spice/d_replay/cold_nominal_repeat/measurement.json"},
        {"Route":"D","Case":"R11_80kHz_replay","Source V":4.75,"Cable Ohm":.19,"LV W":2.475,"HV mA":9.9,
         "Grade":"PROXY_SCREEN_ONLY","HV Average V":169.846812,"Ripple Vpp":.541549,
         "Evidence":"evidence/spice/d_replay/diagnostic_80khz_22u/measurement.json"},
    ])
    with out.open("w",encoding="utf-8",newline="") as file:
        writer = csv.DictWriter(file,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    main(parser.parse_args().out)
