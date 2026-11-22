"""Build the R14.4 editable project from the frozen whole-system R14 PCB."""

import argparse
import json
from pathlib import Path
import re
import shutil
from uuid import NAMESPACE_URL, uuid5

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / "r14" / "eda"
OLD_STEM = "NXT-M3-R14"
STEM = "NXT-M3-R14.4"
LAND = "Jingdao_MMBTA42_nominal"
FPID = f"R14_4:{LAND}"
DISPLAY_Q = {f"Q{n}" for n in range(1, 31)}
OLD_FPID = r'(?:R10_R10:SOT-23_MMBTA42_route_tails|Package_TO_SOT_SMD:SOT-23)'
HV = ("HV_BUS", "K*", "ANODE_*", "ALIM_*", "BLEED_*",
      "HV_FB_*", "HV_OVP_S_*", "HV_RES_S_*")
PLACEMENTS = (
    # References, PCB-top-view rotation centre, clockwise degrees, translation.
    (("R302", "R303"), (78.5, 80.6), 180, (-1.5, 21.0)),
    (("R60", "R61"), (142.0, 81.75), 180, (-4.5, 9.0)),
    (("R62", "R63"), (128.0, 73.0), 90, (5.0, -10.0)),
    (("R64",), (138.0, 73.0), 90, (-0.5, 0.0)),
    (("D3",), (166.0, 80.0), 90, (-0.5, -0.5)),
    (("R86",), (147.0, 78.0), 0, (18.0, 4.0)),
    (("C48",), (155.0, 81.0), 0, (16.5, 0.0)),
)
BASE_VIAS = {
    "BASE_06": 72.25, "BASE_07": 77.25, "BASE_08": 82.25,
    "BASE_16": 110.25, "BASE_17": 115.25, "BASE_18": 120.25,
}
ROUTES = (
    ("ANODE_1", pcb.F_Cu, .30, ((70.625, 100.125), (70.75, 100), (71.25, 100), (71.875, 99.375))),
    ("ANODE_1", pcb.B_Cu, .30, ((71.875, 99.375), (71.875, 99.25), (72.5, 98.625),
                               (72.5, 96.75), (72.25, 96.5), (72.25, 96.25),
                               (71, 95),
                               (67.75, 95), (67.5, 95.25), (65.75, 95.25))),
    ("ANODE_1", pcb.F_Cu, .30, ((65.75, 95.25), (66.125, 95.25))),
    ("SW_HV", pcb.F_Cu, .50, ((168.5, 78.75), (170, 78.75), (170.5, 78.25), (171.65, 78.25))),
    ("HV_OVP_S", pcb.B_Cu, .20, ((134.625, 70.375), (135.625, 70.375), (137.125, 71.875))),
    ("HV_FB", pcb.B_Cu, .20, ((172.875, 72.625), (171.5, 72.625))),
    ("HV_FB_1", pcb.B_Cu, .30, ((152.5, 70.125), (152.5, 70.25), (152.375, 70.375),
                               (152.375, 70.50), (152.25, 70.625), (152.25, 70.875),
                               (152.125, 71), (152.125, 75.875))),
)
MONITOR_FANOUT = (
    ("HV_FB", pcb.B_Cu, .20, ((168.625, 72.375), (168.625, 73.375),
                             (168.375, 73.625), (166, 73.625))),
    ("HV_FB", pcb.F_Cu, .20, ((166, 73.625), (163.875, 75.75), (163.625, 75.75))),
    ("HV_BUS", pcb.B_Cu, .30, ((145.5, 79.375), (145.5, 82.25))),
    ("HV_BUS", pcb.F_Cu, .30, ((145.5, 82.25), (145.5, 83))),
)
LOCAL_PLACEMENTS = (
    ("C33", (.125, 0), 270),
    ("C42", (-2.25, -2), 90),
    ("C43", (.5, -.875), 0),
    ("C44", (0, -.625), 0),
    ("R65", (2, 2.875), 270),
)
BIAS_PLACEMENTS = (
    ((101, 102, 103, 111, 112, 113, 121, 122, 123), (-.45, -.15)),
    ((104, 106, 107, 108, 114, 116, 117, 118, 119, 124, 127, 128), (0, -.15)),
    ((205, 208, 215, 216, 225), (0, .15)),
)
Q2_SHIFT = (-.75, 0)
Q2_ROUTES = (
    ("GND", pcb.B_Cu, .20, ((69.745, 115.65), (69.745, 115.005), (70, 114.75),
                           (70, 111.625), (70.625, 111), (72, 111), (72.5, 111.5))),
    ("GND", pcb.B_Cu, .20, ((70, 114.75), (70, 115), (68.5, 116.5), (64.75, 116.5))),
    ("GND", pcb.F_Cu, .20, ((64.75, 116.5), (61.5, 116.5), (61.375, 116.375))),
    ("K1_1", pcb.B_Cu, .30, ((72.785, 116.6), (72.875, 116.5), (73.125, 116.5))),
    ("K1_1", pcb.F_Cu, .30, ((73.125, 116.5), (70.625, 114), (67.5, 114))),
    ("K1_1", pcb.B_Cu, .30, ((67.5, 114), (67.5, 110.125), (74.875, 102.75),
                            (74.875, 97.375), (75, 97.25))),
    ("K1_1", pcb.F_Cu, .30, ((75, 97.25), (75, 96.75))),
    ("BASE_01", pcb.B_Cu, .20, ((69.875, 117.875), (69.875, 118.25), (70.625, 119))),
    ("BASE_01", pcb.In1_Cu, .20, ((70.625, 119), (70.875, 119), (71.875, 120),
                                (72.625, 120), (73.5, 119.125), (73.625, 119.125))),
    ("BASE_01", pcb.F_Cu, .20, ((73.625, 119.125), (73.875, 118.875), (74, 118.875),
                               (74.125, 118.75), (74.375, 118.75), (75.625, 117.5),
                               (75.625, 115.375), (74.5, 114.25))),
    ("BASE_01", pcb.B_Cu, .20, ((74.5, 114.25), (74.125, 114.25), (73.875, 114), (72.75, 114))),
)
Q2_VIAS = {
    "GND": ((64.75, 116.5),),
    "K1_1": ((73.125, 116.5), (67.5, 114), (75, 97.25)),
    "BASE_01": ((70.625, 119), (73.625, 119.125), (74.5, 114.25)),
}


