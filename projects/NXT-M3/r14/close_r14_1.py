"""Close and audit the first cathode and the hardware STOP on the frozen R14 board."""
import io
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pcbnew as pcb

from route_r14_1 import LAYERS, Raster, point, xy
import lands_r14_1
import latch_r14_1
import blanking_r14_1

HERE = Path(__file__).resolve().parent
BASE = "d203259673981fc9dc7dcc8ede4780305f21c041"
STEM = "NXT-M3-R14"
CLI = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin")) / "kicad-cli.exe"
WORK = HERE / os.environ.get("R14_1_WORK", "r14_1.tmp")
EVIDENCE = HERE / "evidence/r14_1"
CORE = ("FAULT_N", "LATCH_CLR_N", "RESIDUAL_OK", "ARMED", "ARM_STROBE", "STOP_LOOP", "STOP_GATE",
        "DRV_00", "BASE_00", "K1_0", "PWM_PERMIT", "DRIVE_OK", "OE_SINK", "HC_OE_N")
SUPPORT = ("DIGITS_REQ", "HV_READY", "MCU_EN", "BIAS_OK", "HV_ISOLATE_IN", "5V_HV",
           "CUT_OVLO", "CUT_PGTH", "CUT_ILM", "CUT_DVDT", "CUT_TIMER")
GROUND = (("Q1","2","R200","2"), ("Q1","2","U20","8"))
TARGET_GROUND = {"Q1","R200","Q35","J6","D15","C64","U8","U9","U11","U10","U19","Q31"}


def uid(item):
    return str(item.m_Uuid.AsString())


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def uid_pair(issue):
    return issue["type"], *sorted(i["uuid"] for i in issue["items"])


def all_errors(data):
    return {uid_pair(i):i for i in data["violations"]}


def prepare():
    WORK.mkdir(exist_ok=True)
    target = WORK / "eda"
    source = f"{BASE}:projects/NXT-M3/r14/eda"
    archive = subprocess.check_output(["git","archive","--format=zip",source],cwd=HERE)
    with ZipFile(io.BytesIO(archive)) as package:
        package.extractall(target)
    return target


def check(eda, out, refill=False):
    args = [str(CLI),"pcb","drc","--severity-all","--schematic-parity","--exit-code-violations",
            "--format","json","-o",str(out)]
    if refill:
        args += ["--refill-zones","--save-board"]
    proc = subprocess.run([*args,str(eda)],capture_output=True)
    if proc.returncode not in (0,5):
        raise RuntimeError(proc.stderr or proc.stdout)
    return read(out)


def item_description(item):
    if isinstance(item,pcb.PAD):
        return f"{item.GetParentFootprint().GetReference()}.{item.GetNumber()}"
    return uid(item)


def pad(board, ref, pin):
    return next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber()==pin)


def anchor(item, position):
    if isinstance(item,(pcb.PAD,pcb.PCB_VIA)):
        return item
    return point(position["x"],position["y"]),LAYERS.index(item.GetLayer())


def route_board(board, report, nets, ground):
    raster = Raster(board)
    indexed = {uid(i):i for f in board.GetFootprints() for i in f.Pads()}
    indexed.update({uid(i):i for i in board.GetTracks()})
    jobs = {net:[] for net in nets}
    for issue in report["unconnected_items"]:
        left,right = issue["items"]
        a,b = indexed.get(left["uuid"]),indexed.get(right["uuid"])
        if a is None or b is None or a.GetNetname() != b.GetNetname():
            continue
        net = a.GetNetname()
        names = item_description(a),item_description(b)
        if net in jobs:
            jobs[net].append((anchor(a,left["pos"]),anchor(b,right["pos"]),names))
    if ground:
        jobs["GND"] = [(pad(board,a,p),pad(board,b,q),(f"{a}.{p}",f"{b}.{q}")) for a,p,b,q in GROUND]
    if "ARM_STROBE" in jobs:
        jobs["3V3"] = [(pad(board,a,p),pad(board,b,q),(f"{a}.{p}",f"{b}.{q}")) for a,p,b,q in
                       (("U8","8","R27","1"),("U8","7","U8","8"))]
        if ground:
            jobs["GND"].append((pad(board,"U8","4"),pad(board,"U9","3"),("U8.4","U9.3")))
    records = []
    for net,targets in jobs.items():
        for a,b,names in targets:
            added, anchors = raster.connect(net,a,b)
            if not added and net in {"FAULT_N","ARMED","HC_OE_N","GND"}:
                start = a if isinstance(a,pcb.PAD) else b
                if isinstance(start,pcb.PAD):
                    candidates = sorted((i for i in board.GetTracks() if isinstance(i,pcb.PCB_VIA)
                                         and i.GetNetname()==net),
                                        key=lambda i: (i.GetPosition()-start.GetPosition()).EuclideanNorm())
                    for i in candidates[:3]:
                        alternate, _ = raster.connect(net,start,i,65_000)
                        if alternate:
                            added = alternate
                            names = (item_description(start),uid(i))
                            break
            records.append((net,names,added,anchors))
            print(net,*names,"items",len(added),"anchors",anchors,flush=True)
    return records


