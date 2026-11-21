"""Give Q1 copper-only routing tails and retain its original solder apertures."""
from pathlib import Path

import pcbnew as pcb

from route_r14_1 import point, xy

LIB = "R10_R10"
PATTERN = "SOT-23_MMBTA42_route_tails"
FOOTPRINT_ID = f"{LIB}:{PATTERN}"


def layers(*enabled):
    result = pcb.LSET()
    for layer in enabled:
        result.AddLayer(layer)
    return result


def extend(footprint):
    # Keep paste openings and exposed lands at the factory-library dimensions.
    side = footprint.GetLayer()
    mask, paste = ((pcb.F_Mask,pcb.F_Paste) if side==pcb.F_Cu else (pcb.B_Mask,pcb.B_Paste))
    center, _ = xy(footprint.GetPosition())
    for pad in list(footprint.Pads()):
        x,y = xy(pad.GetPosition())
        length,height = xy(pad.GetSize())
        assert (round(length,3),round(height,3)) == (1.475,.6)
        direction = 1 if x>center else -1
        aperture = pcb.PAD(footprint)
        aperture.SetAttribute(pcb.PAD_ATTRIB_SMD)
        aperture.SetShape(pcb.PAD_SHAPE_ROUNDRECT)
        aperture.SetNumber("")
        aperture.SetPosition(pad.GetPosition())
        aperture.SetFPRelativeOrientation(pad.GetFPRelativeOrientation())
        aperture.SetSize(pad.GetSize())
        aperture.SetRoundRectRadiusRatio(.25)
        aperture.SetLayerSet(layers(mask,paste))
        footprint.Add(aperture)
        tail = .875
        pad.SetLayerSet(layers(side))
        pad.SetPosition(point(x+direction*tail/2,y))
        pad.SetSize(point(length+tail,height))


def apply(board, eda, footprint_library):
    q = board.FindFootprintByReference("Q1")
    if q.GetFPIDAsString() != "Package_TO_SOT_SMD:SOT-23":
        raise ValueError("Expected frozen Q1 land pattern")
    extend(q)
    q.SetFPIDAsString(FOOTPRINT_ID)

    library = pcb.FootprintLoad(str(footprint_library/"Package_TO_SOT_SMD.pretty"),"SOT-23")
    extend(library)
    library.SetFPIDAsString(FOOTPRINT_ID)
    library.SetLibDescription("SOT-23 original mask and paste openings with outward copper-only routing tails")
    pcb.FootprintSave(str(eda/f"{LIB}.pretty"),library)

    path = eda/"Cathodes_1.kicad_sch"
    source = path.read_text(encoding="utf-8")
    ref = source.index('(property "Reference" "Q1"')
    old = '(property "Footprint" "Package_TO_SOT_SMD:SOT-23"'
    at = source.index(old,ref)
    if at >= source.index('(instances ',ref):
        raise ValueError("Could not identify Q1 footprint property")
    source = source[:at] + old.replace("Package_TO_SOT_SMD:SOT-23",FOOTPRINT_ID) + source[at+len(old):]
    path.write_text(source,encoding="utf-8",newline="\n")


def power_tails(footprint):
    for pad in list(footprint.Pads()):
        if pad.GetNumber() not in ("5","6"):
            continue
        assert footprint.GetLayer()==pcb.F_Cu
        width,height = xy(pad.GetSize())
        assert (width,height)==(.25,1.75)
        x,y = xy(pad.GetPosition())
        aperture = pcb.PAD(footprint)
        aperture.SetAttribute(pcb.PAD_ATTRIB_SMD)
        aperture.SetShape(pcb.PAD_SHAPE_ROUNDRECT)
        aperture.SetPosition(pad.GetPosition())
        aperture.SetSize(pad.GetSize())
        aperture.SetRoundRectRadiusRatio(.15)
        aperture.SetLayerSet(layers(pcb.F_Mask,pcb.F_Paste))
        footprint.Add(aperture)
        tail = .875 if pad.GetNumber()=="5" else -.875
        pad.SetLayerSet(layers(pcb.F_Cu))
        pad.SetPosition(point(x,y+tail/2))
        pad.SetSize(point(width,height+abs(tail)))


def apply_cutoff(board,eda):
    new_name = "TI_RPW0010A_IN_OUT_escape"
    fp_id = f"{LIB}:{new_name}"
    old = f"{LIB}:TI_RPW0010A"
    cutoff = board.FindFootprintByReference("U11")
    assert cutoff.GetFPIDAsString()==old
    power_tails(cutoff)
    cutoff.SetFPIDAsString(fp_id)

    library = pcb.FootprintLoad(str(eda/f"{LIB}.pretty"),"TI_RPW0010A")
    power_tails(library)
    library.SetFPIDAsString(fp_id)
    library.SetLibDescription("RPW0010A escape test with separated IN and OUT copper-only land tails")
    pcb.FootprintSave(str(eda/f"{LIB}.pretty"),library)
    sheet = eda/"HV_cutoff.kicad_sch"
    data = sheet.read_text(encoding="utf-8")
    original = f'(property "Footprint" "{old}"'
    assert data.count(original)==1
    sheet.write_text(data.replace(original,f'(property "Footprint" "{fp_id}"'),encoding="utf-8",newline="\n")
