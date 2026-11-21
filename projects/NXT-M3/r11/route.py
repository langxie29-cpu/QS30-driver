"""Two-layer R11 pre-routing with conservative occupied copper and native DRC rollback."""
from collections import defaultdict
import heapq
import itertools
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pcbnew as pcb

from configure import classify, POWER

HERE = Path(__file__).resolve().parent
EDA = HERE / "eda/NXT-M3-R11.kicad_pcb"
CLI = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin")) / "kicad-cli.exe"
F, B = pcb.F_Cu, pcb.B_Cu
STEP = .25
X0, Y0 = 50, 50
NX, NY = 521, 321
LAYERS = (F, B)
GROUPS = (
    ("power", {"5V_RAW", "5V_FUSED", "5V_PROT", "5V_HV", "HV_ISOLATE_IN", "LV_SW",
               "GATE_BIAS", "GATE_HV", "GATE_SNK", "GATE_SRC", "BIAS_SW", "BIAS_FB",
               "SW_HV", "SNUB", "HV_ISENSE", "HV_VCC"}),
    ("protection", {"ALIM_1", "ALIM_2", "ALIM_3", "HV_BUS", "PWM_RAW"}),
    ("mcu_oled", {"3V3", "OLED_3V3"}),
    ("shift_cathodes", set()),
    ("return", {"GND"}),
)


def pos(item):
    point = item.GetPosition()
    return pcb.ToMM(point.x), pcb.ToMM(point.y)


