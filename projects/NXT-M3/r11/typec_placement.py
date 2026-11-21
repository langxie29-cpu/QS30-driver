"""Find nearby Type-C candidates that stay clear of retained tracks and existing footprints."""
import math

import numpy as np
import pcbnew as pcb

import route


def clearance(obstacles, rects, candidates, margin):
    if not obstacles or not rects:
        return np.ones(len(candidates),dtype=np.bool_)
    out = np.ones(len(candidates),dtype=np.bool_)
    obstacles = np.asarray(obstacles)
    filters = np.asarray(rects)
    cutoff = (min(candidates[:,0])+min(filters[:,0])-margin,
              min(candidates[:,1])+min(filters[:,1])-margin,
              max(candidates[:,0])+max(filters[:,2])+margin,
              max(candidates[:,1])+max(filters[:,3])+margin)
    l,t,r,b = obstacles.T
    large = (l<cutoff[2]) & (r>cutoff[0]) & (t<cutoff[3]) & (b>cutoff[1])
    l,t,r,b = obstacles[large].T
    for lo,top,hi,bottom in filters:
        n = np.flatnonzero(out)
        if not len(n):
            break
        xs,ys = candidates[n].T
        occupied = ((xs[:,None]+lo-margin<r) & (xs[:,None]+hi+margin>l) &
                    (ys[:,None]+top-margin<b) & (ys[:,None]+bottom+margin>t)).any(axis=1)
        out[n[occupied]] = False
    return out


def courtyard(fp):
    poly = fp.GetCourtyard(fp.GetLayer()).BBox()
    if poly.GetWidth()<=0:
        return None
    result = tuple(pcb.ToMM(value) for value in
                   (poly.GetLeft(),poly.GetTop(),poly.GetRight(),poly.GetBottom()))
    if fp.GetReference()=="U3":
        # Printed mechanical courtyard includes a larger RF reservation to its west.
        # Use the extents reported by native DRC in any marginal case.
        return (50,65.5,70.2,84.5)
    return result


class Placement:
    def __init__(self,board):
        self.copper = {pcb.F_Cu:[],pcb.B_Cu:[]}
        self.courtyards = {pcb.F_Cu:[],pcb.B_Cu:[]}
        for old in board.GetFootprints():
            self.add(old)
        for track in board.GetTracks():
            sides = (pcb.F_Cu,pcb.B_Cu) if isinstance(track,pcb.PCB_VIA) else (track.GetLayer(),)
            for side in sides:
                self.copper[side].append(route.box(track))

    def add(self,fp):
        if bounds := courtyard(fp):
            self.courtyards[fp.GetLayer()].append(bounds)
        for pad in fp.Pads():
            for side in self.copper:
                if pad.IsOnLayer(side):
                    self.copper[side].append(route.box(pad))

    def choose(self,fp,anchor):
        ref = fp.GetReference()
        x,y,preferred_angle = anchor
        if ref=="J1":
            candidates = [(x,52.825) for x in np.arange(63.5,128.1,.25)]
        else:
            candidates = [(x,y) for x in np.arange(61.5,119.51,.5) for y in np.arange(53.5,82.01,.5)]
        trials = sorted(candidates,key=lambda pos:math.dist(pos,(x,y)))
        trials = np.asarray(trials)
        options = []
        allowed = (pcb.F_Cu,) if ref=="J1" else (pcb.F_Cu,pcb.B_Cu)
        for side in allowed:
            if fp.GetLayer()!=side:
                fp.Flip(route.vec(0,0),False)
            for angle in ((180,) if ref=="J1" else (preferred_angle,preferred_angle+90)):
                fp.SetPosition(route.vec(0,0))
                fp.SetOrientationDegrees(angle)
                body = courtyard(fp)
                good = np.ones(len(trials),dtype=np.bool_)
                if body:
                    good &= clearance(self.courtyards[side],[body],trials,.10)
                    if ref=="J1":
                        # Protect the left mounting hardware and OLED insertion reservation.
                        good &= (trials[:,0]>63.7)&((trials[:,0]<94) | (trials[:,0]>97))
                    else:
                        good &= (trials[:,1]+body[1]>=50.4)
                index = np.flatnonzero(good)
                for surface in self.copper:
                    pads = [route.box(pad) for pad in fp.Pads() if pad.IsOnLayer(surface)]
                    filtered = clearance(self.copper[surface],pads,trials[index],.245)
                    index=index[filtered]
                    if not len(index):
                        break
                if len(index):
                    point = tuple(map(float,trials[index[0]]))
                    penalty = math.dist(point,(x,y)) + (2.5 if side==pcb.B_Cu else 0)
                    options.append((penalty,point,side,angle))
        if not options:
            raise ValueError(f"No screened placement found for {ref}")
        _,xy,side,angle = min(options,key=lambda row:row[0])
        if fp.GetLayer()!=side:
            fp.Flip(route.vec(0,0),False)
        fp.SetPosition(route.vec(*xy))
        fp.SetOrientationDegrees(angle)
        self.add(fp)
        return xy,side,angle
