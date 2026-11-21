"""Implement the R10 hand-wire mounting reference as native R11 copper and NPTH."""
import csv
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pcbnew as pcb

import route

HERE = Path(__file__).resolve().parent
REFERENCE = HERE/"socket_reference"
OUT = HERE/"evidence/socket_fit"
SCH = HERE/"eda/Tube_interfaces.kicad_sch"
LIB = "R10_R10"
FOOTPRINT = "GZC13F_HandWire_11_SMD"
FP_DIR = HERE/"eda"/f"{LIB}.pretty"
PROJECT_ROOT = "291289d0-40d1-520c-94bf-4c43df5338f6"
BRASS_RADIUS = 4
PIN = dict(zip("A0123456789",("1","3","13","12","11","10","9","7","6","5","4")))


def meta():
    return json.loads((REFERENCE/"socket-mechanics.json").read_text(encoding="utf-8-sig"))


def rows():
    with (REFERENCE/"handwire-pads.csv").open(encoding="utf-8-sig",newline="") as source:
        return list(csv.DictReader(source))


def coordinates(row):
    return float(row["x_mm_from_pcb_left"])+50, float(row["y_mm_from_pcb_top"])+50


def centers():
    return {f"V{i+1}":(77+38*i,102) for i in range(3)}


def capture():
    out = ['(footprint "'+FOOTPRINT+'"',
           '  (version 20241229) (generator pcbnew) (layer "F.Cu") (attr smd exclude_from_pos_files)',
           '  (fp_text reference "REF**" (at 0 -11.0) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))',
           '  (fp_text value "GZC13-F hand-wire pads" (at 0 12) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))']
    center = centers()["V1"]
    for row in rows():
        if row["tube"]!="V1":
            continue
        name = row["function"]
        x,y = (a-b for a,b in zip(coordinates(row),center))
        out.append(f'  (pad "{PIN[name]}" smd roundrect (at {x:g} {y:g}) (size 1.8 2.6)'
                   ' (layers "F.Cu" "F.Mask") (roundrect_rratio .20))')
        out.append(f'  (fp_text user "{name}" (at {x:g} {y+(2.15 if y>0 else -2.15):g}) (layer "F.SilkS")'
                   ' (effects (font (size .8 .8) (thickness .13))))')
    out.append(")")
    (FP_DIR/f"{FOOTPRINT}.kicad_mod").write_text("\n".join(out)+"\n",encoding="utf-8")
    old = SCH.read_text(encoding="utf-8")
    text = old.replace('QS30-1 / socket geometry TBD','QS30-1 / GZC13-F external hand-wire')
    text = text.replace('QS30-1 / used socket TBD','GZC13-F / used socket candidate')
    text = text.replace('SOCKET_GEOMETRY_TBD','HANDWIRE_ASSEMBLY_CANDIDATE')
    text = text.replace('Socket footprint, key and hole coordinates are TBD.',
                        'V1-V3 pads are hand-wire terminals; map the physical socket independently.')
    changed, hits = re.subn(
        r'(\(property "Value" "QS30-1 / GZC13-F external hand-wire"[^\n]*\n\(property "Footprint" )""',
        lambda match: match[1]+f'"{LIB}:{FOOTPRINT}"',text)
    if hits!=3:
        raise ValueError(f"Expected three socket references, found {hits}")
    SCH.write_text(changed,encoding="utf-8")


def distance(point, box):
    x,y = point
    l,t,r,b = box
    return math.hypot(max(l-x,0,x-r),max(t-y,0,y-b))



def actual_pads(footprint):
    return [p for p in footprint.Pads() if p.GetNetname() and not p.GetNetname().startswith("unconnected-")]


def at(xy):
    return route.vec(*xy)


def track_endpoints(track):
    if isinstance(track,pcb.PCB_VIA):
        return (route.pos(track),)
    return tuple((pcb.ToMM(point.x),pcb.ToMM(point.y)) for point in (track.GetStart(),track.GetEnd()))


def crosses_disk(track,point,radius):
    ends = track_endpoints(track)
    start = ends[0]
    end = ends[-1]
    u = end[0]-start[0],end[1]-start[1]
    squared = u[0]**2+u[1]**2
    scale = min(1,max(0,((point[0]-start[0])*u[0]+(point[1]-start[1])*u[1])/squared)) if squared else 0
    near = start[0]+scale*u[0],start[1]+scale*u[1]
    return math.dist(point,near) < radius+pcb.ToMM(track.GetWidth(pcb.F_Cu) if isinstance(track,pcb.PCB_VIA) else track.GetWidth())/2