def xy(vector):
    return pcb.ToMM(vector.x), pcb.ToMM(vector.y)


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def uid(item):
    return str(item.m_Uuid.AsString())


def new_id(label):
    return pcb.KIID(str(uuid5(NAMESPACE_URL, f"QS30-driver/R14.4/P01/{label}")))


def pads(footprint):
    return {pad.GetNumber(): pad for pad in footprint.Pads() if pad.GetNumber()}


def replace_transistor(board, old, local_library):
    land = pcb.FootprintLoad(str(local_library), LAND)
    if land is None:
        raise RuntimeError(f"Could not load {local_library / (LAND + '.kicad_mod')}")
    ref = old.GetReference()
    old_pads = pads(old)
    new_pads = pads(land)
    assert set(old_pads) == set(new_pads) == {"1", "2", "3"}, ref
    land.SetUuidDirect(old.m_Uuid)
    land.SetFPID(pcb.LIB_ID("R14_4", LAND))
    land.SetPath(old.GetPath())
    land.SetSheetfile(old.GetSheetfile())
    land.SetSheetname(old.GetSheetname())
    land.SetAttributes(old.GetAttributes())
    land.SetLocked(old.IsLocked())
    for field in old.GetFields():
        name = field.GetName()
        if name not in {"Reference", "Value", "KiLib_Generator"}:
            land.SetField(name, field.GetText())
            land.GetField(name).SetVisible(False)
    land.SetReference(ref)
    land.SetValue(old.GetValue())
    for i, graphic in enumerate(land.GraphicalItems()):
        graphic.SetUuidDirect(new_id(f"{ref}/graphic/{i}"))
    for field in land.GetFields():
        field.SetUuidDirect(new_id(f"{ref}/field/{field.GetName()}"))
    for pin, pad in new_pads.items():
        previous = old_pads[pin]
        pad.SetUuidDirect(previous.m_Uuid)
        pad.SetPinFunction(previous.GetPinFunction())
        pad.SetPinType(previous.GetPinType())

    board.Remove(old)
    board.Add(land)
    if old.IsFlipped():
        land.Flip(land.GetPosition(), pcb.FLIP_DIRECTION_TOP_BOTTOM)
    land.SetOrientation(old.GetOrientation())
    land.SetPosition(old.GetPosition())
    for pin, pad in new_pads.items():
        pad.SetNet(old_pads[pin].GetNet())
    for field, original in ((land.Reference(), old.Reference()), (land.Value(), old.Value())):
        field.SetLayer(original.GetLayer())
        field.SetPosition(original.GetPosition())
        field.SetTextAngle(original.GetTextAngle())
        field.SetTextSize(original.GetTextSize())
        field.SetTextThickness(original.GetTextThickness())
        field.SetVisible(original.IsVisible())
    return land


