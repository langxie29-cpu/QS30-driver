"""Localized R14.6 placement and routing edits."""
from pathlib import Path
import re
import sys

from build_board import STEM
from route_board import BoardRouter, pcb, point, uid, xy


CAP_FOOTPRINT = "Kemet_C2220_HV_Density_B"
CAP_MPN = "C2220C101JDGACTU"
CAP_VALUE = "100p 1kV C0G snubber candidate"
CAP_DATASHEET = "https://www.mouser.com/datasheet/3/508/1/KEM_C1009_C0G_HV_SMD.pdf"
CAP_LIB = "R14_6"

CAP_PATTERN = """(footprint "Kemet_C2220_HV_Density_B"
  (version 20260206)
  (generator "pcbnew")
  (layer "F.Cu")
  (descr "KEMET C1009 table 3 2220 density B. Rectangular nominal land pattern.")
  (attr smd)
  (property "Reference" "REF**" (at 0 -3.7) (layer "F.SilkS")
    (effects (font (size 0.85 0.85) (thickness 0.13))))
  (property "Value" "Kemet_C2220_HV_Density_B" (at 0 3.7) (layer "F.Fab")
    (effects (font (size 0.85 0.85) (thickness 0.13))))
  (fp_rect (start -2.8 -2.5) (end 2.8 2.5) (stroke (width 0.1) (type default)) (fill no) (layer "F.Fab"))
  (fp_rect (start -3.65 -2.95) (end 3.65 2.95) (stroke (width 0.05) (type default)) (fill no) (layer "F.CrtYd"))
  (pad "1" smd rect (at -2.65 0) (size 1.5 5.4) (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "2" smd rect (at 2.65 0) (size 1.5 5.4) (layers "F.Cu" "F.Paste" "F.Mask"))
)
"""


def move(footprint, x, y, angle, backside):
    if footprint.IsFlipped() != backside:
        footprint.Flip(footprint.GetPosition(), pcb.FLIP_DIRECTION_TOP_BOTTOM)
    footprint.SetPosition(point(x, y))
    footprint.SetOrientationDegrees(angle)


def feedback(board, positions):
    router = BoardRouter(board)
    local_nets = {"HV_FB_1", "HV_FB_2"}
    for net, refs in (("HV_FB_1", {"R81", "R82"}), ("HV_FB_2", {"R82", "R83"})):
        actual = {f.GetReference() for f in router.refs.values()
                  for p in f.Pads() if p.GetNetname() == net}
        if actual != refs:
            raise RuntimeError((net, actual))
    for track in list(router.board.GetTracks()):
        if track.GetNetname() in local_nets:
            router.board.RemoveNative(track)
    for ref, location in zip(("R81", "R82", "R83"), positions, strict=True):
        move(router.refs[ref], *location)
    router = BoardRouter(router.board)
    for left, right in (("R81.2", "R82.1"), ("R82.2", "R83.1")):
        if not router.pair("preserve feedback", left, right, margin=8, via_size=.60):
            return False, router.events
    for left, right in (("R81.1", "C47.1"), ("R83.2", "R84.1"), ("R67.2", "R68.1"),
                        ("D3.1", "C47.1")):
        router.pair("feedback and supply", left, right, margin=17, limit=240000)
    router.save(board)
    return True, router.events


def cap_project(eda):
    library = eda / f"{CAP_LIB}.pretty"
    library.mkdir(exist_ok=True)
    (library / f"{CAP_FOOTPRINT}.kicad_mod").write_text(CAP_PATTERN, encoding="utf-8")
    lib_table = eda / "fp-lib-table"
    old = lib_table.read_text(encoding="utf-8").rstrip()
    if CAP_LIB not in old:
        row = f'  (lib (name "{CAP_LIB}")(type "KiCad")(uri "\x24{{KIPRJMOD}}/{CAP_LIB}.pretty")(options "")(descr ""))'
        lib_table.write_text(old[:-1].rstrip() + "\n" + row + "\n)\n", encoding="utf-8")
    sheet = eda / "HV_boost.kicad_sch"
    text = sheet.read_text(encoding="utf-8")
    start = text.index('(property "Reference" "C48"')
    end = text.index('(pin "1"', start)
    cap = text[start:end]
    properties = {"Value": CAP_VALUE, "Footprint": f"{CAP_LIB}:{CAP_FOOTPRINT}",
                  "Datasheet": CAP_DATASHEET, "MPN": CAP_MPN}
    for name, value in properties.items():
        cap, count = re.subn(rf'(\(property "{name}" ")[^"]*(")', rf'\g<1>{value}\2', cap)
        if count != 1:
            raise RuntimeError((name, count))
    sheet.write_text(text[:start] + cap + text[end:], encoding="utf-8")


