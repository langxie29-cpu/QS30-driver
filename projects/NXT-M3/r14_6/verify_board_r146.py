"""Validate the saved R14.6 PCB and regenerate the routing evidence."""
import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import subprocess

from build_board import BASE, HERE, SOURCE_STEM, STEM, CLI, BoardRouter, write_json
from route_board import channel_pairs, copper, pcb, uid, xy
from verify_board import (CopperPaths, PROTECTION, REGISTER_PINS, REMOVED_MOUNTS, STOP,
                          component_groups, descriptor, drc_compare, external_gap, find_obstacles,
                          label_for, metrics, native, object_diff, pairs, schematic_pins, write_csv)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv(path, rows):
    if not rows:
        raise ValueError(f"No rows for {path}")
    write_csv(path, list(rows[0]), rows)


def report(root, before, after, a, b, aa, bb):
    rows = [*drc_compare(before, after, a, b, "standard"),
            *drc_compare(before, after, aa, bb, "all_tracks")]
    csv(root / "DRC_BEFORE_AFTER.csv", rows)
    added = [r for r in rows if r["state"] == "added"]
    if added:
        raise RuntimeError(added)
    counts = [Counter(r["category"] for r in rows if r["mode"] == "all_tracks" and r["state"] != state)
              for state in ("added", "removed")]

    paths = CopperPaths(after)
    channels = []
    for i in range(1, 31):
        gap, left, right, layer = external_gap(after, i)
        checked = list(pairs(before, after, paths, channel_pairs(i, after)))
        channels.extend(dict(channel=f"Q{i}", channel_complete=all(row["after_copper"] for row in checked),
                             minimum_external_hv_gap_mm=round(gap, 6),
                             nearest_objects=f"{left} / {right}", nearest_layer=layer, **row)
                        for row in checked)
    csv(root / "CATHODE_30_CHANNEL_AUDIT.csv", channels)
    assert len(channels) == 180 and all(r["after_copper"] for r in channels)

    protection = [dict(section=section, **row) for section, defs in
                  (("OVP/FB/SNUB", PROTECTION), ("J6", STOP))
                  for row in pairs(before, after, paths, defs)]
    csv(root / "PROTECTION_NET_CONNECTIVITY.csv", protection)
    stats = {section: {phase: sum(r["section"] == section and r[f"{phase}_copper"] for r in protection)
                       for phase in ("before", "after")} for section in ("OVP/FB/SNUB", "J6")}

    components = [component_groups(brd) for brd in (before, after)]
    old, new = ({i: set(group) for groups in state.values() for group in groups for i in group}
                for state in components)
    assert old.keys() == new.keys()
    losses = [{"pad": label_for(before, i),
               "lost": [label_for(before, k) for k in sorted(old[i] - new[i])]}
              for i in sorted(old) if not old[i] <= new[i]]
    if losses:
        raise RuntimeError(losses)
    write_json(root / "evidence/copper-components.json",
               {phase: {net: [[label_for(brd, i) for i in group] for group in groups]
                        for net, groups in state.items()}
                for phase, brd, state in zip(("before", "after"), (before, after), components, strict=True)})

    registers = []
    for i in range(20, 24):
        ref = f"U{i}"
        for pad in sorted(after.refs[ref].Pads(), key=lambda x: int(x.GetNumber())):
            pin = pad.GetNumber()
            if pin not in (*REGISTER_PINS, "9"):
                continue
            siblings = new[uid(pad)]
            registers.append(dict(ref=ref, pin=pin, net=pad.GetNetname(),
                                  copper_pad_group_size=len(siblings),
                                  copper_pads="|".join(sorted(label_for(after, k) for k in siblings))))
    csv(root / "SHIFT_REGISTER_CONNECTIVITY.csv", registers)

    def open_rows(board, data):
        for v in data["unconnected_items"]:
            left, right = (item["uuid"] for item in v["items"])
            net = board.by_id[left].GetNetname()
            assert net == board.by_id[right].GetNetname()
            positions = v["items"]
            yield dict(net=net, left=label_for(board, left), right=label_for(board, right),
                       left_uuid=left, right_uuid=right,
                       left_mm=f'{positions[0]["pos"]["x"]},{positions[0]["pos"]["y"]}',
                       right_mm=f'{positions[1]["pos"]["x"]},{positions[1]["pos"]["y"]}')

    blocked = []
    for row in open_rows(after, bb):
        nearby = {side: find_obstacles(after, after.by_id[row[f"{side}_uuid"]]) for side in ("left", "right")}
        blocked.append(dict(**row, nearby_foreign_copper=json.dumps(nearby, ensure_ascii=False)))
    csv(root / "BLOCKED_ROUTES.csv", blocked)
    old_opens = Counter(r["net"] for r in open_rows(before, aa))
    new_opens = Counter(r["net"] for r in blocked)
    summary_rows = [dict(net=n, before=old_opens[n], after=new_opens[n],
                         change=new_opens[n]-old_opens[n], groups_before=len(components[0].get(n, [])),
                         groups_after=len(components[1].get(n, [])))
                    for n in sorted(old_opens.keys() | new_opens.keys())]
    csv(root / "UNCONNECTED_NETS.csv", summary_rows)
    return counts, stats, new_opens


