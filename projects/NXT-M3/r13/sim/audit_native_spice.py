"""Read raw waveform and native DRC exports to cross-check adjudication."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".local"
EDA = ROOT / "evidence/eda_baseline"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def replay(folder):
    raw = folder / "waveform.raw"
    with raw.open("rb") as file:
        header = bytearray()
        while line := file.readline():
            if line.strip() == b"Binary:":
                break
            header.extend(line)
        else:
            raise ValueError(f"Missing raw header in {raw}")
        offset = file.tell()
    fields = [m.decode() for m in re.findall(rb"(?m)^\s*\d+\s+(\S+)\s+\S+\s*$",header)]
    n = int(re.search(rb"No\. Points:\s*(\d+)",header)[1])
    data = np.memmap(raw, dtype="<f8", offset=offset, mode="r", shape=(n,len(fields)))
    values = dict(zip(fields,data.T))
    t = values["time"]
    y = values["v(hv)"]
    select = t >= .062
    tf, yf = t[select], y[select]
    difference = np.diff(tf)
    sample_indices = sorted(set(np.linspace(0,n-1,161,dtype=int)) |
                            set(np.linspace(n-1400,n-1,140,dtype=int)))
    with (OUT/(folder.name+"_sample.csv")).open("w",encoding="utf-8",newline="") as file:
        writer = csv.writer(file)
        writer.writerow(fields)
        writer.writerows(np.round(data[sample_indices],12))
    if not np.all(np.isfinite(data)) or np.any(np.diff(t) < 0):
        raise ValueError("Nonfinite or unordered waveform")
    return {"id":folder.name, "evidence":"PROXY", "raw_sha256":sha(raw),
            "raw_size_bytes":raw.stat().st_size, "raw_path":str(raw),
            "circuit_sha256":sha(folder/"circuit.cir"), "log_sha256":sha(folder/"run.log"),
            "first_s":float(t[0]),"last_s":float(t[-1]),"points":n,
            "hv_initial_v":float(y[0]),
            "hv_time_weighted_62_to_65_ms":float(np.dot(difference,(yf[1:]+yf[:-1])/2)/(tf[-1]-tf[0])),
            "hv_ripple_vpp_62_to_65_ms":float(np.ptp(yf))}


def native():
    drc = json.loads((EDA/"DRC.json").read_text(encoding="utf-8-sig"))
    counts = Counter()
    for item in drc["unconnected_items"]:
        names = {match for node in item["items"] for match in
                 re.findall(r"\[([^\]]+)\]",node["description"])}
        if len(names) != 1:
            raise ValueError(f"Unexpected DRC net attribution {names}")
        counts[next(iter(names))] += 1
    nets = ElementTree.parse(EDA/"native_netlist.xml").findall("./nets/net")
    multi = {net.get("name") for net in nets if len(net.findall("node")) >= 2}
    represented = {name for name in counts if name in multi}
    previews = {p.name: {"sha256":sha(p), "bytes":p.stat().st_size}
                for p in sorted((EDA/"preview").iterdir()) if p.is_file()}
    return {"real_project":"R11 baseline", "schematic_nets":len(nets),
            "schematic_multi_terminal_nets":len(multi),
            "multi_terminal_without_drc_open":len(multi - represented),
            "declared_drc_open_items":sum(counts.values()),
            "drc_open_distinct_net_names":len(counts),
            "drc_open_names_missing_from_multi_terminal_netlist":sorted(counts.keys()-multi),
            "drc_error_categories":Counter(row["type"] for row in drc["violations"]),
            "drc_open_by_net":counts, "parity_count":len(drc["schematic_parity"]),
            "previews":previews, "release":"HOLD"}


if __name__ == "__main__":
    write(OUT/"d_proxy_replay.json", [replay(x) for x in sorted((ROOT/"evidence/spice/d_replay").iterdir())])
    write(OUT/"native_audit.json",native())