def rule_area(board, name, point):
    zone=pcb.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetZoneName(name+" / socket fixing copper keepout")
    zone.SetLayerSet(pcb.LSET.AllCuMask())
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    outline=zone.Outline()
    outline.NewOutline()
    for i in range(64):
        angle=i*math.tau/64
        q=at((point[0]+BRASS_RADIUS*math.cos(angle),point[1]+BRASS_RADIUS*math.sin(angle)))
        outline.Append(q.x,q.y)
    board.Add(zone)


def populate():
    board = pcb.LoadBoard(str(route.EDA))
    old = {fp.GetReference():fp for fp in board.GetFootprints()}
    if set(centers())&set(old):
        raise ValueError("Start from the historical Type-C PCB")
    metadata = meta()
    holes={ref:(50+x,50+y) for ref,(x,y) in metadata["pcb_holes_mm"].items()}
    copper = [(p.GetNetname(),route.box(p)) for ref in metadata["moved_footprints"] for p in actual_pads(old[ref])]
    displaced=[]
    removed=set()
    for item in list(board.GetTracks()):
        net=item.GetNetname()
        clip = any(crosses_disk(item,point,BRASS_RADIUS if route.gap(net)<=.2 else 6.18)
                   for point in holes.values())
        terminal = any(name==net and any(distance(q,box)<.08 for q in track_endpoints(item))
                       for name,box in copper)
        if clip or terminal:
            displaced.append({"net":net,"points_mm":track_endpoints(item),
                              "reason":"mechanical keepout" if clip else "moved component terminal"})
            removed.add(str(item.m_Uuid.AsString()))
    for ref,(x,y,angle) in metadata["moved_footprints"].items():
        old[ref].SetPosition(at((x+50,y+50)))
        old[ref].SetOrientationDegrees(angle)
    for ref,point in holes.items():
        lib = Path(route.CLI.parent.parent/"share/kicad/footprints/MountingHole.pretty")
        footprint = pcb.FootprintLoad(str(lib),"MountingHole_3.5mm")
        assert footprint is not None
        footprint.SetFPIDAsString("MountingHole:MountingHole_3.5mm")
        footprint.SetReference(ref)
        footprint.SetAttributes(footprint.GetAttributes() | pcb.FP_BOARD_ONLY
                                | pcb.FP_EXCLUDE_FROM_BOM | pcb.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(footprint)
        footprint.SetPosition(at(point))
        rule_area(board,ref,point)
    exported = ET.parse(OUT/"new_native_netlist.xml")
    comps = {c.get("ref"):c for c in exported.findall("./components/comp") if c.get("ref") in centers()}
    targets = {(n.get("ref"),n.get("pin")):net.get("name") for net in exported.findall("./nets/net")
               for n in net.findall("node")}
    for ref,center in centers().items():
        component=comps[ref]
        fp=pcb.FootprintLoad(str(FP_DIR),FOOTPRINT)
        fp.SetReference(ref)
        fp.SetValue(component.findtext("value"))
        fp.SetFPIDAsString(f"{LIB}:{FOOTPRINT}")
        fields={name:component.findtext(f'./fields/field[@name="{name}"]') or ""
                for name in ("MPN","Status","Datasheet")}
        fp.SetFields(fields)
        for name in fields:
            fp.GetField(name).SetVisible(False)
        folder=component.find("sheetpath").get("tstamps").strip("/")
        fp.SetPath(pcb.KIID_PATH(f"/{PROJECT_ROOT}/{folder}/{component.findtext('tstamps')}"))
        fp.Value().SetVisible(False)
        board.Add(fp)
        fp.SetPosition(at(center))
        for p in fp.Pads():
            p.SetNet(board.FindNet(targets[ref,p.GetNumber()]))
    for drawing in list(board.GetDrawings()):
        if hasattr(drawing,"GetText") and drawing.GetText()=="GZC13-F R10 REFERENCE / NO DRILLS":
            drawing.SetText("GZC13-F / HAND-WIRE / ENGINEERING HOLD")
    pcb.SaveBoard(str(route.EDA),board)
    draft=route.EDA.read_text(encoding="utf-8")
    blocks = re.compile(r"(?ms)^\t\((?:segment|via)\n.*?^\t\)\n")
    def retain(match):
        key=re.search(r'\(uuid "([^"]+)"\)',match[0])[1]
        return "" if key in removed else match[0]
    route.EDA.write_text(blocks.sub(retain,draft),encoding="utf-8")
    (OUT/"tracks_displaced.json").write_text(json.dumps(displaced,indent=2)+"\n",encoding="utf-8")
    print(len(holes),"NPTH and",sum(1 for _ in rows()),"solder pad positions added;",len(displaced),"track items displaced")


if __name__=="__main__":
    import sys
    if sys.argv[1]=="capture":
        capture()
    else:
        populate()
