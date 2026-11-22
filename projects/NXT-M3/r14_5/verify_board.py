"""Capture native reports and audit R14.5 copper against R14.4."""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pcbnew as pcb

from route_board import (BASE, BASE_STEM, HERE, LAYERS, STEM, STOP, BoardRouter,
                         channel_pairs, gap, polygons, uid, xy)
from shapely import box
from shapely.strtree import STRtree
from remote_display import REMOVED_MOUNTS

sys.path.insert(0, str(HERE.parent / "r14_4"))
from verify_p01 import classify, drc_distances, drc_key, metrics, schematic_pins, write_csv

CLI = Path(sys.executable).with_name("kicad-cli.exe")
MECHANICAL = {"J2","J3","J4","J5","J6","U3","U4"}
INTRINSIC = {"mmbta42_candidate_exception", "switch_package", "lv_same_package"}
PROTECTION = (
    ("ovp_high", "R60.1", "C47.1"),
    ("ovp_1", "R60.2", "R61.1"),
    ("ovp_2", "R61.2", "R62.1"),
    ("ovp_3", "R62.2", "R63.1"),
    ("ovp_sense", "R63.2", "R64.1"),
    ("ovp_comp", "R64.1", "U13.2"),
    ("ovp_cap", "C35.1", "U13.2"),
    ("ovp_return", "R64.2", "U13.4"),
    ("feedback_high", "R81.1", "C47.1"),
    ("feedback_1", "R81.2", "R82.1"),
    ("feedback_2", "R82.2", "R83.1"),
    ("feedback_3", "R83.2", "R84.1"),
    ("feedback_comp", "R84.2", "U17.8"),
    ("feedback_bottom", "R84.2", "R85.1"),
    ("feedback_return", "R85.2", "U17.7"),
    ("rectifier_switch", "D3.2", "Q32.2"),
    ("inductor_switch", "L3.2", "Q32.2"),
    ("rectifier_bus", "D3.1", "C47.1"),
    ("bus_return", "C47.2", "R79.2"),
    ("switch_snubber", "D3.2", "R86.1"),
    ("snubber_cap", "R86.2", "C48.1"),
    ("snubber_return", "C48.2", "R79.2"),
    ("watchdog_logger", "U3.17", "U25.7"),
)
REGISTER_PINS = ("8", "10", "11", "12", "13", "14", "16")
REGISTER_OUTPUT = {"U20": "SER1", "U21": "SER2", "U22": "SER3"}


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def native(out, stem, records):
    out.mkdir(parents=True, exist_ok=True)
    pcb_file = stem.parent / f"{stem.name}.kicad_pcb"
    sch_file = stem.parent / f"{stem.name}.kicad_sch"

    def run(args, output, source, allowed):
        product = out / output
        rel = lambda path: Path(os.path.relpath(path,HERE)).as_posix()
        call = [*args, "-o", rel(product), rel(source)]
        proc = subprocess.run([CLI, *call],cwd=HERE,capture_output=True,encoding="utf-8",errors="replace")
        records.append(dict(arguments=call, exit=proc.returncode, stdout=proc.stdout,
                            stderr=proc.stderr))
        if proc.returncode not in allowed or not product.is_file():
            raise RuntimeError(records[-1])

    drc = ["pcb","drc","--severity-all","--schematic-parity","--exit-code-violations"]
    erc = ["sch","erc","--severity-all","--exit-code-violations"]
    run([*drc,"--format","json"],"DRC.json",pcb_file,{0,5})
    run([*drc,"--all-track-errors","--format","json"],"DRC-all-tracks.json",pcb_file,{0,5})
    run([*drc,"--format","report"],"DRC.rpt",pcb_file,{0,5})
    run([*erc,"--format","json"],"ERC.json",sch_file,{0,5})
    run([*erc,"--format","report"],"ERC.rpt",sch_file,{0,5})
    run(["sch","export","netlist","--format","kicadxml"],"netlist.xml",sch_file,{0})


def descriptor(board, ident):
    item = board.by_id.get(ident)
    if item is None:
        return ("","","", "", "")
    ref = item.GetParentFootprint().GetReference() if isinstance(item,pcb.PAD) else ""
    pin = item.GetNumber() if isinstance(item,pcb.PAD) else ""
    layers = "/".join(board.board.GetLayerName(layer) for layer in LAYERS if item.IsOnLayer(layer))
    return ref,pin,item.GetNetname(),layers,type(item).__name__


