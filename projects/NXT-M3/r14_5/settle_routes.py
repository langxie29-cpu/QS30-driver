"""Recover inherited pad memberships and remove native dangling copper."""
import argparse
from collections import defaultdict
import math
from pathlib import Path
import subprocess

import pcbnew as pcb

from route_board import BASE, BASE_STEM, HERE, STEM, BoardRouter, point, uid, xy
from remote_display import ident
from verify_board import CLI, component_groups, label_for, read_json, write_json


def restore(path):
    baseline = BoardRouter(BASE / f"{BASE_STEM}.kicad_pcb")
    board = BoardRouter(path)
    groups = component_groups(baseline)
    unresolved = []
    for net, nets in groups.items():
        for component in nets:
            remaining = [board.by_id[i] for i in component]
            if len(remaining)<2:
                continue
            while remaining:
                by_group = defaultdict(list)
                for item in remaining:
                    by_group[board.component(item)].append(item)
                if len(by_group)<2:
                    break
                parts = sorted(by_group.values(), key=lambda g:(-len(g),uid(g[0])))
                main = parts[0]
                targets = [p for group in parts[1:] for p in group]
                candidates = sorted((math.dist(xy(a.GetPosition()),xy(b.GetPosition())),
                                     uid(a),uid(b),a,b) for a in main for b in targets)
                for _,i,j,a,b in candidates[:8]:
                    label = f"restore inherited {label_for(board,i)} -> {label_for(board,j)}"
                    if board.route(label,[a],[b],margin=11,limit=180000):
                        break
                else:
                    unresolved.append(dict(net=net, old_group=[label_for(board,uid(p))
                                                              for p in remaining]))
                    break
    board.save(path)
    return board.events, unresolved


def native(board_path, report):
    options = ["pcb","drc","--all-track-errors","--schematic-parity","--severity-all",
               "--refill-zones","--save-board","--format","json","-o",str(report),
               str(board_path)]
    subprocess.run([CLI,*options],cwd=HERE,check=True)
    return read_json(report)


def prune(path, report):
    result = []
    previous_ids = set()
    for cycle in range(16):
        drc = native(path,report)
        ids = {item["uuid"] for v in drc["violations"]
               if v["type"] in {"track_dangling","via_dangling"} for item in v["items"]}
        if not ids or ids == previous_ids:
            return result
        previous_ids = ids
        board = BoardRouter(path)
        state_before = component_groups(board)
        for ident in sorted(ids):
            item = board.by_id[ident]
            assert isinstance(item,pcb.PCB_TRACK)
            board.board.RemoveNative(item)
            board.sync()
            state_after = component_groups(board)
            # Existing copper can form a T-junction along a flagged segment.
            # Retain the object if deletion would split any pad component.
            if state_after != state_before:
                board.board.Add(item)
                board.sync()
                continue
            result.append(dict(cycle=cycle,uuid=uid(item),net=item.GetNetname(),
                               position_mm=xy(item.GetPosition()),type=type(item).__name__))
        board.save(path)
    native(path,report)
    return result


def boundary(path):
    raw = pcb.LoadBoard(str(path))
    raw.FindFootprintByReference("C45").SetPosition(point(171.25,65.0))
    b = BoardRouter(raw)
    for label,a,c in (
        ("gate bias decoupling","C45.1","U18.1"),
        ("gate bias return","C45.2","U18.4"),
        ("feedback upper stage","R83.2","R84.1"),
        ("OVP upper stage","R61.2","R62.1"),
        ("OVP capacitor sense","C35.1","U13.2"),
    ):
        short = label.startswith("gate bias")
        b.pair(label,a,c,margin=8 if short else 24,limit=200000)
    b.save(path)
    return b.events


def replace_same_layer_bridge(path):
    raw = pcb.LoadBoard(str(path))
    board = BoardRouter(raw)
    at = board.by_id.get("88c0beee-ba95-5c70-b088-2e447afbbc0e")
    if at is None:
        return []
    assert isinstance(at,pcb.PCB_VIA) and at.GetNetname() == "HC_OE_N"
    assert xy(at.GetPosition()) == (81.4,92.9)
    before = component_groups(board)
    track = pcb.PCB_TRACK(raw)
    track.SetLayer(pcb.B_Cu)
    track.SetStart(at.GetPosition())
    track.SetEnd(point(81.4,93.2))
    track.SetWidth(pcb.FromMM(.20))
    track.SetNet(at.GetNet())
    track.SetUuidDirect(ident("U20/13/same-layer-bridge"))
    raw.Add(track)
    raw.RemoveNative(at)
    board.record(track)
    board.sync()
    assert component_groups(board)==before
    board.save(path)
    return [dict(removed_via=uid(at),added_track=uid(track),net="HC_OE_N",
                 start_mm=[81.4,92.9],end_mm=[81.4,93.2])]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("restore","prune","boundary","polish"))
    p.add_argument("--out",type=Path,default=HERE)
    args = p.parse_args()
    root = args.out.resolve()
    evidence = root/"evidence"
    path = root/"eda"/f"{STEM}.kicad_pcb"
    if args.stage=="restore":
        events, unresolved = restore(path)
        write_json(evidence/"routing-restore.json",events)
        write_json(evidence/"inherited-membership-unresolved.json",unresolved)
    elif args.stage=="boundary":
        write_json(evidence/"routing-boundary.json",boundary(path))
    elif args.stage=="polish":
        write_json(evidence/"same-layer-bridge.json",replace_same_layer_bridge(path))
    else:
        write_json(evidence/"pruned-copper-final.json",prune(path,evidence/"post-prune-native.json"))


if __name__ == "__main__":
    main()
