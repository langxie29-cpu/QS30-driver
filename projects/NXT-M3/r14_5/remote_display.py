"""Lay out the display bank for sockets mounted on the external plastic panel."""
import argparse
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5

import pcbnew as pcb

from route_board import BoardRouter, HERE, STEM, channel_pairs, point, uid, xy

LIB = "R14_5"
LAND = "Remote_Tube_11_SMD"
OLD = "R10_R10:GZC13F_HandWire_11_SMD"
REMOVED_MOUNTS = {f"MH{n}{side}" for n in range(5,8) for side in ("L","R")}
FIRST_X = (63.5, 99.0, 136.5)
PITCH = 7.5
UPPER_Q_Y = 107.25
LOWER_Q_Y = 120.75
PIN_ORDER = (3,13,12,11,10,9,7,6,5,4)


def ident(label):
    return pcb.KIID(str(uuid5(NAMESPACE_URL,f"QS30-driver/R14.5/remote/{label}")))


def cell(number):
    i = number - 1
    group, digit = divmod(i,10)
    x = FIRST_X[group] + (digit % 5) * PITCH
    y = UPPER_Q_Y if digit < 5 else LOWER_Q_Y
    return group,digit,x,y


def library(eda):
    dest = eda / f"{LIB}.pretty"
    dest.mkdir(exist_ok=True)
    pads = [(1,-7.5,-9.75,"A")]
    for digit,pin in enumerate(PIN_ORDER):
        pads.append((pin,(digit%5-2)*PITCH,-4.5 if digit<5 else 9.0,str(digit)))
    lines = [f'(footprint "{LAND}" (version 20241229) (generator pcbnew)',
             '  (layer "F.Cu") (attr smd exclude_from_pos_files)',
             '  (fp_text reference "REF**" (at -15 -8) (layer "F.Fab")'
             ' (effects (font (size 1 1) (thickness .15))))',
             f'  (fp_text value "{LAND}" (at 0 12) (layer "F.Fab")'
             ' (effects (font (size 1 1) (thickness .15))))']
    for pin,x,y,text in pads:
        # TOP_BOTTOM flip reflects the original front-pad y coordinate.
        lines += [f'  (pad "{pin}" smd roundrect (at {x} {-y}) (size 1.8 2.6)'
                  ' (layers "F.Cu" "F.Mask") (roundrect_rratio .2))',
                  f'  (fp_text user "{text}" (at {x} {-y-2.1}) (layer "F.SilkS")'
                  ' (effects (font (size .8 .8) (thickness .13))))']
    (dest / f"{LAND}.kicad_mod").write_text("\n".join(lines + [")",""]),encoding="utf-8")
    table = eda / "fp-lib-table"
    old = table.read_text(encoding="utf-8").rstrip()
    entry = f' (lib (name "{LIB}") (type "KiCad") (uri "$' + (
        f'{{KIPRJMOD}}/{LIB}.pretty") (options "") (descr "R14.5 remote display cable lands"))')
    if f'(name "{LIB}")' not in old:
        table.write_text(old[:-1]+"\n"+entry+"\n)\n",encoding="utf-8")
    sch = eda / "Tube_interfaces.kicad_sch"
    data = sch.read_text(encoding="utf-8")
    if OLD in data:
        assert data.count(OLD)==3
        sch.write_text(data.replace(OLD,f"{LIB}:{LAND}"),encoding="utf-8")
    return dest