def label_for(board, ident):
    ref,pin,net,layer,kind = descriptor(board,ident)
    return f"{ref}.{pin}" if ref else f"{kind} {net} {ident}"


def drc_compare(before, after, a, b, mode):
    report = [{drc_key(v): v for v in r["violations"]} for r in (a,b)]
    for key in sorted(report[0].keys() | report[1].keys()):
        old,new = (r.get(key) for r in report)
        obj = new or old
        board = after if new else before
        required, actual = drc_distances(obj)
        items = [descriptor(board,i["uuid"]) for i in obj["items"]]
        cat = classify([item[:3] for item in items],required)
        coords = [f'{i["pos"]["x"]},{i["pos"]["y"]}' for i in obj["items"]]
        yield dict(mode=mode,type=obj["type"],category=cat,
                   state="retained" if old and new else "added" if new else "removed",
                   required_mm=required,before_mm=drc_distances(old)[1] if old else "",
                   after_mm=actual if new else "",object_uuids="|".join(key[1]),
                   objects="|".join(label_for(board,i["uuid"]) for i in obj["items"]),
                   nets="|".join(item[2] for item in items),
                   layers="|".join(item[3] for item in items),
                   locations_mm="|".join(coords))


def component_groups(board):
    by_net = defaultdict(list)
    for p in board.by_id.values():
        if isinstance(p,pcb.PAD) and p.GetNumber() and p.GetNetname():
            by_net[p.GetNetname()].append(p)
    out = {}
    for net, pads in sorted(by_net.items()):
        groups = defaultdict(list)
        for pad in pads:
            groups[board.component(pad)].append(uid(pad))
        out[net] = [sorted(g) for g in sorted(groups.values(),key=lambda g:(-len(g),min(g)))]
    return out


class CopperPaths:
    def __init__(self, board):
        self.board = board
        self.by_net_layer = defaultdict(list)
        for ident,net,_,z,shape,_ in board.obstacles:
            if net:
                self.by_net_layer[net,z].append((ident,shape))
        for zone in board.board.Zones():
            if zone.GetIsRuleArea() or not zone.IsFilled():
                continue
            for z,layer in enumerate(LAYERS):
                if zone.IsOnLayer(layer):
                    region = polygons(zone.GetFilledPolysList(layer))
                    group = list(region.geoms) if hasattr(region,"geoms") else [region]
                    self.by_net_layer[zone.GetNetname(),z].extend(
                        (f"{uid(zone)}/{i}",shape) for i,shape in enumerate(group) if not shape.is_empty)
        self.cache = {}

    def neighbours(self, net):
        if net in self.cache:
            return self.cache[net]
        links = defaultdict(list)
        via_layers = defaultdict(list)
        for z in range(4):
            nodes = self.by_net_layer[net,z]
            ids, shapes = ([item[i] for item in nodes] for i in (0,1))
            if not shapes:
                continue
            tree = STRtree(shapes)
            i,j = tree.query(shapes,predicate="intersects")
            for a,b in zip(i,j):
                if a < b:
                    left,right = (ids[a],z),(ids[b],z)
                    links[left].append((right,0))
                    links[right].append((left,0))
            for ident in ids:
                item = self.board.by_id.get(ident)
                if isinstance(item,pcb.PCB_VIA) or isinstance(item,pcb.PAD) and item.HasHole():
                    via_layers[ident].append(z)
        for ident,layers in via_layers.items():
            is_via = isinstance(self.board.by_id[ident],pcb.PCB_VIA)
            for z in layers:
                for k in layers:
                    if z != k:
                        links[ident,z].append(((ident,k),int(is_via)))
        self.cache[net] = links
        return links

    def count_vias(self, net, left, right):
        a = [(uid(p),z) for p in left for z in range(4) if (uid(p),z) in self.board.shapes]
        finish = {(uid(p),z) for p in right for z in range(4) if (uid(p),z) in self.board.shapes}
        links = self.neighbours(net)
        score = {key: 0 for key in a}
        wait = deque(a)
        while wait:
            at = wait.popleft()
            distance = score[at]
            if at in finish:
                return distance
            for to, cost in links[at]:
                total = distance + cost
                if total < score.get(to,math.inf):
                    score[to] = total
                    if cost:
                        wait.append(to)
                    else:
                        wait.appendleft(to)
        return ""