def replace_cap(router, eda):
    existing = router.refs["C48"]
    pads = {p.GetNumber(): p for p in existing.Pads()}
    replacement = pcb.FootprintLoad(str(eda / f"{CAP_LIB}.pretty"), CAP_FOOTPRINT)
    if replacement is None:
        raise RuntimeError(CAP_FOOTPRINT)
    replacement.SetReference("C48")
    replacement.SetValue(CAP_VALUE)
    replacement.SetDNP(existing.IsDNP())
    for name, value in (("MPN", CAP_MPN), ("Datasheet", CAP_DATASHEET), ("Status", "HOLD_DNP")):
        field = pcb.PCB_FIELD(replacement, pcb.FIELD_T_USER, name)
        field.SetText(value)
        field.SetVisible(False)
        field.SetLayer(pcb.F_Fab)
        replacement.Add(field)
    replacement.SetPath(existing.GetPath())
    replacement.SetUuidDirect(pcb.KIID(uid(existing)))
    replacement.SetFPID(pcb.LIB_ID(CAP_LIB, CAP_FOOTPRINT))
    for pad in replacement.Pads():
        old = pads[pad.GetNumber()]
        pad.SetUuidDirect(pcb.KIID(uid(old)))
        pad.SetNet(old.GetNet())
    # Use stable IDs for graphics that the KiCad footprint loader may randomize.
    from uuid import NAMESPACE_URL, uuid5
    for index, item in enumerate((*replacement.GetFields(), *replacement.GraphicalItems())):
        item.SetUuidDirect(pcb.KIID(str(uuid5(NAMESPACE_URL,
            f"QS30-driver/R14.6/C48/graphic/{index}"))))
    router.board.RemoveNative(existing)
    router.board.Add(replacement)
    return replacement


def snubber(board, locations):
    from shapely.strtree import STRtree
    from route_board import LAYERS, copper, gap, box
    eda = board.parent
    cap_project(eda)
    base = BoardRouter(board)
    footprint = replace_cap(base, eda)
    router = BoardRouter(base.board)
    cap_ids = {uid(p) for p in footprint.Pads()}
    layout = []
    locations = tuple(locations)
    for layer_index in (0, 1):
        candidates = [entry for entry in router.obstacles if entry[3] == layer_index and entry[0] not in cap_ids]
        index = STRtree([entry[4] for entry in candidates])
        court_layer = pcb.B_CrtYd if layer_index else pcb.F_CrtYd
        courts = []
        for ref, other in router.refs.items():
            if ref == "C48":
                continue
            rectangles = [xy(end) for g in other.GraphicalItems() if g.GetLayer() == court_layer
                          for end in (g.GetStart(), g.GetEnd())]
            if rectangles:
                xs, ys = zip(*rectangles)
                courts.append(box(min(xs), min(ys), max(xs), max(ys)))
        court_index = STRtree(courts)
        for x, y, angle, back in locations:
            if back != bool(layer_index):
                continue
            move(footprint, x, y, angle, back)
            half_x, half_y = (3.65, 2.95) if angle % 180 == 0 else (2.95, 3.65)
            court = box(x-half_x, y-half_y, x+half_x, y+half_y).buffer(.07)
            if len(court_index.query(court, predicate="intersects")):
                continue
            allowed = True
            for pad in footprint.Pads():
                net = pad.GetNetname()
                shape = copper(pad, LAYERS[layer_index])
                if not box(52.1, 52.1, 177.9, 127.9).covers(shape):
                    allowed = False
                    break
                if any(other != net and shape.distance(geom) < max(gap(net), other_gap) + .025
                       for ident, other, other_gap, z, geom, is_pad in
                       (candidates[i] for i in index.query(shape.buffer(3.3)))):
                    allowed = False
                    break
            if allowed:
                at = xy(next(p for p in footprint.Pads() if p.GetNumber() == "1").GetPosition())
                target = xy(router.pads("R86.2")[0].GetPosition())
                layout.append((abs(at[0] - target[0]) + abs(at[1] - target[1]) + (0 if back else 7),
                               x, y, angle, back))
    print("Snubber placements with clearance", sorted(layout)[:16], flush=True)
    for _, x, y, angle, back in sorted(layout)[:16]:
        baseline = BoardRouter(board)
        cap = replace_cap(baseline, eda)
        move(cap, x, y, angle, back)
        candidate = BoardRouter(baseline.board)
        if not candidate.pair("snubber", "R86.2", "C48.1", margin=6, limit=100000):
            continue
        returned = candidate.pair("snubber return", "C48.2", "R79.2", margin=11, via_size=.50)
        if not returned and not candidate.pair("snubber bus return", "C48.2", "C47.2",
                                               margin=7, via_size=.50):
            continue
        candidate.save(board)
        return (x, y, angle, back), candidate.events
    return None, []



def replace_span(router, ident, corners):
    from uuid import NAMESPACE_URL, uuid5
    track = router.by_id[ident]
    points = (xy(track.GetStart()), *corners, xy(track.GetEnd()))
    net, layer, width = track.GetNet(), track.GetLayer(), track.GetWidth()
    router.board.RemoveNative(track)
    for index, (a, b) in enumerate(zip(points, points[1:])):
        replacement = pcb.PCB_TRACK(router.board)
        replacement.SetStart(point(*a))
        replacement.SetEnd(point(*b))
        replacement.SetWidth(width)
        replacement.SetNet(net)
        replacement.SetLayer(layer)
        replacement.SetUuidDirect(pcb.KIID(str(uuid5(NAMESPACE_URL,
            f"QS30-driver/R14.6/replace-span/{ident}/{index}/{a}/{b}"))))
        router.board.Add(replacement)


