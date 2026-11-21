"""Read real ngspice binary waveforms, retain CSV samples and measurements."""
import csv
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def process(file):
    with file.open("rb") as stream:
        description = []
        for line in stream:
            if line.strip() == b"Binary:":
                break
            description.append(line.decode("ascii", "replace"))
        start = stream.tell()
    variables = [line.split()[1] for line in description if line.startswith("\t") and len(line.split()) >= 3]
    count = int(next(row.split(":")[1] for row in description if row.startswith("No. Points:")))
    data = np.memmap(file, dtype="<f8", offset=start, mode="r", shape=(count, len(variables)))
    traces = {name.lower(): data[:, index] for index, name in enumerate(variables)}
    t = traces["time"]
    if not np.all(np.isfinite(data)) or np.any(np.diff(t) < 0):
        raise ValueError(f"Invalid waveform: {file}")
    metrics = {"start_s": float(t[0]), "last_s": float(t[-1]), "samples": int(count)}
    if "v(da)" in traces:
        metrics["diode_reverse_peak_v"] = float(np.max(traces["v(hv)"] - traces["v(da)"]))
        active = t >= 1e-3
        metrics["input_peak_after_1ms_a"] = float(-np.min(traces["i(v5)"][active]))
        metrics["bus_initial_v"] = float(traces["v(hv)"][0])
        metrics["bus_last_v"] = float(traces["v(hv)"][-1])
        metrics["boost_armed_current_limit_screen_a"] = float(np.max(traces["i(l3)"]))
    (file.parent / "waveform_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    selection = np.linspace(0, count-1, min(501, count), dtype=int)
    with (file.parent / "waveform_sample.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(variables)
        writer.writerows(np.round(data[selection], 12))


for raw in sorted((HERE.parent / "evidence/r2").glob("*/waveform.raw")):
    if (raw.parent / "measurement.json").exists():
        process(raw)
