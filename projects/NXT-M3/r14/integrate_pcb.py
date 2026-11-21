"""Place the interface and route local R14 changes on the frozen R11 board."""
import collections
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
SYS = HERE.parent / "r11"
sys.path.insert(0, str(SYS))
import route
from placement import Placement
from typec_escape import tap

EDA = HERE / "eda/NXT-M3-R14.kicad_pcb"
BASE = SYS / "eda/NXT-M3-R11.kicad_pcb"
OUT = HERE / "evidence/pcb"
FOOTPRINTS = route.CLI.parent.parent / "share/kicad/footprints"
ROUTING_LAYER = (pcb.F_Cu, pcb.B_Cu)
INPUTS = ("BTN1", "BTN2", "AUX1", "AUX2")
CATHODE = {"Q1": (60.5, 115.0, 90), "R100": (57.4, 117.5, 0), "R200": (60.5, 119.25, 0)}

PLACEMENT = {
    "J5": (63.0, 89.0, 0, 0), "J6": (65.0, 56.75, 180, 0),
    "R508": (74.0, 87.3, 90, 1), "D14": (71.5, 88.3, 180, 1),
    "R509": (64.5, 61.75, 0, 0), "R510": (66.0, 63.75, 0, 0),
    "D15": (64.75, 59.75, 180, 0), "C64": (62.0, 63.75, 0, 0), "Q35": (65.0, 65.0, 90, 0),
}
for i in range(4):
    PLACEMENT[f"R{500+i}"] = (73.0, 78.6 - i * 1.65, 0, 1)
    PLACEMENT[f"R{504+i}"] = (76.6, 78.6 - i * 1.65, 0, 1)
    PLACEMENT[f"C{60+i}"] = (80.2, 78.6 - i * 1.65, 0, 1)
    PLACEMENT[f"D{10+i}"] = (60.0 + i * 2.2, 92.0, 0, 1)


def uuid(item):
    return str(item.m_Uuid.AsString())


def insert(board):
    netlist = ET.parse(OUT / "netlist.xml")
    parts = {c.get("ref"): c for c in netlist.findall("./components/comp")}
    existing = {f.GetReference(): f for f in board.GetFootprints()}
    if set(PLACEMENT) & existing.keys():
        raise ValueError("New references collide with the frozen PCB")
    house = parts["U3"].find("sheetpath").get("tstamps")
    prefix = existing["U3"].GetPath().AsString()
    root = prefix.split("/")[1]
    assert house.strip("/") in prefix
    nets = {}
    for net in netlist.findall("./nets/net"):
        name = net.get("name")
        if board.FindNet(name) is None:
            board.Add(pcb.NETINFO_ITEM(board, name))
        for node in net.findall("node"):
            nets[node.get("ref"), node.get("pin")] = name
    for pad in existing["U3"].Pads():
        name = nets.get(("U3", pad.GetNumber()))
        if name in {f"{signal}_GPIO" for signal in INPUTS}:
            pad.SetNet(board.FindNet(name))
    placement = Placement(board, CATHODE)
    picked = {}
    for ref, anchor in PLACEMENT.items():
        part = parts[ref]
        fid = part.findtext("footprint")
        lib, name = fid.split(":")
        fp = pcb.FootprintLoad(str(FOOTPRINTS / f"{lib}.pretty"), name)
        if fp is None:
            raise ValueError(fid)
        fp.SetFPIDAsString(fid)
        fp.SetReference(ref)
        fp.SetValue(part.findtext("value"))
        fp.SetFields({name: part.findtext(f'./fields/field[@name="{name}"]') or ""
                      for name in ("MPN", "Status", "Datasheet")})
        for name in ("MPN", "Status", "Datasheet"):
            fp.GetField(name).SetVisible(False)
        fp.Value().SetVisible(False)
        if part.find('property[@name="dnp"]') is not None:
            fp.SetAttributes(fp.GetAttributes() | pcb.FP_DNP)
        folder = part.find("sheetpath").get("tstamps").strip("/")
        fp.SetPath(pcb.KIID_PATH(f"/{root}/{folder}/{part.findtext('tstamps')}"))
        board.Add(fp)
        for pad in fp.Pads():
            pad.SetNet(board.FindNet(nets[ref, pad.GetNumber()]))
        picked[ref] = placement.choose(fp, anchor)
        fp.Reference().SetLayer(pcb.B_Fab if fp.GetLayer() == pcb.B_Cu else pcb.F_Fab)
    # Remove obsolete base routing before moving R100/R200. No other net is ripped up.
    removed = []
    gnd_sites = {tuple(pad.GetPosition()) for ref in CATHODE for pad in existing[ref].Pads()
                 if pad.GetNetname() == "GND"}
    for item in list(board.GetTracks()):
        if item.GetNetname() == "BASE_00":
            removed.append(uuid(item))
            board.Remove(item)
        elif item.GetNetname() == "GND" and any(
                tuple(end) == pos for end in (item.GetStart(), item.GetEnd()) for pos in gnd_sites):
            raise ValueError("Unexpected pre-existing Q1 ground route")
    for ref, target in CATHODE.items():
        picked[ref] = placement.choose(existing[ref], (*target, 1), move=True)
    for ref, label, dx, dy in (("J5", "J_BTN", -1.5, -3.4), ("J6", "HV STOP", -6.25, 4.75)):
        fp = board.FindFootprintByReference(ref)
        silk = pcb.PCB_TEXT(board)
        silk.SetText(label)
        silk.SetTextSize(route.vec(.85, .85))
        silk.SetTextThickness(pcb.FromMM(.15))
        x, y = route.pos(fp)
        silk.SetPosition(route.vec(x+dx, y+dy))
        silk.SetLayer(pcb.B_SilkS if fp.GetLayer() == pcb.B_Cu else pcb.F_SilkS)
        silk.SetMirrored(fp.GetLayer() == pcb.B_Cu)
        board.Add(silk)
    (OUT / "placement.json").write_text(json.dumps(picked, indent=2) + "\n", encoding="utf-8")
    return removed


