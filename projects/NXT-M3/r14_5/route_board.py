"""Route copper on the delivered R14.4 board with native KiCad objects."""
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import heapq
import json
import math
import os
from pathlib import Path
import shutil
import sys
from uuid import NAMESPACE_URL, uuid5

import numpy as np
import pcbnew as pcb
if deps := os.environ.get("NXT_R145_DEPS"):
    sys.path.insert(0, deps)

from scipy.ndimage import label
from shapely import box, intersects_xy
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "r14"))
from route_r14_1 import LAYERS, MOVES, WIDTH_05, gap, point, xy
from verify_r14_1 import STOP

BASE = HERE.parent / "r14_4/eda"
BASE_STEM = "NXT-M3-R14.4"
STEM = "NXT-M3-R14.5"
STEP = .1
VIA = .60
DRILL = .30
MARGIN = .008
EDGE = (50, 50, 180, 130)


def uid(item):
    return str(item.m_Uuid.AsString())


def channel_pairs(number, board):
    i = number - 1
    q, feed, pull = f"Q{number}", f"R{100+i}", f"R{200+i}"
    u = "U" + str(20 + i // 8)
    pin = (15, 1, 2, 3, 4, 5, 6, 7)[i % 8]
    v = f"V{1+i//10}"
    cathode_pin = next(p.GetNumber() for p in board.refs[v].Pads()
                       if p.GetNetname() == f"K{1+i//10}_{i%10}")
    return (
        ("drive", f"{u}.{pin}", f"{feed}.1"),
        ("base_feed", f"{feed}.2", f"{q}.1"),
        ("base_pulldown", f"{pull}.1", f"{q}.1"),
        ("return_local", f"{pull}.2", f"{q}.2"),
        ("return_driver", f"{u}.8", f"{q}.2"),
        ("cathode_socket", f"{q}.3", f"{v}.{cathode_pin}"),
    )


def polygons(poly):
    def ring(line):
        return [xy(line.CPoint(i)) for i in range(line.PointCount())]

    return unary_union([Polygon(ring(poly.COutline(i)),
                                [ring(poly.CHole(i, j)) for j in range(poly.HoleCount(i))])
                        for i in range(poly.OutlineCount())]).buffer(0)


def copper(item, layer):
    if isinstance(item, pcb.PCB_VIA):
        return Point(xy(item.GetPosition())).buffer(pcb.ToMM(item.GetWidth(layer))/2, quad_segs=12)
    if isinstance(item, pcb.PCB_TRACK) and not isinstance(item, pcb.PCB_ARC):
        return LineString([xy(item.GetStart()), xy(item.GetEnd())]).buffer(
            pcb.ToMM(item.GetWidth())/2, quad_segs=12)
    poly = pcb.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(poly, layer, 0, pcb.FromMM(.002), pcb.ERROR_OUTSIDE)
    return polygons(poly)


def create_project(out):
    out.mkdir(parents=True, exist_ok=True)
    for source in sorted(BASE.iterdir()):
        if source.is_dir() and source.suffix == ".pretty":
            shutil.copytree(source, out / source.name, dirs_exist_ok=True)
        elif source.is_file() and (source.suffix in (".kicad_sch", ".kicad_pro", ".kicad_dru",
                                                      ".kicad_sym", ".kicad_pcb")
                                   or source.name.endswith("-lib-table")):
            dest = out / source.name.replace(BASE_STEM, STEM)
            data = source.read_bytes()
            if source.suffix in (".kicad_sch", ".kicad_pro"):
                data = data.replace(BASE_STEM.encode(), STEM.encode())
            dest.write_bytes(data)



def common_components(blocks, vias, starts, ends):
    """Screen a raster window for disconnected islands before running A*."""
    if not starts or not ends:
        return False
    labels = np.array([label(~layer)[0] for layer in blocks])
    left = {(z, int(labels[z,y,x])) for x,y,z in starts}
    right = {(z, int(labels[z,y,x])) for x,y,z in ends}
    if left & right:
        return True
    edges = defaultdict(set)
    at_vias = labels[:,vias]
    for z in range(len(blocks)):
        for k in range(z):
            both = (at_vias[z] != 0) & (at_vias[k] != 0)
            if not np.any(both):
                continue
            multiplier = int(at_vias[k].max()) + 1
            for pair in np.unique(at_vias[z,both] * multiplier + at_vias[k,both]):
                i,j = divmod(int(pair),multiplier)
                edges[z,i].add((k,j))
                edges[k,j].add((z,i))
    pending = list(left)
    while pending:
        group = pending.pop()
        if group in right:
            return True
        more = edges[group] - left
        left.update(more)
        pending.extend(more)
    return False


def search(block, via_ok, starts, ends, step, via_penalty, limit):
    nl, ny, nx = block.shape
    if not starts or not ends:
        return [], 0
    via_lookup = via_ok.tolist()
    blocked = block.tolist()
    costs = [{} for _ in range(nl)]
    prev = {}
    xy_targets = [(x,y) for x,y,_ in ends]
    x0, x1 = min(x for x,y in xy_targets), max(x for x,y in xy_targets)
    y0, y1 = min(y for x,y in xy_targets), max(y for x,y in xy_targets)

    @lru_cache(maxsize=None)
    def estimate(x, y):
        dx, dy = max(0, x0-x, x-x1), max(0, y0-y, y-y1)
        return 10*max(dx,dy) + 4*min(dx,dy)

    queue = []
    for state, cost in starts.items():
        x,y,z = state
        costs[z][(x,y)] = cost
        heapq.heappush(queue, (cost+estimate(x,y), -cost, state))
    visited = 0
    while queue and visited < limit:
        _, neg_cost, state = heapq.heappop(queue)
        x,y,z = state
        d = -neg_cost
        layer_cost = costs[z]
        if d != layer_cost[(x,y)]:
            continue
        if state in ends:
            route = [state]
            while state in prev:
                state = prev[state]
                route.append(state)
            return route[::-1], visited
        visited += 1
        mask = blocked[z]
        for dx,dy,delta in MOVES:
            i,j = x+dx,y+dy
            if not (0 <= i < nx and 0 <= j < ny) or mask[j][i]:
                continue
            if dx and dy and (mask[j][x] or mask[y][i]):
                continue
            n = d+delta+(1 if z == 3 else 0)
            if n < layer_cost.get((i,j), math.inf):
                child = i,j,z
                layer_cost[(i,j)] = n
                prev[child] = state
                heapq.heappush(queue, (n+estimate(i,j), -n, child))
        if not via_lookup[y][x]:
            continue
        for other in range(nl):
            n = d + round(10 * via_penalty / step)
            if other == z or blocked[other][y][x] or n >= costs[other].get((x,y), math.inf):
                continue
            child = x,y,other
            costs[other][(x,y)] = n
            prev[child] = state
            heapq.heappush(queue, (n+estimate(x,y), -n, child))
    return [], visited


class BoardRouter:
    def __init__(self, path):
        self.board = path if isinstance(path, pcb.BOARD) else pcb.LoadBoard(str(path))
        self.refs = {f.GetReference(): f for f in self.board.GetFootprints()}
        self.by_id = {}
        self.shapes = {}
        self.obstacles = []
        self.holes = []
        self.keepouts = []
        self.events = []
        for f in self.refs.values():
            for pad in f.Pads():
                self.record(pad)
                drill = max(xy(pad.GetDrillSize()))
                if drill:
                    self.holes.append((Point(xy(pad.GetPosition())).buffer(drill/2),
                                       f.GetReference().startswith("MH"), uid(pad)))
            for zone in f.Zones():
                self.keepout(zone)
        for t in self.board.GetTracks():
            self.record(t)
        for z in self.board.Zones():
            self.keepout(z)
        self.sync()

    def sync(self):
        assert self.board.BuildConnectivity()
        self.conn = self.board.GetConnectivity()
        self.components = {}

    def keepout(self, zone):
        if zone.GetIsRuleArea():
            g = polygons(zone.Outline())
            layers = tuple(z for z, layer in enumerate(LAYERS) if zone.IsOnLayer(layer))
            self.keepouts.append((g, layers, zone.GetDoNotAllowTracks(),
                                  zone.GetDoNotAllowVias()))

    def record(self, item):
        ident = uid(item)
        self.by_id[ident] = item
        net = item.GetNetname()
        for z, layer in enumerate(LAYERS):
            if item.IsOnLayer(layer):
                shape = copper(item, layer)
                if not shape.is_empty:
                    self.shapes[ident,z] = shape
                    self.obstacles.append((ident, net, gap(net), z, shape,
                                           isinstance(item, pcb.PAD)))
        if isinstance(item, pcb.PCB_VIA):
            self.holes.append((Point(xy(item.GetPosition())).buffer(
                pcb.ToMM(item.GetDrillValue())/2), False, ident))

    def pads(self, label):
        ref, pin = label.split(".")
        result = [p for p in self.refs[ref].Pads() if p.GetNumber() == pin]
        assert result, label
        return result

    def component(self, item):
        ident = uid(item)
        if ident not in self.components:
            net = item.GetNetname()
            connected = {uid(x) for x in self.conn.GetConnectedItems(item)
                         if x.GetNetname() == net}
            connected.add(ident)
            ids = frozenset(connected)
            for k in ids:
                self.components[k] = ids
        return self.components[ident]

    def connected(self, left, right):
        return any(uid(b) in self.component(a) for a in left for b in right)

    @staticmethod
    @lru_cache(maxsize=80000)
    def inflated(shape, radius):
        return shape.buffer(round(radius, 4), quad_segs=10)

    def grid(self, left, right, margin, step):
        values = [xy(obj.GetPosition()) for obj in left + right]
        xmin, ymin = map(min, zip(*values))
        xmax, ymax = map(max, zip(*values))
        ix = math.floor(max(EDGE[0], xmin-margin)/step)
        iy = math.floor(max(EDGE[1], ymin-margin)/step)
        endx = math.ceil(min(EDGE[2], xmax+margin)/step)
        endy = math.ceil(min(EDGE[3], ymax+margin)/step)
        return np.arange(ix,endx+1)*step, np.arange(iy,endy+1)*step

    def maps(self, net, width, xs, ys, padding, via_size=VIA):
        nx, ny = len(xs), len(ys)
        block = np.zeros((4,ny,nx), dtype=bool)
        via = np.zeros((ny,nx), dtype=bool)
        exclusions = [[] for _ in LAYERS]
        netgap = gap(net)
        rad = width/2
        edge = 2 if netgap > 1 else .30
        view = box(xs[0]-5.5, ys[0]-5.5, xs[-1]+5.5, ys[-1]+5.5)

        def stamp(dst, g):
            if g.is_empty:
                return
            x0,y0,x1,y1 = g.bounds
            i,j = xs.searchsorted(x0), ys.searchsorted(y0)
            m,n = xs.searchsorted(x1,"right"), ys.searchsorted(y1,"right")
            if i < m and j < n:
                dst[j:n,i:m] |= intersects_xy(g, xs[None,i:m], ys[j:n,None])

        def deny(z, g, allowance):
            shape = self.inflated(g, allowance)
            exclusions[z].append(shape)
            stamp(block[z], shape)

        def keep_edges(arr, hw):
            d = edge+hw+MARGIN
            arr[..., (ys < EDGE[1]+d) | (ys > EDGE[3]-d), :] = True
            arr[..., :, (xs < EDGE[0]+d) | (xs > EDGE[2]-d)] = True

        for ident, other, other_gap, z, g, is_pad in self.obstacles:
            if not view.intersects(g):
                continue
            if other == net:
                if is_pad:
                    stamp(via, self.inflated(g,via_size/2+MARGIN))
                continue
            required = max(netgap,other_gap)
            allowance = required+rad+MARGIN+padding
            deny(z,g,allowance)
            if other_gap > 1 and netgap <= 1 and z < 2:
                for inner in (2,3):
                    deny(inner,g,allowance)
            stamp(via,self.inflated(g,required+via_size/2+MARGIN))
        for shape, mounting, ident in self.holes:
            if not view.intersects(shape):
                continue
            item = self.by_id[ident]
            same = item.GetNetname() == net
            keepout = 4.4 if mounting and netgap > 1 else .25
            if not same:
                for z in range(4):
                    deny(z,shape,keepout+rad+MARGIN+padding)
            stamp(via,self.inflated(shape,max(keepout+via_size/2,.25+DRILL/2)+MARGIN))
        for shape, layers, tracks, vias in self.keepouts:
            if not view.intersects(shape):
                continue
            if tracks:
                for z in layers:
                    deny(z,shape,rad+MARGIN+padding)
            if vias:
                stamp(via,self.inflated(shape,via_size/2+MARGIN))
        keep_edges(block, rad)
        keep_edges(via,via_size/2)
        if netgap > 1:
            block[2:] = True
        return block, ~via, exclusions

    def anchors(self, items, block, xs, ys, width):
        nodes = {}
        for item in items:
            ident = uid(item)
            centre_x, centre_y = xy(item.GetPosition())
            for z in range(4):
                shape = self.shapes.get((ident,z))
                if shape is None:
                    continue
                # Trace cap must enter the existing copper by at least 45 um.
                # Pad centres have lower cost whenever the inherited geometry permits.
                target = self.inflated(shape, width/2-.045)
                if target.is_empty:
                    continue
                x0,y0,x1,y1 = target.bounds
                i,j = xs.searchsorted(x0),ys.searchsorted(y0)
                e,f = xs.searchsorted(x1,"right"),ys.searchsorted(y1,"right")
                if i >= e or j >= f:
                    continue
                mask = intersects_xy(target,xs[None,i:e],ys[j:f,None]) & ~block[z,j:f,i:e]
                ys_found,xs_found = np.nonzero(mask)
                for ly,lx in zip(ys_found.tolist(),xs_found.tolist()):
                    x,y = i+lx,j+ly
                    if isinstance(item,pcb.PAD):
                        cost = round(28*math.hypot(xs[x]-centre_x,ys[y]-centre_y))
                    else:
                        cost = 0
                    state = x,y,z
                    nodes[state] = min(cost,nodes.get(state,math.inf))
        return nodes

    def attempt(self, net, left, right, width, margin, step, padding, via_penalty, limit, via_size):
        xs,ys = self.grid(left,right,margin,step)
        blocks,vias,exclusions = self.maps(net,width,xs,ys,padding,via_size)
        start = self.anchors(left,blocks,xs,ys,width)
        end = self.anchors(right,blocks,xs,ys,width)
        possible = common_components(blocks,vias,start,end)
        path,visited = search(blocks,vias,start,end,step,via_penalty,limit) if possible else ([],0)
        info = dict(grid_mm=step, window_mm=[float(xs[0]),float(ys[0]),float(xs[-1]),float(ys[-1])],
                    start_access=len(start), end_access=len(end), visited=visited, limit=limit)
        if len(path) == 1:
            x,y,z = path[0]
            for dx,dy,_ in MOVES[:4]:
                if 0 <= x+dx < len(xs) and 0 <= y+dy < len(ys) and not blocks[z,y+dy,x+dx]:
                    path.append((x+dx,y+dy,z))
                    break
        if len(path) < 2:
            info["failure"] = "no access" if not start or not end else "search limit" if possible else "isolated corridor"
            return [],info
        corners = [path[0]]
        for a,b,c in zip(path,path[1:],path[2:]):
            if tuple(q-p for p,q in zip(a,b)) != tuple(q-p for p,q in zip(b,c)):
                corners.append(b)
        corners.append(path[-1])
        segments = []
        trees = {}
        for a,b in zip(corners,corners[1:]):
            x,y,z = a
            i,j,k = b
            at,end = (float(xs[x]),float(ys[y])),(float(xs[i]),float(ys[j]))
            if z == k:
                if z not in trees:
                    trees[z] = STRtree(exclusions[z])
                if len(trees[z].query(LineString((at,end)),predicate="intersects")):
                    info["failure"] = "continuous geometry blocked"
                    return [],info
            segments.append((z,k,at,end))
        return segments,info

    def nearby_component(self, items, opposite):
        positions = [Point(xy(x.GetPosition())) for x in opposite]
        ids = set().union(*(self.component(x) for x in items))
        candidates = set(ids) & self.by_id.keys()
        dist = lambda i: min((shape.distance(p) for z in range(4) for p in positions
                              if (shape := self.shapes.get((i,z))) is not None), default=1000)
        close = sorted(candidates, key=lambda i:(dist(i),i))[:9]
        return [self.by_id[i] for i in close]

    def route(self, label, left, right, *, margin=9, limit=130000, via_penalty=7,
              alternatives=True, via_size=VIA):
        if self.connected(left,right):
            return True
        net = left[0].GetNetname()
        assert net and all(x.GetNetname()==net for x in left+right), (label,net)
        left_original, right_original = left, right
        left = self.nearby_component(left_original, right_original)
        right = self.nearby_component(right_original, left_original)
        width = .50 if net in WIDTH_05 or net in ("SW_HV","SNUB","HV_BUS") else (
            .30 if gap(net)>1 or net == "3V3" else .20)
        tries = [(margin,STEP,0)]
        if alternatives:
            tries += [(margin+4,.05,0),(margin+5,.1,.055)]
        diagnostic = []
        for radius,step,padding in tries:
            looking,stats = self.attempt(net,left,right,width,radius,step,padding,via_penalty,limit,via_size)
            diagnostic.append(stats)
            if looking:
                break
        event = dict(label=label,net=net,width_mm=width,attempts=diagnostic,
                     left=[(uid(x),xy(x.GetPosition())) for x in left],
                     right=[(uid(x),xy(x.GetPosition())) for x in right],
                     committed=bool(looking),objects=[])
        self.events.append(event)
        if not looking:
            print("BLOCK",label,net,[(x["start_access"],x["end_access"],x["visited"],x["failure"])
                                    for x in diagnostic],flush=True)
            return False
        added = []
        for z,k,at,end in looking:
            if z != k:
                item = pcb.PCB_VIA(self.board)
                item.SetPosition(point(*at))
                item.SetViaType(pcb.VIATYPE_THROUGH)
                item.SetLayerPair(pcb.F_Cu,pcb.B_Cu)
                item.SetWidth(pcb.FromMM(via_size))
                item.SetDrill(pcb.FromMM(DRILL))
            else:
                item = pcb.PCB_TRACK(self.board)
                item.SetLayer(LAYERS[z])
                item.SetStart(point(*at))
                item.SetEnd(point(*end))
                item.SetWidth(pcb.FromMM(width))
            item.SetNet(self.board.FindNet(net))
            item.SetUuidDirect(pcb.KIID(str(uuid5(NAMESPACE_URL,
                f"QS30-driver/R14.5/{net}/{z}/{k}/{at}/{end}"))))
            self.board.Add(item)
            added.append(item)
        self.sync()
        if not self.connected(left_original,right_original):
            for item in added:
                self.board.RemoveNative(item)
            self.sync()
            event["committed"] = False
            event["rejection"] = "KiCad connectivity did not acknowledge the endpoint overlap"
            print("REJECT", label, net, flush=True)
            return False
        for item in added:
            self.record(item)
        event["objects"] = [uid(x) for x in added]
        event["vias"] = sum(isinstance(x,pcb.PCB_VIA) for x in added)
        event["length_mm"] = round(sum(math.dist(a,b) for z,k,a,b in looking),3)
        print("ROUTE",label,net,event["length_mm"],event["vias"],flush=True)
        return True

    def pair(self, name, left, right, **kwargs):
        return self.route(f"{name} {left} -> {right}",self.pads(left),self.pads(right),**kwargs)

    def save(self, path):
        assert pcb.SaveBoard(str(path),self.board)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("q2","sample","group1","group2","group3","protect","general","refine"))
    p.add_argument("--out", type=Path, default=HERE)
    p.add_argument("--drc", type=Path)
    opts = p.parse_args()
    out = opts.out.resolve()
    eda = out / "eda"
    path = eda / f"{STEM}.kicad_pcb"
    if opts.stage == "q2":
        create_project(eda)
    if opts.stage == "q2":
        raw = pcb.LoadBoard(str(BASE / f"{BASE_STEM}.kicad_pcb"))
        r101 = raw.FindFootprintByReference("R101")
        r101.Flip(r101.GetPosition(), False)
        r101.SetPosition(point(74.0, 120.5))
        r101.SetOrientation(pcb.EDA_ANGLE(90, pcb.DEGREES_T))
        # Clear the 595 output-side corridor by transferring the 3V3 bridge
        # between the same two existing plated vias to In2.Cu.
        lift = {"2905d01e-294b-49d2-b6b7-90e9cca1403c", "d2191c0c-67e2-4616-bd97-80a907518584",
                "d5c6e317-9104-4f26-a76e-ef43a5072711"}
        for track in list(raw.GetTracks()):
            if uid(track) in lift:
                track.SetLayer(pcb.In2_Cu)
            if uid(track) == "61476acd-5e98-4179-8648-6f990c2a0321":
                raw.RemoveNative(track)
    b = BoardRouter(raw if opts.stage == "q2" else path)
    if opts.stage == "q2":
        assert b.pair(*channel_pairs(2,b)[1], margin=5)
        assert b.pair(*channel_pairs(2,b)[0], margin=11, limit=1300000)
        assert all(b.connected(b.pads(a),b.pads(c)) for n in (1,2)
                   for _,a,c in channel_pairs(n,b))
    if opts.stage in ("sample","group1","group2","group3"):
        groups = {"sample": range(3,6), "group1":range(6,11),
                  "group2":range(11,21), "group3":range(21,31)}
        channels = groups[opts.stage]
        from place_array import pose_array
        placed = pose_array(b, channels)
        if placed:
            b = BoardRouter(b.board)
            print("PLACEMENT", placed, flush=True)
        pairs = {n:channel_pairs(n,b) for n in channels}
        for idx in (5,1,2,3,4,0):
            for n in channels:
                name,left,right = pairs[n][idx]
                b.pair(f"Q{n} {name}",left,right,margin=6 if idx in (1,2,3) else 11,
                       via_penalty=6 if idx != 5 else 3, limit=700000)
    if opts.stage == "protect":
        for label,left,right in (
            ("OVP", "R61.2", "R62.1"), ("OVP comparator", "R64.1", "U13.2"),
            ("feedback", "R83.2", "R84.1"), ("SW snubber","D3.2","R86.1"),
            ("SNUB capacitor","R86.2","C48.1"), ("SNUB return","C48.2","R79.2"),
            *STOP,
        ):
            short = label.startswith(("SW snubber","SNUB capacitor"))
            b.pair(label,left,right,margin=3 if short else 11,via_penalty=8,
                   alternatives=not short)
    if opts.stage in ("general", "refine"):
        assert opts.drc
        report = json.loads(opts.drc.read_text(encoding="utf-8"))
        entries = []
        for v in report["unconnected_items"]:
            a,c = [b.by_id.get(x["uuid"]) for x in v["items"]]
            if a is None or c is None:
                continue
            net = a.GetNetname()
            d = math.dist(xy(a.GetPosition()),xy(c.GetPosition()))
            priority = 0 if gap(net)>1 or net in WIDTH_05 else (1 if net in ("3V3","GND") else 2)
            entries.append((priority,d,net,uid(a),uid(c),a,c))
        for _,d,net,ida,idc,a,c in sorted(entries,key=lambda entry:entry[:5]):
            label = f"native open {ida} -> {idc}"
            if opts.stage == "general":
                b.route(label,[a],[c],margin=6 if d<10 else 9,limit=65000,alternatives=False)
            else:
                b.route(label,[a],[c],margin=10 if d<10 else 14,limit=200000,
                        via_penalty=5,alternatives=d < 40 and net != "SNUB")
    b.save(path)
    (out / "evidence").mkdir(exist_ok=True)
    (out / "evidence" / f"routing-{opts.stage}.json").write_text(
        json.dumps(b.events,indent=2)+"\n",encoding="utf-8")
    print(Counter("routed" if e["committed"] else "blocked" for e in b.events))


if __name__ == "__main__":
    main()
