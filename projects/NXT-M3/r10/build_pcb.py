"""Create a two-layer prelayout from the native hierarchical KiCad XML netlist."""
import csv
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew as pcb

from build_schematic import EDA, PROJECT, LIB, HERE, uid
from circuit import parts, kinds

MECH = json.loads((HERE/"mechanical.json").read_text(encoding="utf-8-sig"))
EVIDENCE = HERE/"evidence"
LIBROOT = Path(os.environ.get("KICAD10_FOOTPRINT_DIR",
    r"C:\Program Files\KiCad\10.0\share\kicad\footprints"))
OX,OY = MECH["board"]["cad_origin"]

def at(x,y):
    return pcb.VECTOR2I(pcb.FromMM(OX+x),pcb.FromMM(OY+y))

def shape(board, kind, start, end, layer, line=0.15):
    item=pcb.PCB_SHAPE()
    item.SetShape(kind)
    item.SetLayer(layer)
    item.SetStart(at(*start))
    item.SetEnd(at(*end))
    item.SetWidth(pcb.FromMM(line))
    board.Add(item)

def box(board,rect,layer):
    x,y,w,h=rect
    shape(board,pcb.SHAPE_T_RECT,(x,y),(x+w,y+h),layer)

def circle(board,center,diameter,layer):
    x,y=center
    shape(board,pcb.SHAPE_T_CIRCLE,center,(x+diameter/2,y),layer)

def text(board,value,x,y,layer=pcb.Dwgs_User,size=1):
    item=pcb.PCB_TEXT(board)
    item.SetText(value)
    item.SetTextSize(pcb.VECTOR2I(pcb.FromMM(size),pcb.FromMM(size)))
    item.SetTextThickness(pcb.FromMM(0.15))
    item.SetLayer(layer)
    item.SetPosition(at(x,y))
    board.Add(item)

def keepout(board,name,rect,all_features):
    x,y,w,h=rect
    points=[at(*xy) for xy in ((x,y),(x+w,y),(x+w,y+h),(x,y+h))]
    zone=pcb.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetZoneName(name)
    zone.SetLayerSet(pcb.LSET.AllCuMask())
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(all_features)
    # The WROOM body spans the antenna boundary by design; footprints are checked separately.
    zone.SetDoNotAllowFootprints(False)
    contour=zone.Outline()
    contour.NewOutline()
    for point in points:
        contour.Append(point.x,point.y)
    board.Add(zone)