def vec(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def box(item):
    bound = item.GetBoundingBox()
    return tuple(pcb.ToMM(value) for value in
                 (bound.GetLeft(), bound.GetTop(), bound.GetRight(), bound.GetBottom()))


def gap(net):
    if net in {"SW_HV", "SNUB"}:
        return 3.2
    if re.fullmatch(r"K[123]_[0-9]", net) or net == "HV_BUS" or net.startswith(
            ("ANODE_", "ALIM_", "BLEED_", "HV_FB_", "HV_OVP_S_", "HV_RES_S_")):
        return 2.0
    return .2


def width(net):
    if net in POWER or net == "SW_HV":
        return .5
    if gap(net) > .2:
        return .30
    if net in {"3V3", "GND", "GATE_BIAS", "OLED_3V3"}:
        return .25
    return .20


def idx(x, y):
    return (round((x - X0) / STEP), round((y - Y0) / STEP))


def mm(x, y):
    return X0 + x * STEP, Y0 + y * STEP


def stamp(grid, layer, bounds, margin):
    l, t, r, b = bounds
    x, y = math.ceil((l-X0-margin)/STEP), math.ceil((t-Y0-margin)/STEP)
    u, v = math.floor((r-X0+margin)/STEP), math.floor((b-Y0+margin)/STEP)
    if u >= 0 and v >= 0 and x < NX and y < NY:
        grid[layer, max(0,y):min(NY,v+1), max(0,x):min(NX,u+1)] = True


def find_path(block, via, starts, endpoints, limit):
    targets = set(endpoints)
    if not starts or not targets:
        return []
    minx, miny = min(q[0] for q in targets), min(q[1] for q in targets)
    maxx, maxy = max(q[0] for q in targets), max(q[1] for q in targets)

    def heuristic(x, y):
        return max(minx-x, 0, x-maxx) + max(miny-y, 0, y-maxy)

    cost = {state: 0 for state in starts}
    queue = [(heuristic(x,y), 0, x,y,z) for x,y,z in starts]
    heapq.heapify(queue)
    parents = {}
    count = 0
    while queue and count < limit:
        _, dist, x, y, z = heapq.heappop(queue)
        state = x,y,z
        if dist != cost[state]:
            continue
        if state in targets:
            path = [state]
            while path[-1] in parents:
                path.append(parents[path[-1]])
            return path[::-1]
        count += 1
        steps = [(x+1,y,z,1), (x-1,y,z,1), (x,y+1,z,1), (x,y-1,z,1)]
        if not via[y][x]:
            steps.append((x,y,1-z,14))
        for i,j,k,delta in steps:
            if i<0 or j<0 or i>=NX or j>=NY or block[k][j][i]:
                continue
            child = i,j,k
            total = dist + delta
            if total < cost.get(child, 10**9):
                cost[child] = total
                parents[child] = state
                heapq.heappush(queue, (total + heuristic(i,j), total, i,j,k))
    return []


class Draft:
    def __init__(self, board):
        self.board = board
        self.pads = defaultdict(list)
        self.obstacles = []
        self.saved = []
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            for p in fp.Pads():
                net = p.GetNetname()
                layers = tuple(i for i, side in enumerate(LAYERS) if p.IsOnLayer(side))
                if not layers:
                    continue
                self.obstacles.append((net, layers, box(p), "pad"))
                if net and not net.startswith("unconnected-"):
                    self.pads[net].append((ref, p, layers))
            if ref.startswith("MH"):
                x,y = pos(fp)
                self.obstacles.append(("", (0,1), (x-4,y-4,x+4,y+4), "reserve"))
        for zone in board.Zones():
            if zone.GetIsRuleArea() and zone.GetDoNotAllowTracks():
                self.obstacles.append(("", (0,1), box(zone), "reserve"))

    def maps(self, net):
        route = np.zeros((2,NY,NX), dtype=np.bool_)
        via = route.copy()
        clearance = gap(net)
        for other, layers, bounds, kind in self.obstacles:
            if other == net and kind != "reserve":
                if kind in ("pad", "via"):
                    for layer in layers:
                        stamp(via, layer, bounds, .42)
                continue
            separation = max(clearance, gap(other))
            if kind == "reserve":
                separation = .4 if clearance <= .2 else clearance
            for layer in layers:
                stamp(route, layer, bounds, width(net)/2 + separation + .042)
                stamp(via, layer, bounds, .30 + separation + .042)
        edge = math.ceil((max(clearance if clearance > .2 else .30, .30) + width(net)/2 + .05)/STEP)
        for grid in (route, via):
            grid[:, :edge] = grid[:, -edge:] = True
            grid[:, :, :edge] = grid[:, :, -edge:] = True
        if net in {"SW_HV", "SNUB", "HV_ISENSE", "LV_SW", "BIAS_SW"}:
            via[:] = True
        return route.tolist(), (via[0]|via[1]).tolist()

    def anchors(self, entry, block):
        _, pad, layers = entry
        l,t,r,b = box(pad)
        x,y = pos(pad)
        j,k = idx(x,y)
        out = []
        for z in layers:
            for p,q in itertools.product(range(j-2,j+3), range(k-2,k+3)):
                if not (0<=p<NX and 0<=q<NY) or block[z][q][p]:
                    continue
                u,v = mm(p,q)
                # All joins remain within the central portion of rounded or rotated pads.
                if abs(u-x) <= min(.32, .38*(r-l)) and abs(v-y) <= min(.32, .38*(b-t)):
                    out.append((p,q,z))
        return out

    def add_track(self, coords, width_mm, net, z):
        item = pcb.PCB_TRACK(self.board)
        item.SetStart(vec(*coords[0]))
        item.SetEnd(vec(*coords[1]))
        item.SetLayer(LAYERS[z])
        item.SetWidth(pcb.FromMM(width_mm))
        item.SetNetCode(self.board.FindNet(net).GetNetCode())
        self.board.Add(item)
        self.obstacles.append((net, (z,), box(item), "track"))
        return item

    def add_via(self, point, net):
        item = pcb.PCB_VIA(self.board)
        item.SetPosition(vec(*point))
        item.SetViaType(pcb.VIATYPE_THROUGH)
        item.SetLayerPair(F,B)
        item.SetWidth(pcb.FromMM(.6))
        item.SetDrill(pcb.FromMM(.3))
        item.SetNetCode(self.board.FindNet(net).GetNetCode())
        self.board.Add(item)
        self.obstacles.append((net, (0,1), box(item), "via"))
        return item

    def route(self, net, a, b, limit=8500):
        block, via = self.maps(net)
        path = find_path(block, via, self.anchors(a,block), self.anchors(b,block), limit)
        if not path:
            return
        corners = [path[0]]
        for j in range(1,len(path)-1):
            p,q,r = path[j-1:j+2]
            if tuple(q[d]-p[d] for d in range(3)) != tuple(r[d]-q[d] for d in range(3)):
                corners.append(q)
        if len(path)>1:
            corners.append(path[-1])
        tracks = []
        for p,q in zip(corners,corners[1:]):
            if p[2] != q[2]:
                tracks.append(self.add_via(mm(*p[:2]),net))
            elif p != q:
                tracks.append(self.add_track((mm(*p[:2]),mm(*q[:2])),width(net),net,p[2]))
        for entry, point in ((a,path[0]),(b,path[-1])):
            center, join = pos(entry[1]), mm(*point[:2])
            if center != join:
                tracks.append(self.add_track((center,join),width(net),net,point[2]))
        if tracks:
            self.saved.append((net,a[0],b[0],tracks))

    def save_drc(self, stage):
        pcb.SaveBoard(str(EDA),self.board)
        output = HERE / "evidence/r3" / (stage + ".json")
        command = [str(CLI), "pcb", "drc", "--schematic-parity", "--format", "json",
                   "--exit-code-violations", "-o", str(output), str(EDA)]
        proc = subprocess.run(command, capture_output=True)
        (output.with_suffix(".command.txt")).write_text(
            subprocess.list2cmdline(command) + f"\nexit={proc.returncode}\n" +
            proc.stdout.decode("utf-8","replace") + proc.stderr.decode("utf-8","replace"), encoding="utf-8")
        if proc.returncode not in (0, 5):
            raise RuntimeError(proc.returncode)
        return json.loads(output.read_text(encoding="utf-8-sig"))

    def settle(self, stage):
        latest = self.save_drc(stage + "_initial")
        bad = {item["uuid"] for failure in latest["violations"] for item in failure["items"]}
        discard = [row for row in self.saved if any(track.m_Uuid.AsString() in bad for track in row[3])]
        if discard:
            for row in discard:
                for track in row[3]:
                    self.board.Remove(track)
                self.saved.remove(row)
            prior = self.saved.copy()
            self.__init__(self.board)
            self.saved = prior
            for net, _, _, items in prior:
                for item in items:
                    layers = (0,1) if isinstance(item,pcb.PCB_VIA) else (LAYERS.index(item.GetLayer()),)
                    self.obstacles.append((net,layers,box(item),"via" if isinstance(item,pcb.PCB_VIA) else "track"))
            latest = self.save_drc(stage)
        print(stage, "kept routes",len(self.saved),"removed",len(discard),
              "native unrouted items",len(latest["unconnected_items"]),flush=True)

    def pairs(self, net, maxspan=None):
        entries = self.pads[net]
        spans = []
        for i,j in itertools.combinations(range(len(entries)),2):
            a,b = entries[i],entries[j]
            distance = math.dist(pos(a[1]),pos(b[1]))
            if maxspan is None or distance <= maxspan:
                spans.append((distance +(0 if set(a[2]) & set(b[2]) else 1.5), i,j))
        previous = [set((net,a,b)) for net,a,b,_ in self.saved]
        return [(score,entries[i],entries[j]) for score,i,j in sorted(spans)
                if set((net,entries[i][0],entries[j][0])) not in previous]


def run():
    board = pcb.LoadBoard(str(EDA))
    if len(list(board.GetTracks())):
        raise RuntimeError("Run from the untracked R1 board, not over an edited PCB")
    placement = {fp.GetReference():fp for fp in board.GetFootprints()}
    moves = {"R400":(136,120),"R401":(146,120),"R402":(156,120),"R403":(166,120),
             "R404":(136,126),"R405":(146,126),"R406":(156,126),"R407":(166,126)}
    for ref, point in moves.items():
        placement[ref].SetPosition(vec(*point))
    (HERE/"evidence/r3").mkdir(parents=True,exist_ok=True)
    for item in board.GetDrawings():
        if hasattr(item,"GetText") and item.GetText().startswith("PRELAYOUT / HOLD"):
            item.SetText("R11 ROUTING STUDY / HV HOLD / SOCKETS UNDRILLED")
    design = Draft(board)
    design.save_drc("placement")
    excluded = set().union(*(nets for _,nets in GROUPS))
    for stage, manual in GROUPS:
        if stage == "protection":
            nets = manual | {net for net in design.pads if gap(net)> .2 and not net.startswith("K")} - GROUPS[0][1]
            nets |= {net for net in design.pads if classify(net) == "SAFETY_CONTROL"}
        elif stage == "mcu_oled":
            nets = manual | {net for net in design.pads if net.startswith(("OLED_", "MCU_", "UART", "BOOT", "STRAP", "RST", "FRONT", "BUCK"))}
        elif stage == "shift_cathodes":
            nets = {net for net in design.pads if net not in excluded and net.startswith(("DRV_", "BASE_", "SR_", "SER"))}
        else:
            nets = manual
        jobs = []
        for net in sorted(nets):
            pairs = design.pairs(net, 14 if stage=="return" else 115)
            if stage=="return":
                pairs = pairs[:300]
            elif len(design.pads[net])>3:
                pairs = pairs[:max(0,len(design.pads[net])*3)]
            jobs.extend((score,net,a,b) for score,a,b in pairs)
        roots = {}
        def find(key):
            while key in roots:
                key = roots[key]
            return key
        for score,net,a,b in sorted(jobs,key=lambda row:(row[0],row[1])):
            if stage=="return" and score>9:
                continue
            k1, k2 = a[1].m_Uuid.AsString(), b[1].m_Uuid.AsString()
            one,two = find(k1),find(k2)
            if one!=two:
                before = len(design.saved)
                design.route(net,a,b, 26000 if stage in ("power","shift_cathodes","mcu_oled") else 8000)
                if len(design.saved)>before:
                    roots[one] = two
        design.settle(stage)
    result = [{"net":net,"from":a,"to":b,"segments":sum(isinstance(item,pcb.PCB_TRACK)
               and not isinstance(item,pcb.PCB_VIA) for item in items),
               "vias":sum(isinstance(item,pcb.PCB_VIA) for item in items)}
              for net,a,b,items in design.saved]
    (HERE/"evidence/r3/routes.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    run()

