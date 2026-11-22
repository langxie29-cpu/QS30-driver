"""Place isolated array packages where all three copper exits fit."""
from collections import namedtuple
import math

import numpy as np
import pcbnew as pcb
from shapely import box, intersects_xy
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from route_board import LAYERS, MARGIN, common_components, copper, gap, point, uid, xy

Pose = namedtuple("Pose", "x y angle parts screen score")


def compatible(a, b):
    return all(geom.distance(other) >= max(required, gap_other)
               for _,required,geom in a.screen
               for gap_other,other in b.parts)


def intersect(dst, xs, ys, geometry, mark):
    x0,y0,x1,y1 = geometry.bounds
    i,j = xs.searchsorted(x0),ys.searchsorted(y0)
    e,f = xs.searchsorted(x1,"right"),ys.searchsorted(y1,"right")
    covered = intersects_xy(geometry,xs[None,i:e],ys[j:f,None])
    if mark:
        dst[j:f,i:e] |= covered
    else:
        dst[j:f,i:e] &= ~covered


def pose_array(board, channels):
    transistors = [board.refs[f"Q{n}"] for n in channels]
    movable = {uid(p) for f in transistors for p in f.Pads()}
    assert all(len(board.component(board.by_id[i])) == 1 for i in movable)
    objects = [(net, required, geom) for ident,net,required,z,geom,_ in board.obstacles
               if ident not in movable and z == 1]
    tree = STRtree([item[2] for item in objects])

    def clear(screen):
        for net, required, geom in screen:
            x0,y0,x1,y1 = geom.bounds
            for i in tree.query(box(x0-3.23,y0-3.23,x1+3.23,y1+3.23)):
                other, other_gap, other_geom = objects[i]
                if net != other and other_geom.distance(geom) < max(required,other_gap)+MARGIN:
                    return False
        return True

    def poses(f):
        ox,oy = xy(f.GetPosition())
        orig = f.GetOrientation()
        offsets = [(i*.25,j*.25) for i in range(-13,14) for j in range(-11,12)]
        offsets.sort(key=lambda d: math.hypot(*d))
        candidates = []
        for angle in (0,180,90,270):
            f.SetOrientation(pcb.EDA_ANGLE(angle,pcb.DEGREES_T))
            for dx,dy in offsets:
                x,y = round(ox+dx,2),round(oy+dy,2)
                f.SetPosition(point(x,y))
                pads = {p.GetNumber():p for p in f.Pads()}
                shapes = {i:copper(p,pcb.B_Cu) for i,p in pads.items()}
                parts = tuple((gap(pads[i].GetNetname()),geom) for i,geom in shapes.items())
                screen = [(pads[i].GetNetname(),gap(pads[i].GetNetname()),geom)
                          for i,geom in shapes.items()]
                if not clear(screen):
                    continue
                launch = []
                for pin,rad,stub in (("1",.10,.23),("2",.10,.23),("3",.15,.23)):
                    px,py = xy(pads[pin].GetPosition())
                    nx,ny = (px-x),(py-y)
                    if angle in (0,180):
                        ny=0
                    else:
                        nx=0
                    nx,ny = nx/math.hypot(nx,ny),ny/math.hypot(nx,ny)
                    release = .56 if pin != "3" else .55
                    a = (px+nx*release,py+ny*release)
                    c = (a[0]+nx*stub,a[1]+ny*stub)
                    edge = LineString((a,c)).buffer(rad,quad_segs=12)
                    launch.append((pads[pin].GetNetname(),gap(pads[pin].GetNetname()),edge))
                if not clear(launch):
                    continue
                score = math.hypot(dx,dy) + (0 if angle==0 else .85)
                candidates.append(Pose(x,y,angle,parts, screen+launch,score))
                if len(candidates) >= 90:
                    break
            if len(candidates) >= 90:
                break
        f.SetPosition(point(ox,oy))
        f.SetOrientation(orig)
        return sorted(candidates,key=lambda p:p.score)

    candidates = {f.GetReference():poses(f) for f in transistors}
    print("PLACEMENT OPTIONS", {ref:len(v) for ref,v in candidates.items()},flush=True)

    fixed = board.obstacles
    board.obstacles = [o for o in fixed if o[0] not in movable]
    try:
        for f in transistors:
            ref = f.GetReference()
            options = candidates[ref]
            cathode = next(p for p in f.Pads() if p.GetNumber()=="3")
            net = cathode.GetNetname()
            socket = next(p for other in board.refs.values() if other.GetReference().startswith("V")
                          for p in other.Pads() if p.GetNetname()==net)
            step = .05
            xs,ys = board.grid([cathode],[socket],10,step)
            block,allow,_ = board.maps(net,.30,xs,ys,0)
            goal = board.anchors([socket],block,xs,ys,.30)
            connected = []
            for pose in options:
                local = block.copy()
                via = allow.copy()
                high = None
                for other,required,geom in pose.screen[:3]:
                    if other == net:
                        high = geom
                        intersect(via,xs,ys,geom.buffer(.308,quad_segs=10),False)
                        continue
                    intersect(local[1],xs,ys,geom.buffer(2.158,quad_segs=10),True)
                    intersect(via,xs,ys,geom.buffer(2.308,quad_segs=10),False)
                start_area = high.buffer(.105,quad_segs=10)
                x0,y0,x1,y1 = start_area.bounds
                i,j = xs.searchsorted(x0),ys.searchsorted(y0)
                e,k = xs.searchsorted(x1,"right"),ys.searchsorted(y1,"right")
                mask = intersects_xy(start_area,xs[None,i:e],ys[j:k,None]) & ~local[1,j:k,i:e]
                rows,cols = np.nonzero(mask)
                start = {(i+int(x),j+int(y),1) for y,x in zip(rows,cols)}
                if common_components(local[:2],via,start,goal):
                    connected.append(pose)
                if len(connected) >= 12:
                    break
            if connected:
                candidates[ref] = connected
            print("K CORRIDOR OPTIONS",ref,len(connected),flush=True)
    finally:
        board.obstacles = fixed

    def place(refs, selected):
        if not refs:
            return selected
        ref = min(refs,key=lambda r:len(refs[r]))
        for pose in refs[ref]:
            alternatives = {r:[p for p in options
                               if math.dist((p.x,p.y),(pose.x,pose.y)) > 6 or
                               compatible(p,pose) and compatible(pose,p)]
                            for r,options in refs.items() if r!=ref}
            if all(alternatives.values()):
                result = place(alternatives, {**selected,ref:pose})
                if result:
                    return result
        return None

    planned = place(candidates,{})
    if not planned:
        return None
    for ref, pose in planned.items():
        f = board.refs[ref]
        f.SetPosition(point(pose.x,pose.y))
        f.SetOrientation(pcb.EDA_ANGLE(pose.angle,pcb.DEGREES_T))
    return {ref:[pose.x,pose.y,pose.angle] for ref,pose in planned.items()}