def comp_placement():
    table={}
    def add(rows):
        for ref,x,y,*rest in rows:
            table[ref]=(x,y,*((rest+[0,False])[:2]))
    def bank(sheet,positions,skip=()):
        items=[p for p in parts if p["sheet"]==sheet and p["fp"] and p["ref"] not in skip]
        if len(items)>len(positions):
            raise ValueError(f"Placement overflow in {sheet}: {len(items)}>{len(positions)}")
        for part, xy in zip(items,positions):
            table[part["ref"]]=(xy[0],xy[1],0,len(xy)>2 and xy[2])
    add([
        ("J1",21,6),("F1",27,6),("U1",31,10),("U2",31,24),("L1",38,24),
        ("C5",40,10),("R6",31,6),("R7",35.5,4.5),("C6",28,21),("C7",35,20),("C8",40,20),
        ("U3",*MECH["rf"]["module_anchor"],MECH["rf"]["rotation"]),
        ("J2",22,40,90),("SW1",8,51),("U4",28,30),("U24",28,40),
        ("C9",19,21),("C10",19,25),("C11",26,32),("C12",31,31),("C50",30,42),
        ("R8",9,40),("R9",26,35),("R10",9,47),("R11",19,29),("R12",22,29),
        ("R13",25,29),("R14",25,38),("R15",28,44),("R54",33,40),
        ("R16",33,34),("R17",36,34),("TP2",18,34),("TP3",18,37),
        ("TP4",18,40),("TP5",31,37),("TP6",21,35),
        ("J3",68,21,90,True),("U5",61,21,0,True),("U6",56,19,0,True),
        ("U7",52,15,0,True),("D1",74,20,0,True),
        ("J4",41,6),("U8",46,10),("U9",47,16),("U10",47,25),("U19",47,30),
        ("Q31",54,26),("C49",44,30),
        ("U20",22,10,90,True),("U21",41,37,90,True),("U22",65,37,90,True),("U23",89,37,90,True),
        ("C21",17,10,0,True),("C22",44,37,0,True),("C23",68,37,0,True),("C24",92,37,0,True),
        ("U11",90,9),("R40",86,8),("U12",78,24),("U13",94,27),("U14",103,27),
        ("U15",89,30),("U16",103,11),("L2",109,10),("D2",106,16),
        ("U17",117,22),("U18",111,21),("Q32",124,22,90),("L3",119,14.5),("D3",121,30,90),
        ("R73",123,34),("C47",119,43,90,True),
    ])
    bank("Input_and_3V3",
         [(x,y) for y in (11,14,17) for x in (21,25,27,34,37)]
         +[(20,18),(26,18),(30,18),(36,17)],
         {"J1","F1","U1","U2","L1","C5","C6","C7","C8","R6","R7"})
    bank("OLED",[(x,y,True) for y in (11,15) for x in (57,61,66,70,74,78)],
         {"J3","U5","U6","U7","D1"})
    bank("Hardware_inhibit",
         [(x,y) for y in (7,13,16,19,23,27,31,34) for x in (50,54,58)],
         {"J4","U8","U9","U10","U19","Q31","C49"})
    bank("Shift_registers",[(x,29,True) for x in (28,32,36,40,44,48)],
         {f"U{20+i}" for i in range(4)} | {f"C{21+i}" for i in range(4)})
    bank("HV_cutoff",[(x,y) for y in (6,11,15,18) for x in (87,94,98)],{"U11","R40"})
    bank("Analog_protection",
         [(x,y) for y in (22,26,30,33) for x in (74,82,86,98)]
         +[(x,y,True) for y in (23,28,32) for x in (72,79,86,94,102,109)],
         {"U12","U13","U14","U15"})
    bank("Gate_bias",[(x,y) for y in (7,13,17) for x in (103,109,112)],{"U16","L2","D2"})
    bank("HV_boost",[(x,y,True) for y in (8,13,18,23,28) for x in (100,105,111,117,123)],
         {"U17","U18","Q32","L3","D3","R73","C47"})
    for i,part in enumerate(p for p in parts if p["sheet"]=="Tube_interfaces" and p["fp"]):
        tube,stage=divmod(i,2)
        table[part["ref"]]=(MECH["tube"]["centers"][tube][0]+(stage*8-4),34.6,0,False)
    for i,part in enumerate(p for p in parts if p["sheet"]=="HV_bleeders"):
        branch,stage=divmod(i,4)
        table[part["ref"]]=(91+stage*8,63+branch*5,0,False)
    for n in range(30):
        tube,digit=divmod(n,10)
        center=MECH["tube"]["centers"][tube][0]
        x=center+(digit%5-2)*5
        y=66.6+6.3*(digit//5)
        table[f"Q{n+1}"]=(x,y,0,True)
        table[f"R{100+n}"]=(x,y-2.25,0,True)
        table[f"R{200+n}"]=(x,y+2.25,0,True)
    return table

def load_footprint(name):
    lib,package=name.split(":")
    location=EDA/f"{lib}.pretty" if lib==LIB else LIBROOT/f"{lib}.pretty"
    if not (location/f"{package}.kicad_mod").is_file():
        raise FileNotFoundError(f"{name}: {location}")
    fp=pcb.FootprintLoad(str(location),package)
    if fp is None:
        raise ValueError(f"KiCad failed to load {name}")
    # FootprintLoad assigns only the item name by default.
    fp.SetFPIDAsString(name)
    return fp

def load_netlist(board):
    netlist=ET.parse(EVIDENCE/"native_netlist.xml")
    components={c.attrib["ref"]:c for c in netlist.findall("./components/comp")}
    by_pad={}
    for net in netlist.findall("./nets/net"):
        name=net.attrib["name"]
        item=pcb.NETINFO_ITEM(board,name)
        board.Add(item)
        for node in net.findall("node"):
            by_pad[(node.attrib["ref"],node.attrib["pin"])]=item
    return components,by_pad

def decorate(board):
    w,h=MECH["board"]["size"]
    box(board,(0,0,w,h),pcb.Edge_Cuts)
    for i,center in enumerate(MECH["tube"]["centers"],1):
        circle(board,center,MECH["tube"]["diameter"],pcb.Dwgs_User)
        circle(board,center,MECH["socket"]["approach_envelope_diameter"],pcb.Cmts_User)
        text(board,f"V{i} SOCKET TBD",*center)
    oled=MECH["oled"]["carrier_keepout"]
    x,y=oled["center"]
    w,h=oled["size"]
    box(board,(x-w/2,y-h/2,w,h),pcb.Dwgs_User)
    text(board,"OLED CARRIER TBD",x,y)
    for i,center in enumerate(MECH["mounting"]["hole_centers"],1):
        circle(board,center,MECH["mounting"]["hardware_envelope_diameter"],pcb.Dwgs_User)
        fp=load_footprint("MountingHole:MountingHole_3.2mm_M3")
        fp.SetReference(f"MH{i}")
        fp.SetPosition(at(*center))
        fp.SetAttributes(fp.GetAttributes() | pcb.FP_BOARD_ONLY | pcb.FP_EXCLUDE_FROM_BOM | pcb.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp)
    keepout(board,"RF plan / antenna edge", (0.1,14,0.4,22),True)
    box(board,MECH["rf"]["near_field_reserve"],pcb.Cmts_User)
    text(board,"RF / WALL CLEARANCE TBD",11,43,pcb.Cmts_User,.8)
    text(board,"HV / POWER CONVERSION",104,4,pcb.Cmts_User,.9)
    text(board,"LV / INPUT / SERVICE",32,4,pcb.Cmts_User,.9)
    text(board,"PRELAYOUT / HOLD / SOCKETS UNDRILLED",65,78,pcb.Dwgs_User,.9)


def inside(rect, boundary):
    l,t,r,b=rect
    x,y,w,h=boundary
    return l>=x and t>=y and r<=x+w and b<=y+h

def overlaps(a,b,margin=.15):
    return a[0]<b[2]+margin and a[2]>b[0]-margin and a[1]<b[3]+margin and a[3]>b[1]-margin

def rectangle(center, width, height):
    x,y=center
    return (x-width/2,y-height/2,x+width/2,y+height/2)

def courtyard(fp):
    bounds=fp.GetCourtyard(fp.GetLayer()).BBox()
    if bounds.GetWidth()<=0 or bounds.GetHeight()<=0:
        bounds=fp.GetBoundingBox(False,False)
    pos=fp.GetPosition()
    return tuple(pcb.ToMM(a-b) for a,b in (
        (bounds.GetLeft(),pos.x),(bounds.GetTop(),pos.y),
        (bounds.GetRight(),pos.x),(bounds.GetBottom(),pos.y)))

def refine_placement(footprints):
    """Distribute overlapping proposal boxes while keeping each part on its proposed side."""
    w,h=MECH["board"]["size"]
    board_boundary=(.6,.6,w-1.2,h-1.2)
    front=pcb.F_Cu
    back=pcb.B_Cu
    mount=[rectangle(c,8,8) for c in MECH["mounting"]["hole_centers"]]
    glass=[rectangle(c,29.6,29.6) for c in MECH["tube"]["centers"]]
    oled=MECH["oled"]["carrier_keepout"]
    carrier=rectangle(oled["center"],*oled["size"])
    obstacles={front:mount+glass,back:mount.copy()}
    offsets=sorted(((dx/2,dy/2) for dx in range(-36,37) for dy in range(-36,37)),
                   key=lambda q:(q[0]**2+q[1]**2,abs(q[1]),q))
    prepared=[(fp,xy,courtyard(fp),any(p.GetDrillSize().x>0 for p in fp.Pads()))
              for fp,xy in footprints]
    prepared.sort(key=lambda row: (row[0].GetReference() not in ("U3","J1","J2","J3","C47"),
                  -(row[2][2]-row[2][0])*(row[2][3]-row[2][1]),row[0].GetReference()))
    warnings=[]
    for fp,xy,box_,thru in prepared:
        x,y=xy
        ref,side=fp.GetReference(),fp.GetLayer()
        other_side=back if side==front else front
        other_pad_boxes=[]
        if thru:
            origin=at(x,y)
            for pad in fp.Pads():
                if pad.GetDrillSize().x<=0:
                    continue
                pp=pad.GetPosition()-origin
                pbox=pad.GetBoundingBox()
                other_pad_boxes.append(rectangle((pcb.ToMM(pp.x),pcb.ToMM(pp.y)),
                                       pcb.ToMM(pbox.GetWidth()),pcb.ToMM(pbox.GetHeight())))
        def shifted(b_, xx, yy):
            return b_[0]+xx,b_[1]+yy,b_[2]+xx,b_[3]+yy
        for dx,dy in offsets:
            xx,yy=x+dx,y+dy
            bb=shifted(box_,xx,yy)
            if ref=="U3":
                break
            if not inside(bb,board_boundary):
                continue
            if any(overlaps(bb,o) for o in obstacles[side]):
                continue
            if side==front and overlaps(bb,carrier):
                continue
            if any(any(overlaps(shifted(p,xx,yy),o) for o in obstacles[other_side])
                   for p in other_pad_boxes):
                continue
            break
        else:
            xx,yy=x,y
            bb=shifted(box_,x,y)
            warnings.append(ref)
        fp.SetPosition(at(xx,yy))
        obstacles[side].append(bb)
        obstacles[other_side].extend(shifted(p,xx,yy) for p in other_pad_boxes)
        # Move the reference text to the assembly layer to leave dense silkscreen legible.
        fp.Reference().SetLayer(pcb.F_Fab if side==front else pcb.B_Fab)
        fp.Reference().SetPosition(at(xx,yy))
    return warnings


def build():
    board=pcb.BOARD()
    board.SetCopperLayerCount(2)
    decorate(board)
    components,by_pad=load_netlist(board)
    locations=comp_placement()
    report=[]
    placed=[]
    for part in parts:
        ref,fp_id=part["ref"],part["fp"]
        if part["kind"]=="Flag":
            continue
        if ref not in components:
            raise AssertionError(f"Missing native component {ref}")
        comp=components[ref]
        if (comp.findtext("footprint") or "") != fp_id:
            raise AssertionError(f"Footprint differs in XML: {ref}")
        pins=part["nets"]
        for n,net in pins.items():
            actual=by_pad.get((ref,n))
            if (actual.GetNetname() if actual and not actual.GetNetname().startswith("unconnected-") else None)!=net:
                raise AssertionError(f"Net mismatch on native {ref}.{n}: {net!r} / {actual}")
        if not fp_id:
            report.append([ref,fp_id,"SOCKET GEOMETRY TBD; no copper pads",""])
            continue
        fp=load_footprint(fp_id)
        fp.SetReference(ref)
        fp.SetValue(part["value"])
        fp.SetFields({"MPN":part["mpn"],"Status":part["status"],"Datasheet":part["url"]})
        for field in ("MPN","Status","Datasheet"):
            fp.GetField(field).SetVisible(False)
        fp.SetAttributes(fp.GetAttributes() & ~pcb.FP_EXCLUDE_FROM_BOM)
        folder=comp.find("sheetpath").attrib["tstamps"].strip("/")
        fp.SetPath(pcb.KIID_PATH(f"/{uid('root')}/{folder}/{comp.findtext('tstamps')}"))
        if part["status"]=="HOLD_DNP":
            fp.SetAttributes(fp.GetAttributes() | pcb.FP_DNP)
        x,y,rotation,back=locations[ref]
        board.Add(fp)
        fp.SetPosition(at(x,y))
        if back:
            fp.Flip(at(x,y),False)
        fp.SetOrientationDegrees(rotation)
        fp.Value().SetVisible(False)
        assigned=set()
        for pad in fp.Pads():
            n=pad.GetNumber()
            if n and n not in pins:
                raise AssertionError(f"Unexpected numbered pad: {ref}.{n}")
            if n:
                assigned.add(n)
            net=by_pad.get((ref,n))
            if net is not None:
                pad.SetNet(net)
        if assigned != set(pins):
            raise AssertionError(f"Missing numbered pads on {ref}: {set(pins)-assigned}")
        placed.append((fp,(x,y)))
        report.append([ref,fp_id,"NUMBERED_PADS_MATCH",""])
    warnings=refine_placement(placed)
    pos={fp.GetReference():fp for fp,_ in placed}
    for row in report:
        if row[0] in pos:
            fp=pos[row[0]]
            loc=fp.GetPosition()
            row[3]=f"{pcb.ToMM(loc.x)-OX:.2f},{pcb.ToMM(loc.y)-OY:.2f},{fp.GetOrientationDegrees():g},{'B' if fp.GetLayer()==pcb.B_Cu else 'F'}"
    print(f"Unresolved placement boxes: {warnings}")
    pcb.SaveBoard(str(EDA/f"{PROJECT}.kicad_pcb"),board)
    with (EVIDENCE/"footprint_sync.csv").open("w",encoding="utf-8",newline="") as stream:
        table=csv.writer(stream)
        table.writerow(("ref","footprint","native_net_and_pad_audit","x_y_mm_rotation_layer"))
        table.writerows(report)
    print(f"Compared {len(report)} native schematic components; {len(report)-3} placed, 3 logical sockets without pads")

if __name__=="__main__":
    build()