def pairs(board_before, board_after, paths, lines):
    for label,left,right in lines:
        a,b = board_after.pads(left),board_after.pads(right)
        net = a[0].GetNetname()
        if {p.GetNetname() for p in a+b} != {net}:
            raise ValueError((label,left,right,[p.GetNetname() for p in a+b]))
        closed = board_after.connected(a,b)
        old = board_before.connected(board_before.pads(left),board_before.pads(right))
        yield dict(check=label,source=left,target=right,pin=right.split(".")[1],
                   net=net,before_copper=old,after_copper=closed,
                   minimum_layer_change_vias=paths.count_vias(net,a,b) if closed else "")


def external_gap(board,number):
    q = f"Q{number}"
    collector = uid(board.pads(q+".3")[0])
    internal = {uid(board.pads(q+"."+pin)[0]) for pin in ("1","2")}
    net = board.by_id[collector].GetNetname()
    closest = (math.inf,"","","")
    for z,layer in enumerate(LAYERS):
        sources = [(ident,shape) for ident,other,_,side,shape,_ in board.obstacles
                   if side==z and net==other]
        if not sources:
            continue
        targets = [(ident,shape) for ident,other,_,side,shape,_ in board.obstacles
                   if side==z and net!=other]
        for omit in (False,True):
            nearby = [(ident,shape) for ident,shape in targets if not omit or ident not in internal]
            shapes = [shape for _,shape in nearby]
            tree = STRtree(shapes)
            for ident,shape in sources:
                if (ident==collector) != omit:
                    continue
                indices,d = tree.query_nearest(shape,return_distance=True,all_matches=False)
                if len(d) and d[0] < closest[0]:
                    closest = (float(d[0]),label_for(board,ident),
                               label_for(board,nearby[int(indices[0])][0]),
                               board.board.GetLayerName(layer))
    return closest


def object_diff(before, after):
    object_info = {}
    for name,b in (("before",before),("after",after)):
        rows = {}
        for ident,item in b.by_id.items():
            if isinstance(item, pcb.ZONE):
                continue
            item_kind = "via" if isinstance(item,pcb.PCB_VIA) else "track" if isinstance(
                item,pcb.PCB_TRACK) else "pad"
            rows[ident] = dict(kind=item_kind,net=item.GetNetname(),pos=xy(item.GetPosition()),
                               layer=item.GetLayerName(),ref=descriptor(b,ident)[0])
            if item_kind=="track":
                rows[ident].update(end=xy(item.GetEnd()),width_mm=pcb.ToMM(item.GetWidth()))
            if item_kind=="via":
                rows[ident].update(width_mm=pcb.ToMM(item.GetWidth(pcb.F_Cu)),drill_mm=pcb.ToMM(item.GetDrillValue()))
            if item_kind=="pad":
                rows[ident].update(size=xy(item.GetSize()),drill=xy(item.GetDrillSize()),
                                   pin=item.GetNumber(),layers=list(item.GetLayerSet().Seq()))
        object_info[name] = rows

    old,new = object_info.values()
    added = {i:new[i] for i in sorted(new.keys()-old.keys())}
    removed = {i:old[i] for i in sorted(old.keys()-new.keys())}
    modified = {i:dict(before=old[i],after=new[i]) for i in sorted(old.keys()&new.keys())
                if old[i]!=new[i]}
    footprints = {ref: [dict(xy_mm=xy(f.GetPosition()),angle=f.GetOrientationDegrees(),
                             layer=f.GetLayerName(),package=f.GetFPIDAsString(),dnp=f.IsDNP())
                        for f in (before.refs[ref],after.refs[ref])]
                  for ref in sorted(before.refs.keys() & after.refs.keys())}
    return dict(added=added,removed=removed,modified=modified,
                footprints={r:v for r,v in footprints.items() if v[0]!=v[1]})


def find_obstacles(board, item):
    net = item.GetNetname()
    ident = uid(item)
    point = xy(item.GetPosition())
    result = {}
    x,y = point
    nearby = box(x-9,y-9,x+9,y+9)
    for other,other_net,minimum,z,shape,_ in board.obstacles:
        own = board.shapes.get((ident,z))
        if own is None or net == other_net or not nearby.intersects(shape):
            continue
        distance = own.distance(shape)
        clearance = max(gap(net),minimum)
        if distance >= clearance+.85:
            continue
        previous = result.get(other)
        if previous is None or distance < previous[0]:
            result[other] = (distance,clearance,label_for(board,other),
                             xy(board.by_id[other].GetPosition()),board.board.GetLayerName(LAYERS[z]))
    return sorted(result.values(),key=lambda row:(row[0]-row[1],row[2]))[:4]


