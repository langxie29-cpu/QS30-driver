"""Independently audit the saved PCB, KiCad reports and schematic XML."""
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
EDA = HERE / "eda/NXT-M3-R11.kicad_pcb"
R10 = HERE.parent / "r10/eda/NXT-M3-R10.kicad_pcb"


def uuid(item):
    return str(item.m_Uuid.AsString())


def point(item):
    position = item.GetPosition()
    return pcb.ToMM(position.x), pcb.ToMM(position.y)


def rect(value):
    return tuple(pcb.ToMM(v) for v in (value.GetLeft(), value.GetTop(), value.GetRight(), value.GetBottom()))


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def physical_netlist(source):
    return {net.get("name"): {(n.get("ref"), n.get("pin")) for n in net.findall("node")}
            for net in ET.parse(source).findall("./nets/net")}


def main(out):
    target = Path(out)
    raw = json.loads((target/"DRC.json").read_text(encoding="utf-8-sig"))
    board = pcb.LoadBoard(str(EDA))
    b0 = pcb.LoadBoard(str(R10))
    footprints = {fp.GetReference():fp for fp in board.GetFootprints()}
    original = {fp.GetReference():fp for fp in b0.GetFootprints()}
    traces = list(board.GetTracks())
    segments = [t for t in traces if not isinstance(t,pcb.PCB_VIA)]
    ids = {uuid(t): (t.GetNetname(),"") for t in traces}
    ids.update({uuid(zone):(zone.GetNetname(),"zone") for zone in board.Zones()})
    by_net = defaultdict(set)
    for ref, fp in footprints.items():
        for pad in fp.Pads():
            net = pad.GetNetname()
            ids[uuid(pad)] = (net,ref)
            if net and not net.startswith("unconnected-"):
                by_net[net].add((ref,pad.GetNumber()))
    exported = physical_netlist(target/"native_netlist.xml")
    discrepancies = {net: sorted(by_net[net] ^ {item for item in exported.get(net,set())
                                              if item[0] in footprints})
                     for net in set(by_net)|set(exported)
                     if not net.startswith("unconnected-")}
    assert not any(discrepancies.values()), discrepancies
    absent = {net: sorted([p for p in pads if p[0] in {"V1","V2","V3"}])
              for net,pads in exported.items() if not net.startswith("unconnected-")
              and any(p[0] in {"V1","V2","V3"} for p in pads)}
    assert len(absent) == 33
    multi = {net for net, pads in by_net.items() if len(pads)>1}
    remaining = Counter()
    for result in raw["unconnected_items"]:
        nets = {ids[item["uuid"]][0] for item in result["items"] if item["uuid"] in ids}
        nets.discard("")
        assert len(nets) == 1, (nets,result)
        remaining.update(nets)
    sectors = defaultdict(lambda: {"segments":0,"vias":0,"length_mm":0})
    for track in traces:
        line = sectors[track.GetNetname()]
        if isinstance(track,pcb.PCB_VIA):
            line["vias"] += 1
        else:
            line["segments"] += 1
            line["length_mm"] += pcb.ToMM(track.GetLength())
    with (target/"net_completion.csv").open("w",newline="",encoding="utf-8") as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(("net","pcb_pad_endpoints","track_segments","vias","length_mm","drc_open_items","missing_socket_nodes"))
        for net in sorted(set(by_net)|set(absent)):
            line = sectors[net]
            writer.writerow([net,len(by_net[net]),line["segments"],line["vias"],round(line["length_mm"],3),
                             remaining[net], " ".join(".".join(p) for p in absent.get(net,[]))])
    side_bounds = {}
    for ref, fp in footprints.items():
        hull = fp.GetCourtyard(fp.GetLayer()).BBox()
        if hull.GetWidth() > 0 and hull.GetHeight() > 0:
            side_bounds[ref] = fp.GetLayer(), rect(hull)
    collisions = [[one,two] for one,(side, a) in side_bounds.items() for two,(other,b) in side_bounds.items()
                  if one<two and side==other and intersects(a,b)]
    bbox_edges = [ref for ref, (_, box) in side_bounds.items()
                  if box[0]<50 or box[1]<50 or box[2]>180 or box[3]>130]
    front_glass = []
    for ref,(side,bounds) in side_bounds.items():
        if side == pcb.F_Cu:
            for index, cx in enumerate((77,115,153),1):
                cy = 102
                xx = min(bounds[2], max(bounds[0], cx))
                yy = min(bounds[3], max(bounds[1], cy))
                if math.hypot(cx-xx, cy-yy) < 14.8:
                    front_glass.append([ref,index])
    new_copper_ids = {uuid(t) for t in traces}
    violations = Counter(v["type"] for v in raw["violations"])
    summary = {
        "r10_unconnected_native_connectivity":b0.GetConnectivity().GetUnconnectedCount(False),
        "r11_unconnected_native_connectivity":board.GetConnectivity().GetUnconnectedCount(False),
        "r11_unconnected_native_drc":sum(remaining.values()), "pcb_multiterminal_nets":len(multi),
        "pcb_multiterminal_nets_fully_connected":len(multi - set(remaining)),
        "pcb_distinct_nets_with_open_items":len(remaining), "logical_socket_nets_absent":sorted(absent),
        "distinct_open_nets_including_sockets":len(set(remaining)|set(absent)),
        "pcb_pin_network_differences":0,
        "footprints":len(footprints), "side_counts":dict(Counter(board.GetLayerName(fp.GetLayer()) for fp in footprints.values())),
        "moved_footprints":{ref:[list(point(original[ref])),list(point(fp))]
                            for ref,fp in footprints.items() if ref in original and point(fp)!=point(original[ref])},
        "segments":len(segments), "vias":len(traces)-len(segments), "nets_with_copper":len([n for n in sectors if sectors[n]["segments"]]),
        "length_mm_by_layer":{board.GetLayerName(layer): round(sum(pcb.ToMM(t.GetLength()) for t in segments
                                   if t.GetLayer()==layer),3) for layer in (pcb.F_Cu,pcb.B_Cu)},
        "rules":dict(violations), "severity":dict(Counter(v["severity"] for v in raw["violations"])),
        "drc_rules_involving_tracks_vias":sum(any(i["uuid"] in new_copper_ids for i in v["items"])
                                             for v in raw["violations"]),
        "same_side_courtyard_bbox_intersections":collisions, "courtyard_outside_board":bbox_edges,
        "front_courtyard_intersects_glass_projection":front_glass,
        "copper_layers":board.GetCopperLayerCount(), "rules_excluded":len(raw.get("excluded",[])),
    }
    (target/"board_independent.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