def validate(root):
    evidence = root / "evidence"
    before_stem = BASE / "eda" / SOURCE_STEM
    after_stem = root / "eda" / STEM
    old_path, new_path = (s.with_suffix(s.suffix + ".kicad_pcb") for s in (before_stem, after_stem))
    before, after = BoardRouter(old_path), BoardRouter(new_path)
    records = [{"arguments": ["version"], "exit": 0, "stdout":
                subprocess.check_output([CLI, "version"], text=True).strip()}]
    reports = [evidence / state for state in ("before", "after")]
    for directory, stem in zip(reports, (before_stem, after_stem), strict=True):
        native(directory, stem, records)
    write_json(evidence / "native_commands.json", records)
    (a, aa, ae), (b, bb, be) = [[json.loads((d / name).read_text(encoding="utf-8"))
                                for name in ("DRC.json", "DRC-all-tracks.json", "ERC.json")]
                               for d in reports]
    native_counts = [metrics(d, e) for d, e in ((a, ae), (b, be), (aa, ae), (bb, be))]
    assert native_counts[0]["unconnected"] == 84 and native_counts[0]["clearance"] == 103
    for data in native_counts:
        assert data["parity"] == data["erc_errors"] == data["erc_warnings"] == 0
    assert schematic_pins(reports[0] / "netlist.xml") == schematic_pins(reports[1] / "netlist.xml")
    rules = [sha(s.with_suffix(s.suffix+".kicad_dru")) for s in (before_stem, after_stem)]
    assert rules[0] == rules[1]
    projects = [json.loads(s.with_suffix(s.suffix+".kicad_pro").read_text(encoding="utf-8"))
                for s in (before_stem, after_stem)]
    for project in projects:
        project["meta"].pop("filename", None)
        project["schematic"].pop("top_level_sheets", None)
    assert projects[0] == projects[1]
    assert before.board.GetCopperLayerCount() == after.board.GetCopperLayerCount() == 4
    assert before.refs.keys() == after.refs.keys() and not REMOVED_MOUNTS & after.refs.keys()
    changes = object_diff(before, after)
    assert set(changes["footprints"]) <= {"R81", "R82", "R83", "C35", "C48", "U6", "U13", "U14"}
    assert all(before.refs[r].IsDNP() == after.refs[r].IsDNP() for r in before.refs)
    pads = lambda board: {ident: descriptor(board, ident)[:3] for ident, item in board.by_id.items()
                          if isinstance(item, pcb.PAD)}
    assert pads(before) == pads(after)
    edges = lambda brd: sorted((xy(i.GetStart()), xy(i.GetEnd())) for i in brd.board.GetDrawings()
                               if i.GetLayer() == pcb.Edge_Cuts)
    assert edges(before) == edges(after)
    assert sorted({x for edge in edges(after) for x, _ in edge}) == [50., 180.]
    assert sorted({y for edge in edges(after) for _, y in edge}) == [50., 130.]
    for start in (1, 11, 21):
        for row in (range(start, start+5), range(start+5, start+10)):
            xs = sorted(xy(after.refs[f"Q{i}"].GetPosition())[0] for i in row)
            assert all(math.isclose(b - a, 7.5) for a, b in zip(xs, xs[1:]))
    remote_pads = [p for ref in ("V1","V2","V3") for p in after.refs[ref].Pads()]
    assert len(remote_pads) == 33 and all(p.IsOnLayer(pcb.B_Cu) and not p.IsOnLayer(pcb.F_Cu)
                                          and xy(p.GetDrillSize()) == (0, 0)
                                          and sorted(xy(p.GetSize())) == [1.8, 2.6] for p in remote_pads)
    pin_labels = {str(pin): digit for pin, digit in zip((1,3,13,12,11,10,9,7,6,5,4),
                                                          ("A","0","1","2","3","4","5","6","7","8","9"),
                                                          strict=True)}
    mapping = []
    for name in ("V1", "V2", "V3"):
        pads_by_pin = {p.GetNumber(): p for p in after.refs[name].Pads()}
        assert set(pads_by_pin) == set(pin_labels)
        for pin, label in pin_labels.items():
            p = pads_by_pin[pin]
            position = xy(p.GetPosition())
            group = after.component(p)
            connected_pads = sorted(label_for(after, i) for i in group
                                    if i != uid(p) and isinstance(after.by_id[i], pcb.PAD))
            mapping.append(dict(tube=name, silk=label, tube_pin=pin, net=p.GetNetname(),
                                x_mm=position[0], y_mm=position[1], layer="B.Cu",
                                pad_mm="1.80 x 2.60", drill_mm=0, other_copper_pads="|".join(connected_pads),
                                socket_continuity="HOLD_PHYSICAL_SAMPLE"))
    csv(root / "HARNESS_PIN_MAP.csv", mapping)
    nominal_wire_gap, wire_left, wire_right = min(
        (copper(a, pcb.B_Cu).distance(copper(b, pcb.B_Cu)), label_for(after, uid(a)), label_for(after, uid(b)))
        for a, b in combinations(remote_pads, 2))
    write_json(evidence / "harness-geometry.json", {
        "nominal_min_pad_gap_mm": round(nominal_wire_gap, 6),
        "nearest_pads": [wire_left, wire_right], "measured_assembly": False,
        "anode_groups": [r for r in mapping if r["silk"] == "A"]})
    write_json(evidence / "object-and-net-diff.json", changes)
    counts, protection, opens = report(root, before, after, a, b, aa, bb)
    all_registers = {name: opens[name] for name in
                     ("SER0", "SER1", "SER2", "SER3", "SR_CLK_BUS", "SR_LATCH_BUS", "HC_CLEAR_N", "HC_OE_N")}
    result = dict(kiCad_version=records[0]["stdout"], native=dict(zip(
                  ("before", "after", "before_all_tracks", "after_all_tracks"), native_counts)),
                  drc_groups_before=counts[0], drc_groups_after=counts[1],
                  added_violations=0, prior_connections_lost=0, project_settings_unchanged=True,
                  cathodes="30/30",
                  cathode_endpoints="180/180", protection=protection, register_opens=all_registers,
                  rule_sha256=rules[0], board_sha256=sha(new_path),
                  baseline_board_sha256=sha(old_path), board_size_mm=[130,80], copper_layers=4,
                  wire_pads=33, frozen_refs=["MH1", "MH2", "MH3", "MH4", "J2", "J3", "J4", "J5", "J6"],
                  footprint_changes=list(changes["footprints"]))
    write_json(root / "ROUTING_GATE_RESULTS.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE)
    validate(parser.parse_args().out.resolve())
