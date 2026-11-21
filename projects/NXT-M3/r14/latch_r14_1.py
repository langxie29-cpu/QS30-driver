"""Place the same SN74LVC1G74 pin map in its wider TI DCT package."""
import json
import re

import pcbnew as pcb

from placement import Placement

PART = "SN74LVC1G74DCTR"
PACKAGE = "Package_SO:SSOP-8_2.95x2.8mm_P0.65mm"


def apply(board, eda, footprint_library, r14_routes):
    old = board.FindFootprintByReference("U8")
    root = json.loads(r14_routes.read_text(encoding="utf-8"))
    branches = {uuid for _,a,b,items in root["retained_routes"] if "U8" in (a,b) for uuid in items}
    nets = {p.GetNumber():p.GetNetname() for p in old.Pads()}
    fp = pcb.FootprintLoad(str(footprint_library/"Package_SO.pretty"),PACKAGE.split(":")[1])
    pcb_path = eda/"NXT-M3-R14.kicad_pcb"
    source = pcb_path.read_text(encoding="utf-8")
    old_id = str(old.m_Uuid.AsString())
    removed = set()

    def omit(node):
        raw = node.group(0)
        if raw.startswith("\t(footprint"):
            if f'(uuid "{old_id}")' in raw:
                removed.add(old_id)
                return ""
        else:
            uid = re.search(r'\(uuid "([^"]+)"\)',raw)
            if uid and uid.group(1) in branches:
                removed.add(uid.group(1))
                return ""
        return raw

    pcb_path.write_text(re.sub(r"(?ms)^\t\((?:footprint|segment|via)(?: |\n).*?^\t\)\n",omit,source),
                        encoding="utf-8",newline="\n")
    assert removed == branches | {old_id},removed
    path = old.GetPath().AsString()
    changed_board = pcb.LoadBoard(str(pcb_path))
    fp.SetFPIDAsString(PACKAGE)
    fp.SetReference("U8")
    fp.SetValue(PART)
    fp.SetPath(pcb.KIID_PATH(path))
    fp.SetFields({"MPN":PART,"Status":"ENGINEERING_CANDIDATE",
                  "Datasheet":"https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf"})
    for name in ("MPN","Status","Datasheet"):
        fp.GetField(name).SetVisible(False)
    fp.Reference().SetLayer(pcb.F_Fab)
    fp.Value().SetVisible(False)
    for pin in fp.Pads():
        name = nets[pin.GetNumber()]
        net = changed_board.FindNet(name)
        if net is None:
            net = pcb.NETINFO_ITEM(changed_board,name)
            changed_board.Add(net)
        pin.SetNet(net)
    changed_board.Add(fp)
    placement = Placement(changed_board,{"U8"})
    position = placement.choose(fp,(102.0,62.75,0,0))
    fp.Reference().SetLayer(pcb.F_Fab if fp.GetLayer()==pcb.F_Cu else pcb.B_Fab)

    sheet = eda/"Hardware_inhibit.kicad_sch"
    schematic = sheet.read_text(encoding="utf-8")
    begin = schematic.index('(property "Reference" "U8"')
    end = schematic.index('(instances ',begin)
    original = schematic[begin:end]
    assert original.count("SN74LVC1G74DCUR")==2
    changed = original.replace("SN74LVC1G74DCUR",PART)
    changed = changed.replace("Package_SO:VSSOP-8_2.3x2mm_P0.5mm",PACKAGE)
    sheet.write_text(schematic[:begin]+changed+schematic[end:],encoding="utf-8",newline="\n")
    return changed_board, position, sorted(branches)
