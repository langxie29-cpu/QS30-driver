"""Capture KiCad reports and classify raw item UUIDs against their native objects."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "r11"))
from route import CLI, gap

EVIDENCE = HERE / "evidence"
BASE = "../r11/eda/NXT-M3-R11"
R14 = "eda/NXT-M3-R14"
PARTS = {f"Q{i}" for i in range(1, 31)}
Q1_NETS = {"BASE_00", "DRV_00", "K1_0"}


def load(path):
    return json.loads((HERE / path).read_text(encoding="utf-8-sig"))


def write(path, data):
    (HERE / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call(args, runs):
    result = subprocess.run([str(CLI), *args], cwd=HERE, capture_output=True)
    runs.append({"args": args, "exit": result.returncode,
                 "stdout": result.stdout.decode("utf-8", "replace"),
                 "stderr": result.stderr.decode("utf-8", "replace")})
    if result.returncode not in (0, 5):
        raise RuntimeError(runs[-1])


def run():
    runs = []
    call(["version"], runs)
    for project, outputs in [(BASE, ("baseline", "baseline")), (R14, ("erc", "drc"))]:
        erc, drc = outputs
        for fmt, suffix in (("report", "rpt"), ("json", "json")):
            options = ["--format", fmt, "--severity-all", "--exit-code-violations"]
            call(["sch", "erc", *options, "-o", f"evidence/{erc}/ERC.{suffix}", project+".kicad_sch"], runs)
            call(["pcb", "drc", "--schematic-parity", *options, "-o", f"evidence/{drc}/DRC.{suffix}",
                  project+".kicad_pcb"], runs)
    write("evidence/pcb/native_commands.json", runs)


def objects(project):
    # Copy data out of SWIG objects while their owning board is alive.
    board = pcb.LoadBoard(str(HERE / (project + ".kicad_pcb")))
    result = {}

    def add(obj, ref, kind, net="", pad=""):
        result[str(obj.m_Uuid.AsString())] = (ref, kind, net, pad)
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        add(fp, ref, "footprint")
        for pad in fp.Pads():
            add(pad, ref, "pad", pad.GetNetname(), pad.GetNumber())
        for item in fp.GraphicalItems():
            add(item, ref, "graphic")
    for tr in board.GetTracks():
        add(tr, "", "via" if isinstance(tr, pcb.PCB_VIA) else "track", tr.GetNetname())
    for z in board.Zones():
        add(z, "", "zone", z.GetNetname())
    for item in board.GetDrawings():
        add(item, "", "board_graphic")
    return result


def sections(report, obj):
    buckets = Counter()
    rows = []
    for index, issue in enumerate(report["violations"], 1):
        things = [obj.get(item["uuid"], ("", "other", "", "")) for item in issue["items"]]
        refs = {ref for ref, _, _, _ in things if ref}
        kinds = {kind for _, kind, _, _ in things}
        nets = {net for _, _, net, _ in things if net}
        if kinds == {"pad"}:
            category = "same_footprint_pad" if len(refs) == 1 else "between_footprint_pads"
        elif any(k in {"via", "track", "zone"} for k in kinds):
            category = "routed_copper_or_zone"
        else:
            category = "manufacturing_mechanical_or_other"
        voltage = ["HV" if gap(net) > .2 else "LV" for net in nets]
        if "HV" in voltage:
            domain = "HV_to_HV" if "LV" not in voltage and len(nets) > 1 else "HV_to_LV_or_boundary"
        else:
            domain = "LV_or_unclassified"
        cathodes = sorted(refs & PARTS, key=lambda ref: int(ref[1:]))
        own_q = kinds == {"pad"} and len(refs) == 1 and bool(cathodes)
        if issue["type"] == "clearance":
            buckets[category] += 1
            buckets[domain] += 1
            if cathodes:
                buckets["any_Q1_Q30"] += 1
            if own_q:
                buckets["same_Q1_Q30_package"] += 1
            if "Q1" in cathodes:
                buckets["Q1_clearance"] += 1
        values = re.findall(r"([\d.]+) mm", issue["description"])
        rows.append([index, issue["type"], issue["severity"], category, domain, " ".join(cathodes),
                     int(own_q), *([values[0], values[-1]] if values else ["", ""]),
                     "|".join(f"{ref}.{pad}:{kind}:{net}" for ref, kind, net, pad in things),
                     "|".join(item["uuid"] for item in issue["items"]), issue["description"]])
    return buckets, rows


def summarize(stem, project, csv_output):
    report = load(stem)
    obj = objects(project)
    classification, rows = sections(report, obj)
    with (HERE / csv_output).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["index", "type", "severity", "geometry", "domain", "cathode_refs",
                         "same_q_package", "limit_mm", "measured_mm", "objects", "uuids", "native_text"])
        writer.writerows(rows)

    opens = Counter()
    for issue in report["unconnected_items"]:
        nets = {obj.get(i["uuid"], ("", "", "", ""))[2] for i in issue["items"]} - {""}
        if len(nets) != 1:
            # Raw DRC also represents generated copper or zones.
            nets = set(re.findall(r"\[([^\]]+)\]", " ".join(i["description"] for i in issue["items"])))
        opens.update(nets)
    return {
        "violations_by_type": Counter(i["type"] for i in report["violations"]),
        "violations_by_severity": Counter(i["severity"] for i in report["violations"]),
        "clearance_groups": classification,
        "unconnected": len(report["unconnected_items"]),
        "unconnected_nets": len(opens),
        "opens_by_net": dict(sorted(opens.items())),
        "parity": Counter(i["type"] for i in report["schematic_parity"]),
        "ignored_drc": [i["key"] for i in report["ignored_checks"]],
        "q1_open_non_ground": {net: opens[net] for net in sorted(Q1_NETS)},
    }


def netlist_checks():
    baseline = ET.parse(EVIDENCE / "baseline/netlist.xml")
    candidate = ET.parse(EVIDENCE / "pcb/netlist.xml")

    def pins(tree):
        return {(node.get("ref"), node.get("pin")): net.get("name")
                for net in tree.findall("./nets/net") for node in net.findall("node")}

    old, new = pins(baseline), pins(candidate)
    changed = [(r, p, v, new.get((r, p))) for (r, p), v in old.items() if new.get((r, p)) != v]
    assert {(r, p) for r, p, _, _ in changed} == {("U3", str(i)) for i in range(18, 22)}, changed
    assert new["U11", "1"] == "ARMED" and new["Q35", "3"] == "FAULT_N"
    assert [new["Q1", n] for n in "123"] == ["BASE_00", "GND", "K1_0"]
    assert candidate.find("./components/comp[@ref='R40']/property[@name='dnp']") is not None
    assert candidate.find("./components/comp[@ref='J5']/property[@name='dnp']") is not None
    gpio = [{"pad": n.get("pin"), "pin": n.get("pinfunction"), "net": x.get("name")}
            for x in candidate.findall("./nets/net") for n in x.findall("./node[@ref='U3']")]
    return {"changed_existing_pins": sorted(changed), "gpio_all_pins": sorted(gpio, key=lambda t: int(t["pad"])),
            "added_pins": len(set(new) - set(old)), "r40_dnp": True, "j5_dnp": True}


def board_audit(project):
    board = pcb.LoadBoard(str(HERE / (project + ".kicad_pcb")))
    points = lambda coord: [round(pcb.ToMM(v), 4) for v in coord]
    footprints = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("MH") or ref in {"U3", "U8", "U11", "J5", "J6", "Q1", "R40", "R100", "R200"}:
            footprints[ref] = {
                "at_mm": points(fp.GetPosition()), "angle": fp.GetOrientationDegrees(),
                "layer": fp.GetLayerName(), "footprint": fp.GetFPIDAsString(),
                "pads": sorted((p.GetNumber(), p.GetNetname(), points(p.GetPosition()), points(p.GetDrillSize()))
                               for p in fp.Pads()),
                "dnp": bool(fp.GetAttributes() & pcb.FP_DNP),
            }
    edge = [(points(x.GetStart()), points(x.GetEnd())) for x in board.GetDrawings()
            if x.GetLayer() == pcb.Edge_Cuts]
    rf = [(z.GetZoneName(), points(z.GetBoundingBox().GetOrigin()), points(z.GetBoundingBox().GetEnd()))
          for z in board.Zones() if z.GetZoneName().startswith("RF plan")]
    tracks = {str(t.m_Uuid.AsString()): t.GetNetname() for t in board.GetTracks()}
    return {"edge": edge, "rf_keepouts": rf, "footprints": footprints}, tracks


def board_delta():
    before, old_tracks = board_audit(BASE)
    after, new_tracks = board_audit(R14)
    assert before["edge"] == after["edge"]
    assert before["rf_keepouts"] == after["rf_keepouts"]
    for ref in before["footprints"]:
        if ref.startswith("MH"):
            assert before["footprints"][ref] == after["footprints"][ref], ref
    assert after["footprints"]["R40"]["dnp"]
    assert after["footprints"]["J5"]["dnp"]
    removed = {k: v for k, v in old_tracks.items() if k not in new_tracks}
    assert removed and set(removed.values()) == {"BASE_00"}, removed
    write("evidence/pcb/mechanical_and_copper.json",
          {"baseline": before, "candidate": after, "removed_native_tracks": removed,
           "new_tracks_and_vias": sum(k not in old_tracks for k in new_tracks)})


def main():
    run()
    results = {}
    settings = {}
    for label, project, erc_path, drc_path, csv_out in (
        ("r11", BASE, "baseline", "baseline", "baseline/clearance_causes.csv"),
        ("r14", R14, "erc", "drc", "drc/violation_causes.csv"),
    ):
        results[label] = summarize(f"evidence/{drc_path}/DRC.json", project, f"evidence/{csv_out}")
        erc = load(f"evidence/{erc_path}/ERC.json")
        results[label]["erc"] = Counter(v["severity"] for s in erc["sheets"] for v in s["violations"])
        results[label]["ignored_erc"] = [i["key"] for i in erc["ignored_checks"]]
        project_data = load(project + ".kicad_pro")
        project_data["meta"].pop("filename", None)
        rules = (HERE / (project + ".kicad_dru")).read_bytes()
        settings[label] = project_data, rules
    assert settings["r11"] == settings["r14"], "Unexpected rule or project-setting change"
    results["netlist"] = netlist_checks()
    board_delta()
    results["shared_dru_sha256"] = hashlib.sha256(settings["r11"][1]).hexdigest()
    write("evidence/pcb/summary.json", results)
    for label in ("r11", "r14"):
        print(label, {k: v for k, v in results[label].items() if k != "opens_by_net"})


if __name__ == "__main__":
    main()