def design_for(board):
    class LocalDraft(route.Draft):
        def anchors(self, entry, block):
            _, item, layers = entry
            l, t, r, b = route.box(item)
            x, y = route.pos(item)
            j, k = route.idx(x, y)
            return [(p, q, z) for z in layers for p in range(j-5, j+6) for q in range(k-5, k+6)
                    if 0 <= p < route.NX and 0 <= q < route.NY and not block[z][q][p]
                    and abs(route.mm(p, q)[0]-x) <= .46*(r-l)
                    and abs(route.mm(p, q)[1]-y) <= .46*(b-t)]
    design = LocalDraft(board)
    for item in board.GetTracks():
        via = isinstance(item, pcb.PCB_VIA)
        layers = (0, 1) if via else (ROUTING_LAYER.index(item.GetLayer()),)
        design.obstacles.append((item.GetNetname(), layers, route.box(item), "via" if via else "track"))
    return design


def routing_jobs(design):
    def between(net, a, b):
        side_a = [entry for entry in design.pads[net] if entry[0] == a]
        side_b = [entry for entry in design.pads[net] if entry[0] == b]
        candidates = sorted((math.dist(route.pos(x[1]), route.pos(y[1])), i, j)
                            for i, x in enumerate(side_a) for j, y in enumerate(side_b))
        return net, [(side_a[i], side_b[j]) for _, i, j in candidates]

    yield between("BASE_00", "R100", "R200")
    yield between("BASE_00", "Q1", "R100")
    yield between("BASE_00", "Q1", "R200")
    yield between("GND", "Q1", "R200")
    yield between("GND", "R200", "SW1")
    yield between("DRV_00", "R100", "U20")
    yield between("K1_0", "Q1", "V1")
    yield between("LATCH_CLR_N", "U9", "U8")
    yield between("ARMED", "U8", "R26")
    yield between("ARM_STROBE", "J4", "U8")
    yield between("RESIDUAL_OK", "U8", "R28")
    for i, signal in enumerate(INPUTS):
        yield between(f"{signal}_GPIO", "U3", f"R{500+i}")
        yield between(f"{signal}_GPIO", f"R{500+i}", f"R{504+i}")
        yield between(f"{signal}_GPIO", f"R{504+i}", f"C{60+i}")
        yield between(signal, "J5", f"D{10+i}")
        yield between(signal, f"D{10+i}", f"R{500+i}")
    for net, pairs in {
        "STOP_LOOP": [("J6","D15"), ("J6","R509")],
        "STOP_GATE": [("R509","Q35"), ("R510","Q35"), ("Q35","C64")],
        "FAULT_N": [("Q35","U9"), ("U9","TP8"), ("U9","R27")],
        "AUX_FEED": [("R508","D14")],
        "3V3_AUX": [("J5","D14")],
        "3V3": [("R510","C21"), ("R508","C50"), ("R504","C10"),
                ("R504","R505"), ("R505","R506"), ("R506","R507")],
        "GND": [("J6","D15"), ("D15","Q35"), ("C64","Q35"), ("Q35","C21"),
                ("J5","D10"), ("D10","D11"), ("D11","D12"), ("D12","D13"),
                ("D13","C50"), ("J5","C50"), ("C60","C61"), ("C61","C62"),
                ("C62","C63"), ("C63","C10")],
    }.items():
        for a, b in pairs:
            yield between(net, a, b)

    # Tie the local sink to the closest existing PCB ground via or pad reachable by the router.
    for ref in ("Q1",):
        a = next(entry for entry in design.pads["GND"] if entry[0] == ref)
        existing = [entry for entry in design.pads["GND"]
                    if entry[0] not in set(CATHODE) | set(PLACEMENT)]
        yield "GND", [(a, b) for b in sorted(existing,
                                             key=lambda e: math.dist(route.pos(a[1]), route.pos(e[1])))[:5]]


