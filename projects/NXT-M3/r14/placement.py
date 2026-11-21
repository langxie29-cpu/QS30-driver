"""Screen nearby native pad and courtyard boxes before exact KiCad DRC."""
import math
import sys
from pathlib import Path

import numpy as np
import pcbnew as pcb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "r11"))
import route
from typec_placement import clearance, courtyard

SIDES = (pcb.F_Cu, pcb.B_Cu)


class Placement:
    def __init__(self, board, moving):
        self.courtyards = {side: [] for side in SIDES}
        self.holes = []
        self.copper = {side: [] for side in SIDES}
        for fp in board.GetFootprints():
            if fp.GetReference() not in moving:
                self.add(fp)
        for item in board.GetTracks():
            if item.GetNetname() == "BASE_00":
                continue
            sides = SIDES if isinstance(item, pcb.PCB_VIA) else (item.GetLayer(),)
            for side in sides:
                self.copper[side].append((item.GetNetname(), route.box(item)))

    def add(self, fp):
        body = courtyard(fp)
        if body:
            self.courtyards[fp.GetLayer()].append(body)
        for pad in fp.Pads():
            if pad.GetDrillSize().x:
                self.holes.append(route.box(pad))
            for side in SIDES:
                if pad.IsOnLayer(side):
                    self.copper[side].append((pad.GetNetname(), route.box(pad)))

    def choose(self, fp, anchor, move=False):
        x, y, angle, side = anchor
        if move:
            windows = (x-3, y-3, x+3, y+3)
            sides, angles = (side,), (angle, angle+90, angle-90)
        elif fp.GetReference() == "J6":
            windows = (61, 56.5, 78, 62)
            sides, angles = (0,), (180,)
        elif fp.GetReference() == "J5":
            windows = (57, 53.5, 99, 91)
            sides, angles = (0, 1), (0, 90, 180, 270)
        else:
            windows = (max(58,x-10), max(51.5,y-9), min(117,x+10), min(92,y+8))
            sides, angles = (side, 1-side), (angle, angle+90, angle+180, angle+270)
        points = sorted(((a, b) for a in np.arange(windows[0], windows[2]+.01, .25)
                         for b in np.arange(windows[1], windows[3]+.01, .25)),
                        key=lambda ab: math.dist(ab, (x, y)))
        trials = np.asarray(points)
        result = []
        fp.SetPosition(route.vec(0, 0))
        for candidate_side in sides:
            layer = SIDES[candidate_side]
            if layer != fp.GetLayer():
                fp.Flip(fp.GetPosition(), pcb.FLIP_DIRECTION_LEFT_RIGHT)
            for candidate_angle in angles:
                fp.SetOrientationDegrees(candidate_angle)
                body = courtyard(fp)
                good = np.ones(len(trials), dtype=np.bool_)
                if body:
                    good &= clearance(self.courtyards[layer], [body], trials, .08)
                    good &= clearance(self.holes, [body], trials, .08)
                    good &= (trials[:,0]+body[0] >= 50.3) & (trials[:,1]+body[1] >= 50.25)
                    good &= (trials[:,0]+body[2] <= 179.7) & (trials[:,1]+body[3] <= 129.7)
                hits = np.flatnonzero(good)
                for pad in fp.Pads():
                    name = pad.GetNetname()
                    size = route.box(pad)
                    gap = route.gap(name)
                    for surface in SIDES:
                        if not pad.IsOnLayer(surface) or not len(hits):
                            continue
                        other = self.copper[surface]
                        lv = [box for net, box in other if net!=name and route.gap(net)<=.2]
                        hv = [box for net, box in other if net!=name and .2<route.gap(net)<=2]
                        sw = [box for net, box in other if net!=name and route.gap(net)>2]
                        for bounds, margin in ((lv, .35), (hv, 2.05), (sw, 3.25)):
                            if not len(hits):
                                break
                            hits = hits[clearance(bounds, [size], trials[hits], max(gap+.05, margin))]
                    if not len(hits):
                        break
                if len(hits):
                    xy = tuple(map(float, trials[hits[0]]))
                    score = math.dist(xy, (x,y)) + (1.2 if candidate_side != side else 0)
                    result.append((score, xy, candidate_side, candidate_angle))
        if not result:
            raise ValueError(f"No screened local placement for {fp.GetReference()}")
        _, xy, chosen_side, chosen_angle = min(result)
        if fp.GetLayer() != SIDES[chosen_side]:
            fp.Flip(fp.GetPosition(), pcb.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetPosition(route.vec(*xy))
        fp.SetOrientationDegrees(chosen_angle)
        self.add(fp)
        return [*xy, chosen_angle % 360, chosen_side]