def replace_tube(board,old,path,group):
    new = pcb.FootprintLoad(str(path), LAND)
    assert new is not None
    ref = old.GetReference()
    new.SetUuidDirect(old.m_Uuid)
    new.SetFPID(pcb.LIB_ID(LIB,LAND))
    new.SetPath(old.GetPath())
    new.SetSheetname(old.GetSheetname())
    new.SetSheetfile(old.GetSheetfile())
    new.SetReference(ref)
    new.SetValue(old.GetValue())
    new.SetAttributes(old.GetAttributes())
    for f in old.GetFields():
        name = f.GetName()
        if name not in {"Reference","Value","KiLib_Generator"}:
            new.SetField(name,f.GetText())
            new.GetField(name).SetVisible(False)
    for i,graphic in enumerate(new.GraphicalItems()):
        graphic.SetUuidDirect(ident(f"{ref}/graphic/{i}"))
    for field in new.GetFields():
        field.SetUuidDirect(ident(f"{ref}/field/{field.GetName()}"))
    pads = {p.GetNumber():p for p in old.Pads()}
    board.Add(new)
    new.Flip(new.GetPosition(),pcb.FLIP_DIRECTION_TOP_BOTTOM)
    new.SetOrientation(pcb.EDA_ANGLE(0,pcb.DEGREES_T))
    new.SetPosition(point(FIRST_X[group]+2*PITCH,UPPER_Q_Y))
    for p in new.Pads():
        old_pad = pads[p.GetNumber()]
        p.SetUuidDirect(old_pad.m_Uuid)
        p.SetNet(old_pad.GetNet())
        p.SetPinFunction(old_pad.GetPinFunction())
        p.SetPinType(old_pad.GetPinType())
        if p.GetNumber()=="1":
            expected = (FIRST_X[group]+PITCH,UPPER_Q_Y-9.75)
        else:
            _,_,x,y = cell(group*10+PIN_ORDER.index(int(p.GetNumber()))+1)
            expected = (x,y-4.5)
        assert xy(p.GetPosition())==expected,(ref,p.GetNumber(),xy(p.GetPosition()),expected)
    board.RemoveNative(old)


def detach_display_copper(board):
    tracks = list(board.GetTracks())
    for t in tracks:
        net = t.GetNetname()
        is_via = isinstance(t,pcb.PCB_VIA)
        x,y = xy(t.GetPosition() if is_via else t.GetStart())
        u,v = (x,y) if is_via else xy(t.GetEnd())
        expired_ground_via = net == "GND" and is_via and (x,y) in {
            (61.5,119.75),(64.75,116.5),(167.75,120.25)}
        if net == "ANODE_1" or expired_ground_via:
            board.RemoveNative(t)
        elif net.startswith("BASE_") or re.fullmatch(r"K[1-3]_[0-9]",net):
            board.RemoveNative(t)
        elif net.startswith("DRV_") and max(y,v)>96.5:
            if is_via or min(y,v)>=96.5:
                board.RemoveNative(t)
            else:
                directed = y<v
                a,b = (x,y) if directed else (u,v)
                c,d = (u,v) if directed else (x,y)
                edge = point(a+(c-a)*(96.5-b)/(d-b),96.5)
                if directed:
                    t.SetEnd(edge)
                else:
                    t.SetStart(edge)
        elif net=="GND" and not is_via and t.GetLayer()==pcb.B_Cu and (
                min(x,u)>=60 and max(x,u)<=170 and min(y,v)>=98):
            board.RemoveNative(t)


def place(path):
    lib = library(path.parent)
    raw = pcb.LoadBoard(str(path))
    refs = {f.GetReference():f for f in raw.GetFootprints()}
    for r in REMOVED_MOUNTS:
        raw.RemoveNative(refs[r])
    for zone in list(raw.Zones()):
        if zone.GetZoneName().split(" / ")[0] in REMOVED_MOUNTS:
            raw.RemoveNative(zone)
    detach_display_copper(raw)
    refs["TP1"].SetPosition(point(70.75,67.0))
    for group in range(3):
        replace_tube(raw,refs[f"V{group+1}"],lib,group)
    for number in range(1,31):
        _,_,x,y = cell(number)
        q,feed,pull = (refs[r] for r in (f"Q{number}",f"R{99+number}",f"R{199+number}"))
        if not feed.IsFlipped():
            feed.Flip(feed.GetPosition(),pcb.FLIP_DIRECTION_TOP_BOTTOM)
        for f,u,v,direction in ((q,x,y,90),(feed,x+1.70,y+3.5,90),
                                (pull,x-.65,y+3.5,180)):
            f.SetOrientation(pcb.EDA_ANGLE(direction,pcb.DEGREES_T))
            f.SetPosition(point(u,v))
    assert pcb.SaveBoard(str(path),raw)


def run_stage(path, stage):
    b = BoardRouter(path)
    if stage == "cathodes":
        for number in range(1,31):
            pairs = channel_pairs(number,b)
            for idx in (5,1,2,3):
                label,a,c = pairs[idx]
                b.pair(f"Q{number} {label}",a,c,margin=3,limit=50000)
        for line in ([*range(first,first+5)] for first in range(1,31,5)):
            for a,c in zip(line,line[1:]):
                b.pair("return row",f"R{199+a}.2",f"R{199+c}.2",margin=2,limit=50000)
        for tube in range(1,4):
            top = 1+(tube-1)*10
            b.pair("return row join",f"R{199+top}.2",f"R{204+top}.2",margin=4,limit=100000)
        for tube,resistor in enumerate(("R303","R305","R307"),1):
            b.pair("remote tube anode",f"V{tube}.1",f"{resistor}.2",margin=11,limit=200000)
    if stage == "drivers":
        for n in range(1,31):
            pairs = channel_pairs(n,b)
            for idx in (4,0):
                label,a,c = pairs[idx]
                if not b.pair(f"Q{n} {label}",a,c,margin=14,limit=450000):
                    print(f"Remaining driver corridor: Q{n} {label}",flush=True)
    b.save(path)
    return b.events


