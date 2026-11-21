"""Continue R11 Type-C connections from native DRC endpoints and validate each new path."""
from collections import Counter
import json

import pcbnew as pcb

import route
from typec_pcb import USBNETS, drc, OUT

NETS = (*USBNETS,"5V_RAW","FRONT_EN")


def tap(item, anchor, board):
    if isinstance(item,pcb.PAD):
        ref = item.GetParentFootprint().GetReference()
        return (ref,item,tuple(i for i,s in enumerate(route.LAYERS) if item.IsOnLayer(s)))
    marker = pcb.PAD(next(iter(board.GetFootprints())))
    marker.SetPosition(route.vec(anchor["x"],anchor["y"]))
    marker.SetSize(route.vec(.55,.55))
    layers = (0,1) if isinstance(item,pcb.PCB_VIA) else (route.LAYERS.index(item.GetLayer()),)
    return ("existing copper",marker,layers)


def main():
    start = drc("escape_before")
    board = pcb.LoadBoard(str(route.EDA))
    route.STEP,route.NX,route.NY = .125,1041,641
    draft = route.Draft(board)
    pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname()]
    tracks = list(board.GetTracks())
    items = {str(item.m_Uuid.AsString()):item for item in [*pads,*tracks]}
    for track in tracks:
        via = isinstance(track,pcb.PCB_VIA)
        layers = (0,1) if via else (route.LAYERS.index(track.GetLayer()),)
        draft.obstacles.append((track.GetNetname(),layers,route.box(track),"via" if via else "track"))
    requested = Counter()
    for gap in start["unconnected_items"]:
        a,b = gap["items"]
        if a["uuid"] not in items or b["uuid"] not in items:
            continue
        first,second = items[a["uuid"]],items[b["uuid"]]
        net = first.GetNetname()
        if net!=second.GetNetname() or net not in NETS:
            continue
        requested[net] += 1
        draft.route(net,tap(first,a["pos"],board),tap(second,b["pos"],board),240000)
    pcb.SaveBoard(str(route.EDA),board)
    trial = drc("escape_trial",fill=True)
    bad = {item["uuid"] for issue in trial["violations"] for item in issue["items"]}
    for row in list(draft.saved):
        if any(str(track.m_Uuid.AsString()) in bad for track in row[3]):
            for track in row[3]:
                board.Remove(track)
            draft.saved.remove(row)
    pcb.SaveBoard(str(route.EDA),board)
    last = drc("escape_final",fill=True)
    summary = {"attempted_by_net":dict(requested),"kept_paths":[row[0] for row in draft.saved],
               "before_open":len(start["unconnected_items"]),"after_open":len(last["unconnected_items"])}
    (OUT/"escape_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
