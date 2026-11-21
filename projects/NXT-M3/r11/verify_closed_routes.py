"""Verify that the accepted routes physically connect the named terminals."""
from collections import Counter
import json
import math
from pathlib import Path

import pcbnew as pcb

from close_r11_blockers import open_nets
from route import EDA,box,pos

HERE=Path(__file__).resolve().parent
TARGET=HERE/"evidence/blocker_closure"
LAYERS=(pcb.F_Cu,pcb.B_Cu,pcb.In1_Cu,pcb.In2_Cu)


def norm(point):
    return pcb.ToMM(point.x),pcb.ToMM(point.y)


def segment_distance(point,ends):
    (sx,sy),(tx,ty)=ends
    u,v=tx-sx,ty-sy
    length_sq=u*u+v*v
    coefficient=min(1,max(0,((point[0]-sx)*u+(point[1]-sy)*v)/length_sq)) if length_sq else 0
    return math.dist(point,(sx+coefficient*u,sy+coefficient*v))


def same_segment(a,b):
    return (min(segment_distance(x,b) for x in a)<.000005 or
            min(segment_distance(y,a) for y in b)<.000005)


def components(board,net):
    nodes=[]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname()==net:
                surfaces={layer for layer in LAYERS if pad.IsOnLayer(layer)}
                nodes.append(("pad",(fp.GetReference(),pad.GetNumber()),surfaces,box(pad)))
    for track in board.GetTracks():
        if track.GetNetname()!=net:
            continue
        if isinstance(track,pcb.PCB_VIA):
            nodes.append(("via",None,set(LAYERS),pos(track)))
        else:
            nodes.append(("line",None,{track.GetLayer()},(norm(track.GetStart()),norm(track.GetEnd()))))
    rooted=list(range(len(nodes)))
    def find(i):
        while rooted[i]!=i:
            i=rooted[i]
        return i
    for i,(kind,name,sides,copper) in enumerate(nodes):
        if kind=="pad":
            continue
        for j,(other,_,layers,shape) in enumerate(nodes):
            if i==j or not sides&layers:
                continue
            if kind=="via":
                touch=(segment_distance(copper,shape)<.000005 if other=="line" else
                       (math.dist(copper,shape)<.000005 if other=="via" else
                        shape[0]<=copper[0]<=shape[2] and shape[1]<=copper[1]<=shape[3]))
            elif other=="line":
                touch=same_segment(copper,shape)
            elif other=="pad":
                touch=any(shape[0]<=x<=shape[2] and shape[1]<=y<=shape[3] for x,y in copper)
            else:
                continue
            if touch:
                rooted[find(i)]=find(j)
    return {node[1]:find(index) for index,node in enumerate(nodes) if node[0]=="pad"}


def four_layer_cc1():
    board = pcb.LoadBoard(str(TARGET/"four_layer_cc1_preview.kicad_pcb"))
    module = next(fp for fp in board.GetFootprints() if fp.GetReference() == "U3")
    keepout, = [zone for zone in module.Zones() if zone.GetIsRuleArea()]
    layers = set(keepout.GetLayerSet().Seq())
    joints = components(board, "USBC_CC1")
    terminals = [("J1", "A5"), ("U26", "1"), ("U26", "2"), ("D5", "1")]
    assert board.GetCopperLayerCount() == 4 and layers == set(LAYERS)
    assert len({joints[terminal] for terminal in terminals}) == 1, joints
    return {"continuous_terminals":[".".join(part) for part in terminals],
            "antenna_keepout_layers":[board.GetLayerName(layer) for layer in LAYERS]}


def main():
    board=pcb.LoadBoard(str(EDA))
    connect={}
    for net,links in {
        "5V_RAW":[(("J1","A9"),("F1","1")),(("J1","B9"),("F1","1"))],
        "5V_FUSED":[(("F1","2"),("R3","1")),(("F1","2"),("R1","1"))],
        "ANODE_2":[(("V2","1"),("R305","2"))],
        "ANODE_3":[(("V3","1"),("R307","2"))],
        "USBC_CC2":[(("J1","B5"),("U26","4"))],
    }.items():
        result=components(board,net)
        connect[net]=[{"from":".".join(first),"to":".".join(second),
                       "continuous":result[first]==result[second]} for first,second in links]
    assert all(x["continuous"] for group in connect.values() for x in group),connect
    report=json.loads((TARGET/"final/DRC.json").read_text(encoding="utf-8-sig"))
    opens = open_nets(report)
    assert opens.total() == len(report["unconnected_items"]), "Unlabeled native opens"
    before = json.loads((TARGET/"ground_return_before.json").read_text(encoding="utf-8-sig"))
    before_ground = open_nets(before)["GND"]
    assert opens["GND"] == before_ground - 2
    result={"coordinate_connectivity":connect,"copper_layers":board.GetCopperLayerCount(),
            "gnd_open_before_pour_extension":before_ground,"gnd_open_after_pour_extension":opens["GND"],
            "unique_unconnected_nets":len(opens),"opens_by_net":dict(sorted(opens.items())),
            "four_layer_cc1_preview":four_layer_cc1(),
            "unconnected":len(report["unconnected_items"]),"native_rule_types":dict(Counter(
                row["type"] for row in report["violations"]))}
    (TARGET/"final/route_connectivity.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
