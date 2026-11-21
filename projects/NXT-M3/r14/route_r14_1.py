"""Route scoped R14.1 ECO copper. All geometry is checked again by native KiCad."""
import heapq
import math
import os

import numpy as np
import pcbnew as pcb

LAYERS = (pcb.F_Cu, pcb.B_Cu, pcb.In1_Cu, pcb.In2_Cu)
STEP = float(os.environ.get('R14_1_GRID', '.125'))
ORIGIN = (50.0, 50.0)
NX, NY = round(130/STEP)+1, round(80/STEP)+1
WIDTH_05 = {"5V_RAW", "5V_FUSED", "5V_PROT", "5V_HV", "HV_ISOLATE_IN", "LV_SW"}
MOVES = ((1,0,10),(-1,0,10),(0,1,10),(0,-1,10),
         (1,1,14),(1,-1,14),(-1,1,14),(-1,-1,14))


def xy(v):
    return tuple(pcb.ToMM(q) for q in v)


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def grid(x, y):
    return round((x-ORIGIN[0])/STEP), round((y-ORIGIN[1])/STEP)


def mm(x, y):
    return ORIGIN[0]+x*STEP, ORIGIN[1]+y*STEP


def gap(net):
    if net in ("SW_HV", "SNUB"):
        return 3.2
    if net == "HV_BUS" or net.startswith(("K", "ANODE_", "ALIM_", "BLEED_", "HV_FB_", "HV_OVP_S_", "HV_RES_S_")):
        return 2
    return .2


def path(block, can_via, start, end, limit):
    target = set(end)
    if not start or not target:
        return []
    lo_x, lo_y, hi_x, hi_y = min(p[0] for p in end), min(p[1] for p in end), max(p[0] for p in end), max(p[1] for p in end)

    def estimate(x, y):
        a, b = max(lo_x-x, 0, x-hi_x), max(lo_y-y, 0, y-hi_y)
        return 10*max(a,b) + 4*min(a,b)

    queue = [(estimate(x,y), 0, x,y,z) for x,y,z in start]
    heapq.heapify(queue)
    cost = np.full((len(block), NY, NX), 2**30, dtype=np.int32)
    prev = {}
    for x,y,z in start:
        cost[z,y,x] = 0
    visited = 0
    while queue and visited < limit:
        _, d, x,y,z = heapq.heappop(queue)
        if d != cost[z,y,x]:
            continue
        key = (x,y,z)
        if key in target:
            result = [key]
            while key in prev:
                key = prev[key]
                result.append(key)
            return result[::-1]
        visited += 1
        for dx,dy,delta in MOVES:
            i,j = x+dx,y+dy
            if not (0 <= i < NX and 0 <= j < NY) or block[z,j,i]:
                continue
            if dx and dy and (block[z,j,x] or block[z,y,i]):
                continue
            n = d+delta
            if n < cost[z,j,i]:
                child = i,j,z
                cost[z,j,i] = n
                prev[child] = key
                heapq.heappush(queue,(n+estimate(i,j),n,*child))
        if can_via[y,x]:
            for other in range(len(block)):
                if other == z or block[other,y,x] or d+115 >= cost[other,y,x]:
                    continue
                child = x,y,other
                cost[other,y,x] = d+115
                prev[child] = key
                heapq.heappush(queue,(d+115+estimate(x,y),d+115,*child))
    return []


def pad_polygon(pad, layer):
    poly = pcb.SHAPE_POLY_SET()
    pad.TransformShapeToPolygon(poly, layer, 0, pcb.FromMM(.004), pcb.ERROR_OUTSIDE)
    for i in range(poly.OutlineCount()):
        outline = poly.COutline(i)
        yield [xy(outline.CPoint(j)) for j in range(outline.PointCount())]