def trace(board, net, layer, width, start, finish, label):
    assert start != finish, (net, label)
    segment = pcb.PCB_TRACK(board)
    segment.SetUuidDirect(new_id(label))
    segment.SetNet(board.FindNet(net))
    segment.SetLayer(layer)
    segment.SetWidth(pcb.FromMM(width))
    segment.SetStart(point(*start))
    segment.SetEnd(point(*finish))
    board.Add(segment)
    return segment


def track_chain(board, net, layer, width, vertices, label):
    return [trace(board, net, layer, width, start, finish, f"{label}/{i}")
            for i, (start, finish) in enumerate(zip(vertices, vertices[1:]))]


def reroute_q1(board, contacts):
    # Retain the already-routed tails and tie into their frozen junctions.
    # Each replacement segment enters the manufacturer's land from the outside row.
    paths = {
        "32103809-88e7-40cc-8067-12b5ba35b9a0":
            [(58.75, 116.375), (58.90, 116.375), (59.04, 116.235)],
        "50b503b5-0219-40a1-8fd9-2daf4cd4b09b":
            [(58.75, 112.50), (58.75, 113.525), (58.95, 113.725), (59.04, 113.725)],
        "c5afabdf-562b-4738-a43d-ace104de75ea":
            [(58.375, 115.125), (58.375, 114.65), (58.85, 114.175), (58.99, 114.175)],
        "1ca7c063-78b8-4e36-a5fc-3e7be8012695":
            [(63, 111.125), (63, 114.75), (62.75, 115), (62.035, 115)],
    }
    assert set(contacts) == set(paths)
    for ident, vertices in paths.items():
        old = contacts[ident]
        net, width = old.GetNetname(), pcb.ToMM(old.GetWidth())
        assert old.GetLayer() == pcb.B_Cu
        board.Remove(old)
        track_chain(board, net, pcb.B_Cu, width, vertices, f"Q1/{ident}")


def q1_terminals(board):
    assert board.BuildConnectivity()
    pairs = [("U20", "15", "R100", "1"), ("R100", "2", "Q1", "1"),
             ("R200", "1", "Q1", "1"), ("R200", "2", "Q1", "2"),
             ("U20", "8", "Q1", "2"), ("Q1", "3", "V1", "3")]
    results = {}
    for a, i, b, j in pairs:
        left, right = (pads(board.FindFootprintByReference(ref))[pin]
                       for ref, pin in ((a, i), (b, j)))
        assert left.GetNetname() == right.GetNetname()
        linked = {uid(item) for item in board.GetConnectivity().GetConnectedItems(left)}
        results[f"{a}.{i}–{b}.{j}"] = uid(right) in linked
    return results


def relocate_group(board, references, centre, clockwise, shift):
    """Move a cluster and every existing track in its fully internal connections."""
    assert board.BuildConnectivity()
    group = [board.FindFootprintByReference(ref) for ref in references]
    connected = board.GetConnectivity()
    cluster_tracks = {}
    for footprint in group:
        for pad in footprint.Pads():
            component = connected.GetConnectedItems(pad)
            segments = [item for item in component if isinstance(item, pcb.PCB_TRACK)]
            if segments:
                terminals = {item.GetParentFootprint().GetReference() for item in component
                             if isinstance(item, pcb.PAD)}
                assert terminals <= set(references), (references, terminals)
                assert all(isinstance(item, (pcb.PCB_TRACK, pcb.PAD)) for item in component)
                assert all(item.GetClass() == "PCB_TRACK" for item in segments)
                cluster_tracks.update({uid(item): item for item in segments})
    for item in [*group, *cluster_tracks.values()]:
        item.Rotate(point(*centre), pcb.EDA_ANGLE(-clockwise, pcb.DEGREES_T))
        item.Move(point(*shift))


