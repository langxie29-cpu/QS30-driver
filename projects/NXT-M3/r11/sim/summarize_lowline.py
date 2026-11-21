"""Verify full transient evidence and write the low-line qualification matrix."""
import csv
import json
from pathlib import Path

from lowline_tolerance import CASES, INPUT
from typec_measure import measure

PROJECT = Path(__file__).resolve().parent.parent
RUNS = PROJECT / "evidence" / "blocker_closure" / "lowline"


def main():
    rows = []
    for name, overrides in CASES.items():
        conditions = INPUT | overrides
        path = RUNS / name / "measurement.json"
        info = json.loads(path.read_text(encoding="utf-8"))
        if info["case"] != name:
            raise ValueError(f"Case name mismatch in {path}")
        values = info["measurements"]
        complete = info["exit"] == 0 and info["raw_points"] > 0
        waveform = measure(path, info) if complete else {}
        required = ("hv_final", "hv_ripple", "hv_input_avg", "hv_peak", "il_peak", "q_vds")
        valid = complete and all(key in values for key in required)
        status = "UNKNOWN"
        if valid:
            in_window = 165 <= values["hv_final"] <= 175 and values["hv_ripple"] <= 1
            status = "LIMITED_PASS" if in_window else "REWORK"
        rows.append({
            "case": name, "source_v": conditions["VIN"], "cable_ohm": conditions["CABLE"],
            "3v3_load_w": conditions["PLOAD"], "hv_load_ma": conditions["LOAD"],
            "inductance": conditions.get("LMAIN", "22u"),
            "inductor_dcr": conditions.get("LSER", "39.5m"),
            "clock_khz": conditions.get("DIAG_KHZ", 100),
            "criteria": "Final 165–175 V and ripple <=1 Vpp (proxy screen)",
            "status": status, "return_code": info["exit"], "seconds": info["seconds"],
            **{key: values.get(key, "") for key in required},
            "initial_hv_v": waveform.get("hv_initial_v", ""),
            "end_time_s": waveform.get("t_last_s", ""), "model": info["model"],
            "command": " ".join(info["command"]),
            "evidence": path.parent.relative_to(PROJECT).as_posix(),
            "waveform_sha256": info["waveform_sha256"],
            "physical_validation": "Real controller, eFuse, losses and loop over tolerances and temperature",
        })
    with (PROJECT / "LOWLINE_BLOCKER_SWEEP.csv").open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=rows[0].keys())
        output.writeheader()
        output.writerows(rows)
    print(f'{len(rows)} runs: {sum(row["status"] != "UNKNOWN" for row in rows)} valid waveforms, '
          f'{sum(row["status"] == "LIMITED_PASS" for row in rows)} within proxy screen')


if __name__ == "__main__":
    main()