class Raster:
    def __init__(self, board):
        self.board = board
        self.layers = LAYERS[:board.GetCopperLayerCount()]
        self.obstacles = []
        self.holes = []
        self.reserves = []
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                for z, layer in enumerate(self.layers):
                    if pad.IsOnLayer(layer):
                        for polygon in pad_polygon(pad, layer):
                            self.obstacles.append((pad.GetNetname(),(z,),polygon,0,"pad"))
                drill = max(xy(pad.GetDrillSize()))/2
                if drill:
                    self.holes.append(([xy(pad.GetPosition())], drill, fp.GetReference().startswith("MH")))
        for item in board.GetTracks():
            self.record(item)
        for zone in [*board.Zones(),*board.FindFootprintByReference("U3").Zones()]:
            if not zone.GetIsRuleArea():
                continue
            layers = tuple(i for i,layer in enumerate(self.layers) if zone.IsOnLayer(layer))
            box = zone.GetBoundingBox()
            x,y = xy(box.GetOrigin())
            r,b = xy(box.GetEnd())
            poly = [(x,y),(r,y),(r,b),(x,b)]
            self.reserves.append((layers,poly,zone.GetDoNotAllowTracks(),zone.GetDoNotAllowVias()))

    def record(self, item):
        if isinstance(item, pcb.PCB_VIA):
            # Candidate and inherited path vias use a single finished copper diameter.
            at = xy(item.GetPosition())
            for z, layer in enumerate(self.layers):
                self.obstacles.append((item.GetNetname(),(z,),[at],pcb.ToMM(item.GetWidth(layer))/2,"via"))
            self.holes.append(([at],pcb.ToMM(item.GetDrillValue())/2,False))
        else:
            z = self.layers.index(item.GetLayer())
            self.obstacles.append((item.GetNetname(),(z,),[xy(item.GetStart()),xy(item.GetEnd())],
                                   pcb.ToMM(item.GetWidth())/2,"track"))

    @staticmethod
    def stamp(dst, vertices, radius):
        a,b = np.asarray(vertices).min(axis=0)-radius
        c,d = np.asarray(vertices).max(axis=0)+radius
        i,j = max(0,math.ceil((a-50)/STEP)),max(0,math.ceil((b-50)/STEP))
        m,n = min(NX,math.floor((c-50)/STEP)+1),min(NY,math.floor((d-50)/STEP)+1)
        if i >= m or j >= n:
            return
        x = (50+STEP*np.arange(i,m))[None,:]
        y = (50+STEP*np.arange(j,n))[:,None]
        region = dst[j:n,i:m]
        if len(vertices)==1:
            px,py = vertices[0]
            region |= (x-px)**2+(y-py)**2 <= radius**2
            return
        segments = zip(vertices, vertices[1:]+vertices[:1]) if len(vertices)>2 else [(vertices[0],vertices[1])]
        inside = np.zeros_like(region)
        for (px,py),(qx,qy) in segments:
            dx,dy = qx-px,qy-py
            if dx or dy:
                t = np.clip(((x-px)*dx+(y-py)*dy)/(dx*dx+dy*dy),0,1)
                region |= (x-px-t*dx)**2+(y-py-t*dy)**2 <= radius**2
            if len(vertices)>2 and dy:
                inside ^= ((y>py)!=(y>qy)) & (x < px+(y-py)*dx/dy)
        region |= inside

    def maps(self, net, width):
        block = np.zeros((len(self.layers),NY,NX),dtype=np.bool_)
        blocked_via = np.zeros((NY,NX),dtype=np.bool_)
        clearance = gap(net)
        for other, sides, shape, radius, kind in self.obstacles:
            if other == net:
                if kind == "pad":
                    self.stamp(blocked_via,shape,.34)
                continue
            required = max(clearance,gap(other))
            # Keep new inner LV copper outside the projection of existing HV metal.
            copper_layers = set(sides) | set(range(2,len(self.layers))) if gap(other)>1 else sides
            for z in copper_layers:
                self.stamp(block[z],shape,radius+required+width/2+.009)
            self.stamp(blocked_via,shape,radius+required+.31)
        for shape, radius, mounting in self.holes:
            keepout = 4.4 if mounting and clearance>1 else .25
            for layer in block:
                self.stamp(layer,shape,radius+keepout+width/2+.009)
            self.stamp(blocked_via,shape,radius+max(keepout+.31,.43))
        for sides, poly, tracks, vias in self.reserves:
            if tracks:
                for z in sides:
                    self.stamp(block[z],poly,width/2+.016)
            if vias:
                self.stamp(blocked_via,poly,.31)
        for mask, radius in ((block,width/2), (blocked_via,.3)):
            edge = math.ceil((max(.3, 2 if clearance>1 else .3)+radius+.01)/STEP)
            mask[..., :edge, :] = mask[..., -edge:, :] = True
            mask[..., :, :edge] = mask[..., :, -edge:] = True
        if clearance > 1:
            block[2:] = True
        return block, ~blocked_via

    def anchors(self, item, block):
        if isinstance(item,list):
            points, exact = [], {}
            for entry in item:
                nodes, joins = self.anchors(entry,block)
                points.extend(nodes)
                exact.update(joins)
            return list(dict.fromkeys(points)),exact
        if isinstance(item, tuple):
            at, z = item
            pos = xy(at)
            n,m = grid(*pos)
            nodes = [(i,j,z) for i in range(max(0,n-1),min(NX,n+2)) for j in range(max(0,m-1),min(NY,m+2))
                     if math.dist(mm(i,j),pos)<.15 and not block[z,j,i]]
            return nodes, {state:pos for state in nodes}
        if isinstance(item, pcb.PCB_VIA):
            pos = xy(item.GetPosition())
            n,m = grid(*pos)
            nodes = [(i,j,z) for z in range(len(self.layers)) for i in range(n-2,n+3) for j in range(m-2,m+3)
                     if math.dist(mm(i,j),pos)<.24 and not block[z,j,i]]
            return nodes, {state:pos for state in nodes}
        bounds = item.GetBoundingBox()
        sx,sy = xy(bounds.GetOrigin())
        ex,ey = xy(bounds.GetEnd())
        left,top = grid(sx-.15,sy-.15)
        right,bottom = grid(ex+.15,ey+.15)
        nodes = []
        for z,layer in enumerate(self.layers):
            if not item.IsOnLayer(layer):
                continue
            for y in range(max(0,top),min(NY,bottom+1)):
                for x in range(max(0,left),min(NX,right+1)):
                    if not block[z,y,x] and item.HitTest(point(*mm(x,y))):
                        nodes.append((x,y,z))
        return nodes, {}

    def connect(self, net, a, b, limit=170_000):
        width = .50 if net in WIDTH_05 else .30 if gap(net)>1 else .20
        block, can_via = self.maps(net,width)
        begin, begin_exact = self.anchors(a,block)
        end, end_exact = self.anchors(b,block)
        result = path(block, can_via, begin, end, limit)
        if not result:
            return [], (len(begin),len(end))
        corners = [result[0]]
        for old, cur, new in zip(result,result[1:],result[2:]):
            if tuple(q-p for p,q in zip(old,cur)) != tuple(q-p for p,q in zip(cur,new)):
                corners.append(cur)
        if len(result)>1:
            corners.append(result[-1])
        items = []
        if corners[0] in begin_exact:
            start = begin_exact[corners[0]]
            if start != mm(*corners[0][:2]):
                items.append(self.trace(net,width,corners[0][2],start,mm(*corners[0][:2])))
        for p,q in zip(corners,corners[1:]):
            if p[2]==q[2]:
                items.append(self.trace(net,width,p[2],mm(*p[:2]),mm(*q[:2])))
            else:
                via = pcb.PCB_VIA(self.board)
                via.SetPosition(point(*mm(*p[:2])))
                via.SetViaType(pcb.VIATYPE_THROUGH)
                via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
                via.SetWidth(pcb.FromMM(.60))
                via.SetDrill(pcb.FromMM(.30))
                via.SetNet(self.board.FindNet(net))
                self.board.Add(via)
                self.record(via)
                items.append(via)
        if corners[-1] in end_exact:
            finish = end_exact[corners[-1]]
            if finish != mm(*corners[-1][:2]):
                items.append(self.trace(net,width,corners[-1][2],mm(*corners[-1][:2]),finish))
        return items, (len(begin),len(end))

    def trace(self, net, width, z, start, end):
        item = pcb.PCB_TRACK(self.board)
        item.SetStart(point(*start))
        item.SetEnd(point(*end))
        item.SetLayer(self.layers[z])
        item.SetWidth(pcb.FromMM(width))
        item.SetNet(self.board.FindNet(net))
        self.board.Add(item)
        self.record(item)
        return item