def register_fanout(board):
    b = BoardRouter(board)
    replaced = "49da741d-50fb-41b3-85b1-b51b24d42654"
    replace_span(b, replaced, ((134.0, 81.0), (141.25, 81.0)))
    b = BoardRouter(b.board)
    for left, right in (("U23.10","U21.10"),("U23.11","U21.11"),("U23.12","U22.12"),
                        ("U22.9","U23.14"),("U21.9","U22.14")):
        b.pair("display control", left, right, margin=14, limit=600000, via_size=.50)
    b.save(board)
    return b.events



DGK_ID = "TI_DGK0008A_VSSOP8"


def ti_dgk_lands(board):
    # Keep the nominal lead pitch and use TI DGK0008A's 4.40 mm row span.
    r = BoardRouter(board)
    eda = board.parent
    stock = Path(sys.executable).parents[1] / "share/kicad/footprints/Package_SO.pretty/VSSOP-8_3x3mm_P0.65mm.kicad_mod"
    package = stock.read_text(encoding="utf-8")
    package = package.replace('(footprint "VSSOP-8_3x3mm_P0.65mm"', f'(footprint "{DGK_ID}"', 1)
    package = package.replace('(property "Value" "VSSOP-8_3x3mm_P0.65mm"', f'(property "Value" "{DGK_ID}"', 1)
    package = package.replace("2.1125", "2.2").replace("(size 1.625 0.5)", "(size 1.4 0.45)")
    package = package.replace("(roundrect_rratio 0.25)", "(roundrect_rratio 0.111111)")
    (eda / f"{CAP_LIB}.pretty" / f"{DGK_ID}.kicad_mod").write_text(package, encoding="utf-8")
    for ref, sheet_name in (("U6", "OLED"), ("U13", "Analog_protection"), ("U14", "Analog_protection")):
        footprint = r.refs[ref]
        footprint.SetFPID(pcb.LIB_ID(CAP_LIB, DGK_ID))
        for pad in footprint.Pads():
            x, y = xy(pad.GetPosition())
            cx, _ = xy(footprint.GetPosition())
            x += .0875 if x > cx else -.0875
            pad.SetPosition(point(x, y))
            pad.SetSize(point(1.4, .45))
            pad.SetRoundRectRadiusRatio(.05/.45)
        sch = eda / f"{sheet_name}.kicad_sch"
        text = sch.read_text(encoding="utf-8")
        start = text.index(f'(property "Reference" "{ref}"')
        end = text.index('(pin "1"', start)
        section = text[start:end]
        old = '(property "Footprint" "Package_SO:VSSOP-8_3x3mm_P0.65mm"'
        if section.count(old) != 1:
            raise RuntimeError((ref, section))
        text = text[:start] + section.replace(old, f'(property "Footprint" "{CAP_LIB}:{DGK_ID}"') + text[end:]
        sch.write_text(text, encoding="utf-8")
    # Three inherited lead-ins touched the former inner land edge.
    for ident, target in (
        ("2f14c08e-bca0-57cc-81df-aeb247f37855", (151.42, 77.475)),
        ("16183620-89de-5556-98e4-f1d1818e0029", (154.61, 76.8)),
        ("ac97adde-c2a7-5579-a960-6367799f8ecf", (151.42, 76.8)),
    ):
        from uuid import NAMESPACE_URL, uuid5
        track = r.by_id[ident]
        tail = pcb.PCB_TRACK(r.board)
        tail.SetStart(track.GetEnd())
        tail.SetEnd(point(*target))
        tail.SetNet(track.GetNet())
        tail.SetWidth(track.GetWidth())
        tail.SetLayer(track.GetLayer())
        tail.SetUuidDirect(pcb.KIID(str(uuid5(NAMESPACE_URL, f"QS30-driver/R14.6/DGK/{ident}"))))
        r.board.Add(tail)
    r.save(board)



def ovp_capacitor(board):
    router = BoardRouter(board)
    move(router.refs["C35"], 140., 75., 90, False)
    old_route = ("753ac22f-f3c8-4e40-a47e-9575921bae6e", "b4f17413-f123-41b3-a0cc-e9f9059535d1")
    for ident in old_route:
        track = router.by_id[ident]
        if track.GetNetname() != "GND":
            raise RuntimeError(ident)
        router.board.RemoveNative(track)
    router = BoardRouter(router.board)
    if not router.connected(router.pads("C35.1"), router.pads("U13.2")):
        raise RuntimeError("C35 local land must join inherited HV_OVP_S copper")
    if not router.pair("OVP capacitor local return", "C35.2", "U13.4", margin=5,
                       limit=40000, alternatives=False, via_size=.50):
        raise RuntimeError("C35 return could not rejoin GND")
    router.save(board)
    return router.events