def controller_trials(path):
    raw = pcb.LoadBoard(str(path))
    refs = {f.GetReference():f for f in raw.GetFootprints()}
    for ref,x,y in (("U20",81,94.75),("U21",97,94.5),("TP1",72,68)):
        refs[ref].SetPosition(point(x,y))
    assert pcb.SaveBoard(str(path),raw)

    b = BoardRouter(raw)
    # Reconnect the real register ground before checking all six channel pairs.
    for n in (4,8,3,7,2,5,6,1,*range(9,17)):
        channel = channel_pairs(n,b)
        for idx in (4,0):
            name,a,c = channel[idx]
            b.pair(f"Q{n} {name} after register move",a,c,margin=14,limit=450000,via_size=.50)
    for label,a,c in (
        ("clear tree","U20.10","R30.2"), ("clear tree","U21.10","U20.10"),
        ("clock tree","U20.11","R32.2"), ("clock tree","U21.11","U20.11"),
        ("latch tree","U20.12","R33.2"), ("latch tree","U21.12","U20.12"),
        ("oe tree","U20.13","U22.13"), ("oe tree","U21.13","U22.13"),
        ("serial chain","U20.14","R31.2"), ("serial chain","U20.9","U21.14"),
        ("serial chain","U21.9","U22.14"),
        ("driver power","U20.16","C21.1"), ("driver power","U21.16","C22.1"),
        ("driver return","U20.8","C21.2"), ("driver return","U21.8","C22.2"),
    ):
        # Paired schematic nodes may already share native copper.
        b.pair(label,a,c,margin=12,limit=300000,via_size=.50)
    b.save(path)
    return b.events


def fanout_north_row(board, ref):
    """Reserve plated escapes under the body before any north-row trunk crosses it."""
    import math
    import numpy as np
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree

    pads = [board.pads(f"{ref}.{n}")[0] for n in range(9,17)]
    locations = {}
    for pad in pads:
        px,py = xy(pad.GetPosition())
        xs = np.arange(round((px-.10)*20), round((px+.10)*20)+1)/20
        ys = np.arange(math.ceil((py+.9)*20), math.floor((py+3.15)*20)+1)/20
        _,via_ok,exclude = board.maps(pad.GetNetname(),.20,xs,ys,0,.50)
        obstacles = STRtree(exclude[1])
        choices = []
        for j,y in enumerate(ys):
            for i,x in enumerate(xs):
                if not via_ok[j,i]:
                    continue
                end = (float(x),float(y))
                ray = LineString(((px,py),end))
                if len(obstacles.query(ray,predicate="intersects")):
                    continue
                choices.append((float(math.dist((px,py),end)),end,ray,Point(end)))
        locations[pad.GetNumber()] = sorted(choices,key=lambda c:(c[0],c[1]))
    print("NORTH ROW FANOUT",ref,{p:len(v) for p,v in locations.items()},flush=True)

    def compatible(a,b):
        return (a[3].distance(b[3]) >= .708 and a[3].distance(b[2]) >= .558
                and b[3].distance(a[2]) >= .558 and a[2].distance(b[2]) >= .408)

    def choose(pending, plan):
        if not pending:
            return plan
        pin = min(pending,key=lambda n:len(pending[n]))
        for trial in pending[pin]:
            rest = {n:[v for v in values if compatible(v,trial)]
                    for n,values in pending.items() if n!=pin}
            if all(rest.values()):
                result = choose(rest,{**plan,pin:trial})
                if result:
                    return result
        return None

    usable = {p:opts for p,opts in locations.items() if opts}
    placement = choose(usable,{})
    if not placement:
        return []
    events = []
    for pad in pads:
        pin = pad.GetNumber()
        if pin not in placement:
            continue
        _,end,_,_ = placement[pin]
        track = pcb.PCB_TRACK(board.board)
        track.SetStart(pad.GetPosition())
        track.SetEnd(point(*end))
        track.SetLayer(pcb.B_Cu)
        track.SetWidth(pcb.FromMM(.20))
        via = pcb.PCB_VIA(board.board)
        via.SetPosition(point(*end))
        via.SetViaType(pcb.VIATYPE_THROUGH)
        via.SetLayerPair(pcb.F_Cu,pcb.B_Cu)
        via.SetWidth(pcb.FromMM(.50))
        via.SetDrill(pcb.FromMM(.30))
        objects = []
        for name, obj in (("trace",track),("via",via)):
            obj.SetUuidDirect(ident(f"{ref}/{pin}/fanout/{name}"))
            obj.SetNet(board.board.FindNet(pad.GetNetname()))
            board.board.Add(obj)
            board.record(obj)
            objects.append(uid(obj))
        events.append(dict(label=f"{ref}.{pin} north row escape",net=pad.GetNetname(),
                           committed=True,objects=objects,attempts=[],
                           left=[(uid(pad),xy(pad.GetPosition()))],right=[(uid(via),end)]))
    board.sync()
    return events