def main():
    mode = sys.argv[1] if len(sys.argv)>1 else "all"
    root = WORK/"eda" if mode in {"finish","blank","cutoff","returns","prune"} else prepare()
    eda = root / f"{STEM}.kicad_pcb"
    if mode in {"finish","blank","cutoff","returns","prune"}:
        before = read(WORK/"baseline.json")
        entry = check(eda,WORK/"finish_entry.json")
        board = pcb.LoadBoard(str(eda))
        if mode=="blank":
            dump(WORK/"placements_blank.json",blanking_r14_1.move(board))
            pcb.SaveBoard(str(eda),board)
            entry = check(eda,WORK/"blank_before.json",refill=True)
        if mode in {"returns","prune"}:
            dropped = []
            for index in range(8):
                extra = all_errors(entry).keys()-all_errors(before).keys()
                dangling = {i["items"][0]["uuid"] for i in entry["violations"]
                            if i["type"] in {"track_dangling","via_dangling"} and uid_pair(i) in extra}
                if not dangling:
                    break
                dropped.extend(sorted(dangling))
                raw = eda.read_text(encoding="utf-8")
                match = re.compile(r"(?ms)^\t\((?:segment|via)\n.*?^\t\)\n")
                eda.write_text(match.sub(lambda m: "" if any(q in m.group() for q in dangling)
                                        else m.group(),raw),encoding="utf-8",newline="\n")
                entry = check(eda,WORK/"returns_before.json")
            dump(WORK/"pruned_stubs.json",dropped)
            if mode=="prune":
                return
            board = pcb.LoadBoard(str(eda))
        if mode=="cutoff":
            if board.FindFootprintByReference("U11").GetFPIDAsString() == "R10_R10:TI_RPW0010A":
                lands_r14_1.apply_cutoff(board,root)
            pcb.SaveBoard(str(eda),board)
            entry = check(eda,WORK/"cutoff_before.json",refill=True)
            added = all_errors(entry).keys()-all_errors(before).keys()
            if added:
                print("U11 tail placement rejected by native DRC",len(added),flush=True)
                return
        moves = follow_up(board,entry,mode)
        settle(board,eda,before,moves,mode)
        return
    before = check(eda,WORK/"baseline.json")
    board = pcb.LoadBoard(str(eda))
    if "latch" in mode:
        board, position, removed = latch_r14_1.apply(board,root,CLI.parent.parent/"share/kicad/footprints",
                                             HERE/"evidence/pcb/routing.json")
        print("U8",position,"disconnected branches",len(removed),flush=True)
    if "4" in mode:
        board.SetCopperLayerCount(4)
        for z in [*board.Zones(), *board.FindFootprintByReference("U3").Zones()]:
            if z.GetIsRuleArea():
                layers = z.GetLayerSet()
                layers.AddLayer(pcb.In1_Cu)
                layers.AddLayer(pcb.In2_Cu)
                z.SetLayerSet(layers)
    if "lands" in mode:
        lands_r14_1.apply(board,root,CLI.parent.parent/"share/kicad/footprints")
    if "q1" in mode:
        groups = ("BASE_00", "K1_0", "DRV_00")
    else:
        groups = CORE if "core" in mode else SUPPORT if "support" in mode else CORE+SUPPORT
    pcb.SaveBoard(str(eda),board)
    entry = check(eda,WORK/"prepared.json",refill=True)
    moves = route_board(board,entry,groups,"support" not in mode)
    settle(board,eda,before,moves,"routes")


