"""Move existing low-voltage blanking parts into routable pockets."""
import pcbnew as pcb
from placement import Placement
from route_r14_1 import xy

TARGETS = {"Q31":(100.75,75.75,0,0), "R25":(102.0,76.5,90,0), "U15":(104.5,68.0,0,0)}


def move(board):
    from route import box

    placer = Placement.__new__(Placement)
    placer.courtyards = {pcb.F_Cu:[],pcb.B_Cu:[]}
    placer.copper = {pcb.F_Cu:[],pcb.B_Cu:[]}
    placer.holes = []
    for fp in board.GetFootprints():
        if fp.GetReference() not in TARGETS:
            placer.add(fp)
    for item in board.GetTracks():
        sides = placer.copper if isinstance(item,pcb.PCB_VIA) else (item.GetLayer(),)
        for side in sides:
            if side in placer.copper:
                placer.copper[side].append((item.GetNetname(),box(item)))
    prior = {}
    for ref,target in TARGETS.items():
        fp = board.FindFootprintByReference(ref)
        landings = {p.GetNumber():xy(p.GetPosition()) for p in fp.Pads()}
        placed = placer.choose(fp,target)
        fp.Reference().SetLayer(pcb.F_Fab if fp.GetLayer()==pcb.F_Cu else pcb.B_Fab)
        prior[ref] = {"old":landings,"placed":placed}
    return prior