def checks(root):
    evidence = root/"evidence"
    baseline = evidence/"before"
    result = evidence/"after"
    before = BoardRouter(BASE / f"{BASE_STEM}.kicad_pcb")
    final = root/"eda"/f"{STEM}.kicad_pcb"
    after = BoardRouter(final)
    for b in (before,after):
        for z in b.board.Zones():
            b.by_id[uid(z)] = z
    assert set(before.refs) - REMOVED_MOUNTS == set(after.refs)
    assert before.board.GetCopperLayerCount() == after.board.GetCopperLayerCount() == 4
    assert (BASE/f"{BASE_STEM}.kicad_dru").read_bytes() == (final.parent/f"{STEM}.kicad_dru").read_bytes()
    a,b = (read_json(f/"DRC.json") for f in (baseline,result))
    aa,bb = (read_json(f/"DRC-all-tracks.json") for f in (baseline,result))
    qa,qb = (metrics(report,read_json(f/"ERC.json")) for f,report in ((baseline,a),(result,b)))
    assert (qa["clearance"],qa["unconnected"],qa["parity"]) == (122,325,0), qa
    baseline_pins,new_pins = (schematic_pins(f/"netlist.xml") for f in (baseline,result))
    assert baseline_pins == new_pins
    pin_map = lambda brd: {i:descriptor(brd,i)[:3] for i,p in brd.by_id.items() if isinstance(p,pcb.PAD)}
    assert {i:v for i,v in pin_map(before).items() if v[0] not in REMOVED_MOUNTS} == pin_map(after)
    assert all(qb[k] == 0 for k in ("parity","erc_errors","erc_warnings")),qb
    new_drcs = {drc_key(v) for v in bb["violations"]} - {drc_key(v) for v in aa["violations"]}

    paths = CopperPaths(after)
    comparison = [*drc_compare(before,after,a,b,"standard"),
                  *drc_compare(before,after,aa,bb,"all_tracks")]
    write_csv(root/"DRC_BEFORE_AFTER.csv",list(comparison[0]),comparison)
    dcount = lambda state: Counter(r["category"] for r in comparison
        if r["mode"]=="standard" and r["state"]!=state)
    before_types,after_types = dcount("added"),dcount("removed")
    counts = dict(before=qa,after=qb,before_categories=before_types,after_categories=after_types,
                  before_all_track_violations=len(aa["violations"]),after_all_track_violations=len(bb["violations"]),
                  added_all_track_violations=len(new_drcs))

    channels = []
    for number in range(1,31):
        delta = [r for r in comparison if r["mode"]=="all_tracks" and r["state"]=="added"
                 and f"Q{number}." in r["objects"]]
        dist,left,right,layer = external_gap(after,number)
        rows = list(pairs(before,after,paths,channel_pairs(number,after)))
        for row in rows:
            transistor_pin = {"drive":1,"base_feed":1,"base_pulldown":1,
                              "return_local":2,"return_driver":2,"cathode_socket":3}
            row.update(channel=f"Q{number}",transistor_pin=transistor_pin[row["check"]],
                       group=(number-1)//10+1,
                       channel_complete=all(x["after_copper"] for x in rows),
                       minimum_external_hv_gap_mm=round(dist,6),nearest_hv_object=left,
                       nearest_other_object=right,nearest_layer=layer,new_drc=len(delta))
        channels.extend(rows)
    write_csv(root/"CATHODE_30_CHANNEL_AUDIT.csv",list(channels[0]),channels)
    write_csv(root/"GROUP_1_ROUTING_AUDIT.csv",list(channels[0]),channels[:60])
    done = [f"Q{i}" for i in range(1,31)
            if channels[(i-1)*6]["channel_complete"]]
    q2_count = sum(r["after_copper"] for r in channels[6:12])
    assert q2_count==6 and "Q1" in done

    protection = []
    for section,defs in (("OVP/FB/SNUB",PROTECTION),("J6",STOP)):
        for row in pairs(before,after,paths,defs):
            protection.append(dict(section=section,**row))
    write_csv(root/"PROTECTION_NET_CONNECTIVITY.csv",list(protection[0]),protection)
    stop = sum(r["after_copper"] for r in protection if r["section"]=="J6")
    protect = sum(r["after_copper"] for r in protection if r["section"]!="J6")

    reg = []
    for ref in ("U20","U21","U22","U23"):
        for pad in sorted(after.refs[ref].Pads(),key=lambda p:int(p.GetNumber())):
            if pad.GetNumber() not in REGISTER_PINS and pad.GetNetname()!=REGISTER_OUTPUT.get(ref):
                continue
            slot = after.component(pad)
            reg.append(dict(ref=ref,pin=pad.GetNumber(),net=pad.GetNetname(),
                            connected_copper_pads=sorted(label_for(after,i) for i in slot
                                if isinstance(after.by_id.get(i),pcb.PAD))))
    write_json(evidence/"shift-register-control.json",reg)

    components = [component_groups(board) for board in (before,after)]
    prior,latest = [{p:set(group) for net,groups in cs.items() for group in groups for p in group}
                    for cs in components]
    assert prior.keys() == latest.keys()
    losses = sorted(p for p in prior if not prior[p] <= latest[p])
    write_json(evidence/"inherited-pad-membership-losses.json",
               [{"pad":label_for(before,p),"lost":[label_for(before,i) for i in sorted(prior[p]-latest[p])]}
                for p in losses])
    write_json(evidence/"copper-components.json",
               {state:{n:[[dict(uuid=i,pad=label_for(brd,i)) for i in group] for group in groups]
                       for n,groups in cs.items()}
                for state,brd,cs in zip(("before","after"),(before,after),components)})

    isolation = sum(len(latest[uid(p)])==1 for n in range(3,31) for p in after.refs[f"Q{n}"].Pads())
    write_json(evidence/"power-copper-components.json",
               {n:{state:[{ "pad_count":len(g), "pads":[label_for(brd,i) for i in g]}
                          for g in cs.get(n,[])]
                   for state,brd,cs in zip(("before","after"),(before,after),components)}
                for n in ("GND","3V3","5V_RAW","5V_FUSED","5V_PROT","5V_HV","HV_BUS")})
    opens = []
    for report,board in ((a,before),(b,after)):
        opens.append(Counter(descriptor(board,v["items"][0]["uuid"])[2]
                             for v in report["unconnected_items"]))
    assert sum(opens[0].values())==qa["unconnected"] and sum(opens[1].values())==qb["unconnected"]
    rows = [dict(net=n,before=opens[0][n],after=opens[1][n],
                 change=opens[1][n]-opens[0][n],copper_pad_groups_before=len(components[0].get(n,[])),
                 copper_pad_groups_after=len(components[1].get(n,[])))
            for n in sorted(opens[0].keys() | opens[1].keys())]
    write_csv(root/"UNCONNECTED_NETS.csv",list(rows[0]),rows)

    events = defaultdict(list)
    for path in sorted(evidence.glob("routing-*.json")):
        for event in read_json(path):
            ends = frozenset((event["left"][0][0],event["right"][0][0]))
            events[(event["net"],ends)].append((path.stem,event))
    blocked = []
    for v in b["unconnected_items"]:
        i,j = [item["uuid"] for item in v["items"]]
        net = descriptor(after,i)[2]
        trials = events.get((net,frozenset((i,j))),[])
        trials = trials or [(name,event) for (n,_),es in events.items() if n==net
                            for name,event in es if not event["committed"]][:8]
        diagnostics = [{"stage":name,"label":e["label"],"attempts":e["attempts"]}
                       for name,e in trials if not e["committed"]]
        blockers = {label_for(after,k): find_obstacles(after,after.by_id[k])
                    for k in (i,j) if k in after.by_id}
        blocked.append(dict(net=net,left=label_for(after,i),right=label_for(after,j),
                            left_uuid=i,right_uuid=j,left_mm=list(v["items"][0]["pos"].values()),
                            right_mm=list(v["items"][1]["pos"].values()),
                            candidates=json.dumps(diagnostics,ensure_ascii=False,separators=(",",":")),
                            nearby_foreign_copper=json.dumps(blockers,ensure_ascii=False,separators=(",",":"))))
    write_csv(root/"BLOCKED_ROUTES.csv",list(blocked[0]),blocked)

    changes = object_diff(before,after)
    assert not MECHANICAL.intersection(changes["footprints"])
    assert not any(ref.startswith("MH") for ref in changes["footprints"])
    assert all(after.refs[r].IsDNP() for r in ("R40","U11"))
    assert all(before.refs[f"Q{n}"].GetFPIDAsString() == after.refs[f"Q{n}"].GetFPIDAsString()
               for n in range(1,31))
    edges = lambda brd: sorted((xy(i.GetStart()),xy(i.GetEnd())) for i in brd.board.GetDrawings()
                               if i.GetLayer()==pcb.Edge_Cuts)
    assert edges(before)==edges(after)
    changes.update(board_outline_mm=edges(after),immutable_pad_net_assignments=len(pin_map(after)),
                   removed_socket_mount_references=sorted(REMOVED_MOUNTS))
    write_json(evidence/"object-and-net-diff.json",changes)
    via,track = (sum(record["kind"]==kind for record in changes["added"].values())
                 for kind in ("via","track"))
    external = sum(after_types[k] for k in ("switch_external","hv_other_same_package",
                                           "hv_interface_mcu","hv_lv_external","hv_internal_external"))
    gates = dict(G1="PASS",G2="PASS" if all(f"Q{n}" in done for n in (3,4,5)) else "BLOCKED",
                 G3="PASS" if all(f"Q{n}" in done for n in range(1,11)) else "BLOCKED",
                 G4="PASS" if len(done)==30 else "BLOCKED",
                 G5="PASS" if stop==49 and protect==len(PROTECTION) else "BLOCKED",
                 G6="PASS" if external==qb["unconnected"]==qb["drc_other"]==len(new_drcs)==len(losses)==0 else "BLOCKED")
    write_json(root/"ROUTING_GATE_RESULTS.json",
               dict(gates=gates,metrics=counts,complete_channels=done,q2=f"{q2_count}/6",
                    j6=f"{stop}/49",other_protection=f"{protect}/{len(PROTECTION)}",
                    Q2_TERMINALS=f"{q2_count}/6",J6_TERMINALS=f"{stop}/49",
                    CATHODE_CHANNELS_CONNECTED=f"{len(done)}/30",
                    remaining_register_control_opens={n:opens[1][n] for n in (
                        "HC_CLEAR_N","HC_OE_N","SR_CLK_BUS","SR_LATCH_BUS","SER0","SER1","SER2","SER3")
                        if opens[1][n]},
                    isolated_q3_q30_pads=isolation,hv_external=external,
                    new_tracks=track,new_vias=via,prior_pad_group_regressions=len(losses),
                    final_board_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
                    inherited_rules_sha256=hashlib.sha256((final.parent/f"{STEM}.kicad_dru").read_bytes()).hexdigest(),
                    measured_switch_repetitive_peak="UNKNOWN", P01_LAYOUT="HOLD",
                    CATHODE_ROUTING="PASS" if gates["G4"]=="PASS" else "PARTIAL",
                    PROTECTION_NET_CONNECTIVITY="PASS" if gates["G5"]=="PASS" else "PARTIAL",
                    HV_EXTERNAL_CLEARANCE="PASS" if external==0 else "PARTIAL" if external<24 else "BLOCKED",
                    FULL_BOARD_ROUTING="PASS" if all(v=="PASS" for v in gates.values()) else "PARTIAL",
                    EVT_RELEASE="HOLD",MANUFACTURING_RELEASE="HOLD",HV_POWER_ON="PROHIBITED"))
    print(json.dumps(dict(gates=gates,channels=done,stop=stop,protection=protect,
                          isolation=isolation,external=external,counts=counts,
                          tracks=track,vias=via),ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=HERE)
    parser.add_argument("--skip-native",action="store_true")
    opts = parser.parse_args()
    root = opts.out.resolve()
    if not opts.skip_native:
        assert subprocess.check_output([CLI,"version"],encoding="utf-8").strip()=="10.0.8"
        evidence = root/"evidence"
        records = []
        native(evidence/"before",BASE/BASE_STEM,records)
        native(evidence/"after",root/"eda"/STEM,records)
        write_json(evidence/"native_commands.json",records)
    checks(root)


if __name__ == "__main__":
    main()