def check(board, stem):
    pcb.SaveBoard(str(EDA), board)
    command = [str(route.CLI), "pcb", "drc", "--refill-zones", "--save-board", "--schematic-parity",
               "--severity-all", "--format", "json", "--exit-code-violations",
               "-o", str(OUT / f"{stem}.json"), str(EDA)]
    proc = subprocess.run(command, capture_output=True)
    if proc.returncode not in (0, 5):
        raise RuntimeError(f"KiCad DRC exit {proc.returncode}: {proc.stderr!r}")
    return json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8-sig"))


def main():
    route.STEP, route.NX, route.NY = .125, 1041, 641
    board = pcb.LoadBoard(str(BASE))
    removed = insert(board)
    before = check(board, "placement_drc")
    board = pcb.LoadBoard(str(EDA))
    design = design_for(board)
    missed = []
    for net, pairs in routing_jobs(design):
        if not pairs:
            raise ValueError(f"No pads for {net}")
        for a, b in pairs:
            size = len(design.saved)
            design.route(net, a, b, 90_000)
            if len(design.saved) > size:
                break
        else:
            missed.append([net, pairs[0][0][0], pairs[0][1][0]])
    first_route = check(board, "routing_first_drc")
    copper = {uuid(item): item for f in board.GetFootprints() for item in f.Pads()}
    copper.update({uuid(item): item for item in board.GetTracks()})
    targeted = {signal for signal in INPUTS} | {f"{signal}_GPIO" for signal in INPUTS}
    targeted |= {"ARMED", "ARM_STROBE", "LATCH_CLR_N", "RESIDUAL_OK", "FAULT_N",
                 "STOP_LOOP", "STOP_GATE", "BASE_00", "K1_0", "DRV_00"}
    for opening in first_route["unconnected_items"]:
        a, b = opening["items"]
        start, end = copper.get(a["uuid"]), copper.get(b["uuid"])
        if start is None or end is None or start.GetNetname() not in targeted:
            continue
        net = start.GetNetname()
        design.route(net, tap(start, a["pos"], board), tap(end, b["pos"], board), 120_000)
    draft = check(board, "routing_drc")
    key = lambda e: (e["type"], *sorted(i["uuid"] for i in e["items"]))
    old = {key(issue) for issue in before["violations"]}
    bad = {i["uuid"] for issue in draft["violations"] if key(issue) not in old for i in issue["items"]}
    kept, discarded = [], []
    for net, a, b, items in design.saved:
        ids = [uuid(item) for item in items]
        if bad.intersection(ids):
            discarded.append([net, a, b, ids])
            for item in items:
                board.Remove(item)
        else:
            kept.append([net, a, b, ids])
    final = check(board, "settled_drc")
    actual = {key(issue) for issue in final["violations"]}
    if not actual.issubset(old):
        print("Review post-refill differences", len(actual - old), flush=True)
    summary = {"removed_old_base_segments": removed, "retained_routes": kept, "drc_rolled_back": discarded,
               "no_path": missed, "unconnected": len(final["unconnected_items"]),
               "violation_types": collections.Counter(i["type"] for i in final["violations"]),
               "parity": collections.Counter(i["type"] for i in final["schematic_parity"])}
    (OUT / "routing.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print({k: len(v) if isinstance(v, list) else v for k, v in summary.items()}, flush=True)


if __name__ == "__main__":
    main()