def retract_base_vias(board):
    """Pull back the six existing lower-row vias past the new collector edges."""
    assert board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    moves = []
    for via in board.GetTracks():
        if isinstance(via, pcb.PCB_VIA):
            x, y = xy(via.GetPosition())
            net = via.GetNetname()
            if BASE_VIAS.get(net) == x and y == 119.25:
                moves.append((via, x, y, net, list(connectivity.GetConnectedTracks(via))))
    assert len(moves) == len(BASE_VIAS)
    for via, x, y, net, segments in moves:
        previous, moved = point(x, y), point(x, y + 0.125)
        assert len(segments) == 2, net
        for segment in segments:
            if segment.GetStart() == previous:
                adjust, far = segment.SetStart, segment.GetEnd()
            else:
                assert segment.GetEnd() == previous, net
                adjust, far = segment.SetEnd, segment.GetStart()
            if far.y == previous.y:
                corner = x + (0.125 if far.x > previous.x else -0.125)
                adjust(point(corner, y))
                trace(board, net, segment.GetLayer(), pcb.ToMM(segment.GetWidth()),
                      (corner, y), xy(moved), f"{net}/via-retreat")
            else:
                assert far.x == previous.x, net
                adjust(moved)
        via.SetPosition(moved)


def route_boundaries(board):
    for i, (net, layer, width, vertices) in enumerate(ROUTES):
        track_chain(board, net, layer, width, vertices, f"{net}/boundary/{i}")
    for i, at in enumerate(((71.875, 99.375), (65.75, 95.25))):
        through_via(board, "ANODE_1", at, f"ANODE_1/boundary/via/{i}")
    # R60.1 is now on the existing same-net R306–C47 trunk. Make its
    # tap a trace endpoint within the land, preserving the two trunk branches.
    trunk = next(t for t in board.GetTracks()
                 if uid(t) == "a1922d00-7405-4c97-81a5-14e3f118488a")
    junction, end = (146.25, 89.50), xy(trunk.GetEnd())
    assert trunk.GetNetname() == "HV_BUS" and end == (146.25, 90.75)
    trunk.SetEnd(point(*junction))
    trace(board, "HV_BUS", pcb.F_Cu, .30, junction, end, "R60.1/HV_BUS/tap")


def through_via(board, net, position, label):
    via = pcb.PCB_VIA(board)
    via.SetUuidDirect(new_id(label))
    via.SetPosition(point(*position))
    via.SetViaType(pcb.VIATYPE_THROUGH)
    via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    via.SetWidth(pcb.FromMM(.60))
    via.SetDrill(pcb.FromMM(.30))
    via.SetNet(board.FindNet(net))
    board.Add(via)


def refine_boundaries(board):
    for refs, shift in BIAS_PLACEMENTS:
        for index in refs:
            board.FindFootprintByReference(f"R{index}").Move(point(*shift))
    for ref, shift, clockwise in LOCAL_PLACEMENTS:
        footprint = board.FindFootprintByReference(ref)
        footprint.Rotate(footprint.GetPosition(), pcb.EDA_ANGLE(-clockwise, pcb.DEGREES_T))
        footprint.Move(point(*shift))
    relocate_group(board, ("R84", "R85"), (171, 73), 180, (0, -1))

    # C33's ground branch terminates on the rotated decoupler's land.
    ground = next(t for t in board.GetTracks()
                  if uid(t) == "ab72f857-2f7d-47dd-a180-4877e349886f")
    assert ground.GetNetname() == "GND" and xy(ground.GetStart()) == (125.775, 83)
    ground.SetStart(pads(board.FindFootprintByReference("C33"))["2"].GetPosition())
    for i, (net, layer, width, vertices) in enumerate(MONITOR_FANOUT):
        track_chain(board, net, layer, width, vertices, f"{net}/monitor/{i}")
    through_via(board, "HV_FB", (166, 73.625), "HV_FB/monitor/via")
    through_via(board, "HV_BUS", (145.5, 82.25), "HV_BUS/monitor/via")


def route_q2(board):
    board.FindFootprintByReference("Q2").Move(point(*Q2_SHIFT))
    for i, (net, layer, width, vertices) in enumerate(Q2_ROUTES):
        track_chain(board, net, layer, width, vertices, f"Q2/{net}/route/{i}")
    for net, positions in Q2_VIAS.items():
        for i, at in enumerate(positions):
            through_via(board, net, at, f"Q2/{net}/via/{i}")