def fix_controller_fanout(path, records):
    raw = pcb.LoadBoard(str(path))
    labels = ("clock tree U20", "oe tree U20", "clear tree U21", "driver power U20",
              "Q1 drive after register move", "serial chain U20.9")
    replace = {item for event in records if event["label"].startswith(labels)
               for item in event["objects"]}
    for t in list(raw.GetTracks()):
        if uid(t) in replace:
            raw.RemoveNative(t)
    b = BoardRouter(raw)
    b.events.extend(fanout_north_row(b,"U20"))
    for label,a,c in (
        ("latch source","U20.12","R36.1"), ("latch peer","U21.12","R36.1"),
        ("serial source","U20.14","R31.2"), ("serial cascade","U21.9","U22.14"),
        ("clock source","U20.11","R32.2"), ("clock peer","U21.11","U20.11"),
        ("blanking enable","U20.13","U22.13"), ("clear source","U20.10","R30.2"),
        ("clear peer","U21.10","U20.10"), ("driver power","U20.16","C21.1"),
        ("serial chain","U20.9","U21.14"), ("Q1 drive","U20.15","R100.1"),
    ):
        b.pair(label,a,c,margin=12,limit=250000,via_size=.50)
    b.save(path)
    return b.events


def finish_display(path):
    raw = pcb.LoadBoard(str(path))
    refs = {f.GetReference():f for f in raw.GetFootprints()}
    for ref,x,y in (("TP1",72.5,60.5),("C21",85.725,90.6375),("C22",101.475,91.1375)):
        refs[ref].SetPosition(point(x,y))
    b = BoardRouter(raw)
    for label,a,c in (
        ("restore BUCK_PG test pad","TP1.1","U2.8"),
        ("local decoupling","U20.16","C21.1"), ("local decoupling","U21.16","C22.1"),
        ("local decoupling return","U20.8","C21.2"), ("local decoupling return","U21.8","C22.2"),
        ("595 serial cascade","U21.9","U22.14"), ("595 serial cascade","U22.9","U23.14"),
        ("595 clear bus","U20.10","R30.2"), ("595 clear bus","U22.10","R30.2"),
        ("595 clear bus","U23.10","R30.2"), ("595 clock","U22.11","R32.2"),
        ("595 clock","U23.11","R32.2"), ("595 latch","U23.12","R33.2"),
        ("595 clock input","R32.1","U3.5"), ("595 latch input","R33.1","U3.6"),
    ):
        b.pair(label,a,c,margin=8 if "decoupling" in label or "test pad" in label else 13,
               limit=220000,via_size=.50)
    b.save(path)
    return b.events


def main():
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("place","cathodes","drivers","controllers","fanout","finish"))
    p.add_argument("--out",type=Path,default=HERE)
    args = p.parse_args()
    path = args.out / "eda" / f"{STEM}.kicad_pcb"
    if args.stage == "place":
        place(path)
    else:
        if args.stage == "controllers":
            events = controller_trials(path)
        elif args.stage == "fanout":
            source = args.out/"evidence/routing-remote-controllers.json"
            events = fix_controller_fanout(path,json.loads(source.read_text(encoding="utf-8")))
        elif args.stage == "finish":
            events = finish_display(path)
        else:
            events = run_stage(path,args.stage)
        (args.out/"evidence"/f"routing-remote-{args.stage}.json").write_text(
            json.dumps(events,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
