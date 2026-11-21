"""Audit and draw the R10 GZC13-F hand-wire reference on the R11 comments layer."""
import csv
import hashlib
import json
import math
from pathlib import Path

import pcbnew as pcb

from route import EDA,vec

HERE = Path(__file__).resolve().parent
REF = HERE/"socket_reference"
OUT = HERE/"evidence/typec"
ORIGIN = (50,50)
TAG = "GZC13-F R10 REFERENCE / NO DRILLS"


def draw_text(board, label, position, size=.8):
    item = pcb.PCB_TEXT(board)
    item.SetLayer(pcb.Cmts_User)
    item.SetText(label)
    item.SetPosition(vec(*position))
    item.SetTextSize(pcb.VECTOR2I(pcb.FromMM(size),pcb.FromMM(size)))
    item.SetTextThickness(pcb.FromMM(.12))
    board.Add(item)


def draw_circle(board,position,radius):
    item = pcb.PCB_SHAPE(board)
    item.SetLayer(pcb.Cmts_User)
    item.SetShape(pcb.SHAPE_T_CIRCLE)
    item.SetStart(vec(*position))
    item.SetEnd(vec(position[0]+radius,position[1]))
    item.SetWidth(pcb.FromMM(.10))
    board.Add(item)


def distance_to_box(position,box):
    bounds = [pcb.ToMM(n) for n in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom())]
    x,y = position
    dx=max(bounds[0]-x,0,x-bounds[2])
    dy=max(bounds[1]-y,0,y-bounds[3])
    return math.hypot(dx,dy)


def main():
    metadata = json.loads((REF/"socket-mechanics.json").read_text(encoding="utf-8-sig"))
    with (REF/"handwire-pads.csv").open(encoding="utf-8-sig",newline="") as f:
        pads = list(csv.DictReader(f))
    assert metadata["part"]=="GZC13-F" and len(pads)==33
    board = pcb.LoadBoard(str(EDA))
    if any(isinstance(item,pcb.PCB_TEXT) and item.GetText()==TAG for item in board.GetDrawings()):
        raise ValueError("The GZC13-F reference is already visible")
    assert all(board.FindNet(row["pcb_net"]) is not None for row in pads)
    footprints = list(board.GetFootprints())
    physical = [(f.GetReference(), p.GetNetname(), p.GetBoundingBox()) for f in footprints
                for p in f.Pads() if p.GetNetname()]
    tracks = [(item.GetNetname(), item.GetBoundingBox()) for item in board.GetTracks()]
    conflicts = []
    for name,point in metadata["pcb_holes_mm"].items():
        center = tuple(x+ref for x,ref in zip(point,ORIGIN))
        draw_circle(board,center,metadata["hardware_envelope_diameter_mm"]/2)
        draw_text(board,name +" REF",(center[0],center[1]+4.8))
        hits = [f"{ref}:{net}" for ref,net,box in physical if distance_to_box(center,box)<4.0]
        copper = sorted({net for net,box in tracks if distance_to_box(center,box)<4.0})
        conflicts.append({"reference":name,"xy_mm":center,"BBOX_pad_hits":sorted(set(hits)),"BBOX_track_net_hits":copper})
    for row in pads:
        point = (float(row["x_mm_from_pcb_left"])+ORIGIN[0],float(row["y_mm_from_pcb_top"])+ORIGIN[1])
        draw_circle(board,point,.55)
        draw_text(board,row["function"],(point[0],point[1]+1.4),.65)
    draw_text(board,TAG,(115,114.8))
    pcb.SaveBoard(str(EDA),board)
    evidence = {"source":"local R10 socket-preview working copy","reference":metadata["part"],
                "overlay_layer":"Cmts.User","unmeasured_socket_terminals":True,"handoffs":len(pads),
                "support_candidates":len(conflicts),"hardware_envelope_Box_intersections":conflicts,
                "source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in REF.glob("*")
                                 if f.suffix in {".json",".csv"}}}
    (OUT/"socket_projection.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
    print("Socket overlay: 33 handoff positions, 6 support candidates, no copper or drills.")


if __name__=="__main__":
    main()