def rules(out):
    frozen = (FROZEN / f"{OLD_STEM}.kicad_dru").read_text(encoding="utf-8")
    frozen = frozen.replace("# A provisional copper screen. See PCB_LAYOUT.md for the assumptions and open qualification.",
                            "# P01 screening minima. See ../P01_CLEARANCE_DECISION.md.")
    pins = ("J2", "J3", "J4", "J5", "J6", "U3", "U4")
    external = [(side, " || ".join(f"{side}.memberOfFootprint('{ref}')" for ref in pins))
                for side in ("A", "B")]
    hv = {side: " || ".join(f"{side}.NetName == '{net}'" for net in HV) for side, _ in external}
    interface = (f"(({external[0][1]}) && ({hv['B']})) || "
                 f"(({external[1][1]}) && ({hv['A']}))")
    rule = ('# Report connector and MCU footprint boundaries with their own rule name.\n'
            '(rule "P01 HV to interface and MCU copper screen"\n'
            f'    (condition "{interface}")\n'
            '    (constraint clearance (min 2.00mm)))\n\n'
            '# Switch rule has higher priority. No same-package clearance exceptions.\n')
    frozen = frozen.replace('(rule "Switch node provisional repetitive-peak screen"', rule +
                            '(rule "Switch node provisional repetitive-peak screen"')
    (out / f"{STEM}.kicad_dru").write_text(frozen, encoding="utf-8")


def make_project(out, q1_only):
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FROZEN / "R10_R10.pretty", out / "R10_R10.pretty", dirs_exist_ok=True)
    local_library = out / "R14_4.pretty"
    local_library.mkdir(exist_ok=True)
    shutil.copyfile(HERE.parent / "r14_3" / "candidate" / "R14_3.pretty" / f"{LAND}.kicad_mod",
                    local_library / f"{LAND}.kicad_mod")
    for name in ("sym-lib-table", "R10_R10.kicad_sym"):
        shutil.copyfile(FROZEN / name, out / name)
    table = (FROZEN / "fp-lib-table").read_text(encoding="utf-8").rstrip()
    table = table[:-1] + ('\n (lib (name "R14_4") (type "KiCad")'
                         ' (uri "${KIPRJMOD}/R14_4.pretty") (options "")'
                         ' (descr "R14.4 manufacturer nominal land patterns")))\n')
    (out / "fp-lib-table").write_text(table, encoding="utf-8")
    project = (FROZEN / f"{OLD_STEM}.kicad_pro").read_text(encoding="utf-8")
    (out / f"{STEM}.kicad_pro").write_text(project.replace(OLD_STEM, STEM), encoding="utf-8")
    included = {"Q1"} if q1_only else DISPLAY_Q
    changed = 0
    for sheet in FROZEN.glob("*.kicad_sch"):
        data = sheet.read_text(encoding="utf-8").replace(f'(project "{OLD_STEM}"',
                                                         f'(project "{STEM}"')
        if sheet.stem.startswith("Cathodes_"):
            for ref in sorted(included):
                pattern = rf'(\(property "Reference" "{ref}" [^\n]+\n[^\n]+\n\(property "Footprint" "){OLD_FPID}(")'
                data, count = re.subn(pattern, rf"\g<1>{FPID}\g<2>", data)
                changed += count
        name = f"{STEM}.kicad_sch" if sheet.stem == OLD_STEM else sheet.name
        (out / name).write_text(data, encoding="utf-8")
    assert changed == len(included), changed
    rules(out)
    return local_library


def build(out, q1_only):
    local_library = make_project(out, q1_only)
    board = pcb.LoadBoard(str(FROZEN / f"{OLD_STEM}.kicad_pcb"))
    assert all(q1_terminals(board).values())
    old = board.FindFootprintByReference("Q1")
    assert xy(old.GetPosition()) == (60.5, 115) and old.IsFlipped()
    assert {pin: pad.GetNetname() for pin, pad in pads(old).items()} == {
        "1": "BASE_00", "2": "GND", "3": "K1_0"}
    conn = board.GetConnectivity()
    contacts = {uid(track): track for pad in pads(old).values()
                for track in conn.GetConnectedTracks(pad)}
    replace_transistor(board, old, local_library)
    reroute_q1(board, contacts)
    q1 = q1_terminals(board)
    if not all(q1.values()):
        raise RuntimeError(f"Q1 copper regression before Q2–Q30: {q1}")
    print(json.dumps(q1, ensure_ascii=False))
    if not q1_only:
        for n in range(2, 31):
            replace_transistor(board, board.FindFootprintByReference(f"Q{n}"), local_library)
        for placement in PLACEMENTS:
            relocate_group(board, *placement)
        retract_base_vias(board)
        route_boundaries(board)
        refine_boundaries(board)
        route_q2(board)
    assert pcb.SaveBoard(str(out / f"{STEM}.kicad_pcb"), board)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "eda")
    parser.add_argument("--q1-only", action="store_true")
    args = parser.parse_args()
    build(args.out.resolve(), args.q1_only)
