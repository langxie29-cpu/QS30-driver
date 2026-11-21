"""Synchronize and route Type-C input changes without replacing the R11 layout."""
from collections import Counter
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pcbnew as pcb
import route
from typec_placement import Placement

HERE = Path(__file__).resolve().parent
OUT = HERE/"evidence/typec"
CLI = route.CLI
EDA = route.EDA
ROOT = "291289d0-40d1-520c-94bf-4c43df5338f6"
KLIB = Path(os.environ.get("KICAD10_FOOTPRINT_DIR",str(CLI.parent.parent/"share/kicad/footprints")))
POSITIONS = {
    "J1":(65.5,52.825,180), "U26":(118.0,60.5,0), "D5":(117.0,57.5,90),
    "R230":(84.0,69.0,0), "R231":(84.0,71.0,0), "R232":(87.2,71.0,0),
    "R233":(87.2,69.0,0), "R234":(121.5,59.5,90),
    "C52":(123.5,57.8,90), "C53":(114.0,60.5,0), "C54":(120.0,64.0,0),
    "Q33":(84.5,61.0,0), "Q34":(88.5,64.5,0),
}
USBNETS = ("USBC_CC1","USBC_CC2","USBC_1V2","USBC_2V7","USBC_VS","USBC_VALID_N","USBC_3A_N")