def follow_up(board, report, mode):
    raster = Raster(board)
    indexed = {uid(i):i for f in board.GetFootprints() for i in f.Pads()}
    indexed.update({uid(i):i for i in board.GetTracks()})
    records = []

    def component_anchors(item, where):
        candidates = [anchor(item,where)]
        for related in board.GetConnectivity().GetConnectedItems(item):
            if uid(related) not in indexed:
                continue
            member = indexed[uid(related)]
            if isinstance(member,pcb.PCB_TRACK) and not isinstance(member,pcb.PCB_VIA):
                z = LAYERS.index(member.GetLayer())
                candidates.extend([(member.GetStart(),z),(member.GetEnd(),z)])
            else:
                candidates.append(member)
        return candidates

    pairs = []
    if mode=="returns":
        targets = (("U8","4","J6","2"),("Q31","2","R25","2"),("U11","8","C27","2"),
                   ("U11","8","C25","2"),("U15","5","U10","5"),("U10","3","J6","2"),
                   ("U19","3","J6","2"),("Q31","2","J6","2"))
        for left,lp,right,rp in targets:
            items = []
            for ref,pin in ((left,lp),(right,rp)):
                item = pad(board,ref,pin)
                x,y = xy(item.GetPosition())
                items.append({"uuid":uid(item),"pos":{"x":x,"y":y}})
            pairs.append({"items":items})
    else:
        pairs = report["unconnected_items"]
    for issue in pairs:
        a,b = issue["items"]
        left,right = indexed.get(a["uuid"]),indexed.get(b["uuid"])
        if left is None or right is None:
            continue
        net = left.GetNetname()
        refs = {item_description(i).split(".")[0] for i in (left,right)}
        if mode=="cutoff":
            if net not in {"5V_HV","HV_ISOLATE_IN","CUT_OVLO","CUT_ILM","CUT_TIMER"}:
                continue
        elif mode=="blank":
            wanted = {"OE_SINK","HC_OE_N","PWM_PERMIT","ARMED","BIAS_OK",
                      "FAULT_N","RESIDUAL_OK","LATCH_CLR_N"}
            if net not in wanted and not (net in ("GND","3V3") and refs & set(blanking_r14_1.TARGETS)):
                continue
        elif mode!="returns" and net not in CORE+SUPPORT:
            continue
        board.BuildConnectivity()
        if uid(right) in {uid(i) for i in board.GetConnectivity().GetConnectedItems(left)}:
            continue
        names = item_description(left),item_description(right)
        items, anchors = raster.connect(net,component_anchors(left,a["pos"]),
                                        component_anchors(right,b["pos"]),260_000)
        records.append((net,names,items,anchors))
        print("component",net,*names,"items",len(items),"anchors",anchors,flush=True)
    return records


def settle(board,eda,before,moves,name):
    pcb.SaveBoard(str(eda),board)
    routed = check(eda,WORK/"routed.json",refill=True)
    new = all_errors(routed).keys()-all_errors(before).keys()
    bad = {item for signature in new for item in signature[1:]}
    rolled_back = []
    results = []
    for net,names,items,anchors in moves:
        ids = [uid(i) for i in items]
        failed = bool(bad.intersection(ids))
        if failed:
            for i in items:
                board.Remove(i)
            rolled_back.append([net,names,ids])
        results.append({"net":net,"endpoints":names,"anchors":anchors,"items":ids,"rolled_back":failed})
    if rolled_back:
        pcb.SaveBoard(str(eda),board)
    candidate = check(eda,WORK/"candidate.json",refill=True)
    print("raw/new",len(routed["violations"]),len(new),"rollback",len(rolled_back),"final/new",
          len(candidate["violations"]),len(all_errors(candidate).keys()-all_errors(before).keys()),
          "unconnected",len(candidate["unconnected_items"]),flush=True)
    dump(WORK/f"{name}.json",results)


if __name__ == "__main__":
    main()