def drc(name, fill=False):
    flags = ["--refill-zones","--save-board"] if fill else []
    output = OUT/f"{name}.json"
    command = [str(CLI),"pcb","drc",*flags,"--schematic-parity","--all-track-errors",
               "--format","json","--exit-code-violations","-o",str(output),str(EDA)]
    result = subprocess.run(command,capture_output=True)
    output.with_suffix(".command.json").write_text(json.dumps(
        {"command":command,"exit":result.returncode,"output":result.stdout.decode("utf-8","replace"),
         "stderr":result.stderr.decode("utf-8","replace")},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if result.returncode not in (0,5):
        raise RuntimeError(command)
    return json.loads(output.read_text(encoding="utf-8-sig"))


def insert(board):
    root = ET.parse(OUT/"native_netlist.xml")
    parts = {c.get("ref"):c for c in root.findall("./components/comp")}
    existing = {f.GetReference():f for f in board.GetFootprints()}
    assert "U26" not in existing, "Start from the pre-Type-C R11 PCB"
    for net in root.findall("./nets/net"):
        name = net.get("name")
        if board.FindNet(name) is None:
            board.Add(pcb.NETINFO_ITEM(board,name))
    pin_map = {(n.get("ref"),n.get("pin")):net.get("name") for net in root.findall("./nets/net")
               for n in net.findall("node")}
    old = existing["J1"]
    old_returns = [pad.GetPosition() for pad in old.Pads() if pad.GetNetname()=="GND"]
    removed = []
    for track in list(board.GetTracks()):
        obsolete_vbus = track.GetNetname()=="5V_RAW"
        obsolete_return = not isinstance(track,pcb.PCB_VIA) and track.GetNetname()=="GND" and (
            track.GetStart() in old_returns or track.GetEnd() in old_returns)
        if obsolete_vbus or obsolete_return:
            removed.append(track.m_Uuid.AsString())
            board.Remove(track)
    board.Remove(old)
    placement = Placement(board)
    selected = {}
    for ref,anchor in POSITIONS.items():
        part = parts[ref]
        fid = part.findtext("footprint")
        lib,package = fid.split(":")
        fp = pcb.FootprintLoad(str(KLIB/f"{lib}.pretty"),package)
        assert fp is not None, fid
        fp.SetFPIDAsString(fid)
        fp.SetReference(ref)
        fp.SetValue(part.findtext("value"))
        fp.SetFields({name:part.findtext(f'./fields/field[@name="{name}"]') or ""
                      for name in ("MPN","Status","Datasheet")})
        for name in ("MPN","Status","Datasheet"):
            fp.GetField(name).SetVisible(False)
        fp.Value().SetVisible(False)
        folder = part.find("sheetpath").get("tstamps").strip("/")
        fp.SetPath(pcb.KIID_PATH(f"/{ROOT}/{folder}/{part.findtext('tstamps')}"))
        board.Add(fp)
        xy, side, angle = placement.choose(fp,anchor)
        selected[ref] = [*xy,board.GetLayerName(side),angle]
        fp.Reference().SetLayer(pcb.F_Fab if side==pcb.F_Cu else pcb.B_Fab)
        for pad in fp.Pads():
            number = pad.GetNumber()
            if number:
                assert (ref,number) in pin_map, (ref,number)
                pad.SetNet(board.FindNet(pin_map[ref,number]))
    (OUT/"placement_picks.json").write_text(json.dumps(selected,indent=2)+"\n",encoding="utf-8")
    print("Old input tracks removed:",len(removed),flush=True)
    return removed


def assign_classes():
    file = EDA.with_suffix(".kicad_pro")
    data = json.loads(file.read_text())
    settings = data["net_settings"]
    assignments = settings["netclass_patterns"]
    existing = {row["pattern"] for row in assignments}
    for name in USBNETS:
        cls = ("SAFETY_CONTROL" if name.endswith("_N") else "LOW_VOLTAGE_POWER"
               if name.endswith(("1V2","2V7")) else "DIGITAL_SIGNAL")
        if name not in existing:
            assignments.append({"pattern":name,"netclass":cls})
    file.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")


def schedule(draft):
    # Connection groups are built from the available pad locations to minimize detours.
    for net in ("5V_RAW",*USBNETS,"FRONT_EN","GND"):
        pad_entries = draft.pads[net]
        candidates = []
        for a,b in itertools.combinations(pad_entries,2):
            if a[0] not in POSITIONS and b[0] not in POSITIONS:
                continue
            distance = math.dist(route.pos(a[1]),route.pos(b[1]))
            if net=="GND" and distance>4:
                continue
            candidates.append((distance,a,b))
        connected = {}
        def root(node):
            while node in connected:
                node = connected[node]
            return node
        for _,a,b in sorted(candidates,key=lambda p:p[0]):
            first,second = (root(str(entry[1].m_Uuid.AsString())) for entry in (a,b))
            if first==second:
                continue
            count = len(draft.saved)
            draft.route(net,a,b,{"5V_RAW":185000,"GND":11000}.get(net,85000))
            if len(draft.saved)>count:
                connected[first] = second


def main():
    assign_classes()
    board = pcb.LoadBoard(str(EDA))
    removed = insert(board)
    pcb.SaveBoard(str(EDA),board)
    base = drc("pcb_typec_placement",fill=True)
    board = pcb.LoadBoard(str(EDA))
    route.STEP,route.NX,route.NY = .125,1041,641
    draft = route.Draft(board)
    for track in board.GetTracks():
        via = isinstance(track,pcb.PCB_VIA)
        layers = (0,1) if via else (route.LAYERS.index(track.GetLayer()),)
        draft.obstacles.append((track.GetNetname(),layers,route.box(track),"via" if via else "track"))
    schedule(draft)
    pcb.SaveBoard(str(EDA),board)
    pre = drc("pcb_typec_trial",fill=True)
    failures = {item["uuid"] for violation in pre["violations"] for item in violation["items"]}
    for paths in list(draft.saved):
        if any(str(item.m_Uuid.AsString()) in failures for item in paths[3]):
            for item in paths[3]:
                board.Remove(item)
            draft.saved.remove(paths)
    pcb.SaveBoard(str(EDA),board)
    final = drc("pcb_typec_final",fill=True)
    summary = {"removed_old_input_track_uuids":removed,
               "kept_new_paths":[{"net":net,"from":a,"to":b,"items":len(items)} for net,a,b,items in draft.saved],
               "placement_violations":dict(Counter(v["type"] for v in base["violations"])),
               "final_violations":dict(Counter(v["type"] for v in final["violations"])),
               "final_open_connections":len(final["unconnected_items"]),
               "final_parity":dict(Counter(v["type"] for v in final["schematic_parity"]))}
    (OUT/"pcb_typec_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
