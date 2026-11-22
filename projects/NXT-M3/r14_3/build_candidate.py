"""Generate and natively audit the separate, low-voltage-only protection coupon."""
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
EDA = HERE / "candidate"
FROZEN = HERE.parent / "r14" / "eda"
STEM = "R14_3-protection-coupon"
sys.path.insert(0, str(HERE.parent / "r10"))
import build_schematic as sch

sch.PROJECT = STEM
sch.LIB = "R14_3"
sch.uid = lambda name: str(uuid5(NAMESPACE_URL, "nxt-m3/r14.3/coupon/" + name))
sch.ROOT = sch.uid("root")
PINMAP = {
    "Diode": "Diode_SMD:D_SMA",
    "R": "Resistor_SMD:R_0805_2012Metric",
    "NPN": "R14_3:Jingdao_MMBTA42_nominal",
    "MOS": "Package_TO_SOT_SMD:SOT-23",
    "TP": "TestPoint:TestPoint_Pad_D1.5mm",
}
JINGDAO = "https://ruelectronics.com/files/Datasheet_MMBTA42_Jingdao-f4487c6fcbed9717aa589a3e4524c22c.pdf"
ES1G = "https://www.diodes.com/datasheet/download/ES1G.pdf"
NEXPERIA = "https://www.nexperia.com/product/2N7002BK"


def parts():
    def part(ref, kind, value, nets, sx, sy, px, py, angle=0, url=""):
        return dict(ref=ref, kind=kind, value=value, status="LV_ONLY",
                    nets={str(i): name for i, name in enumerate(nets, 1)},
                    fp=PINMAP[kind], mpn=value, url=url, sx=sx, sy=sy, px=px, py=py, angle=angle)

    for i, y in enumerate((34, 50, 66), 1):
        sy = 54 + (i-1)*51
        drv, field, base, k = (f"{p}{i}" for p in ("DRV", "FIELD", "BASE", "K"))
        yield part(f"TP{i}", "TP", drv, [drv], 48, sy, 31, y-.95)
        yield part(f"D{i}", "Diode", "ES1G-13-F", [field, drv], 102, sy, 42, y-.95,
                   angle=180, url=ES1G)
        yield part(f"R{i}", "R", "3.0k 1%", [field, base], 157, sy, 52, y-.95)
        yield part(f"R{i+3}", "R", "4.7k 1%", [base, "GND"], 213, sy, 62, y+2.55)
        yield part(f"Q{i}", "NPN", "Jingdao MMBTA42", [base, "GND", k], 271, sy, 70, y,
                   url=JINGDAO)
        yield part(f"TP{i+3}", "TP", k, [k], 329, sy, 93, y)
    yield part("TP7", "TP", "PWM_PERMIT", ["PWM_PERMIT"], 48, 221, 31, 81.05)
    yield part("R7", "R", "100k", ["PWM_PERMIT", "GND"], 110, 221, 62, 84.55)
    yield part("Q4", "MOS", "2N7002BK", ["PWM_PERMIT", "GND", "DRV_IN_MINUS"], 169, 221,
               70, 82, url=NEXPERIA)
    yield part("TP8", "TP", "DRV_IN_MINUS", ["DRV_IN_MINUS"], 227, 221, 93, 82)
    yield part("R8", "R", "10k", ["GATE_BIAS", "DRV_IN_MINUS"], 278, 221, 83, 77)
    yield part("TP9", "TP", "GATE_BIAS", ["GATE_BIAS"], 335, 221, 78, 75)
    yield part("TP10", "TP", "3V3_TAP", ["3V3_TAP"], 48, 255, 31, 93)
    yield part("R9", "R", "1k", ["3V3_TAP", "GND"], 110, 255, 47, 93)
    yield part("TP11", "TP", "GND", ["GND"], 169, 255, 99, 93)


def schematic(items):
    kinds = tuple(PINMAP)
    text = sch.page("reverse block and gate-driver inhibit", sch.ROOT,
                    " ".join(sch.symbol(name, True)[0] for name in kinds))
    text[1] = ('(title_block (title "NXT-M3 R14.3 protection coupon") '
               '(rev "ENGINEERING HOLD") (comment 1 "Low-voltage fixture only. No HV or manufacture."))')
    lib = ['(kicad_symbol_lib (version 20250114) (generator kicad_symbol_editor)']
    lib += [sch.symbol(name)[0] for name in kinds]
    sch.write(EDA / "R14_3.kicad_sym", lib + [")"])
    sch.write(EDA / "sym-lib-table", ["(sym_lib_table (version 7)",
                                     '(lib (name "R14_3") (type "KiCad") '
                                     '(uri "${KIPRJMOD}/R14_3.kicad_sym") (options "") (descr "")))'])
    sch.write(EDA / "fp-lib-table", ["(fp_lib_table (version 7)",
                                    '(lib (name "R14_3") (type "KiCad") '
                                    '(uri "${KIPRJMOD}/R14_3.pretty") (options "") (descr "")))'])
    for item in items:
        placed = sch.place(item, item["sx"], item["sy"], "TOP")
        for line in placed:
            if '(property "MPN"' in line or '(property "Status"' in line:
                continue
            if item["kind"] == "TP":
                line = line.replace("(in_bom yes)", "(in_bom no)")
            text.append(line.replace("/TOP", ""))
    text.extend([sch.note("Drive protection: diode anode faces 595 output. Ground is shared.", 32, 29),
                 sch.note("Gate inhibit interface: remove U18 IN- ground tie in a future ECR.", 32, 197),
                 sch.note("R9 is a shared logic rail load. Its output-side backfeed limit must be verified.",
                          32, 273, 1),
                 '(sheet_instances (path "/" (page "1")))', ")"])
    sch.write(EDA / f"{STEM}.kicad_sch", text)


def point(x, y):
    return pcb.VECTOR2I(round(pcb.FromMM(x)), round(pcb.FromMM(y)))


def footprint_library():
    local = EDA / "R14_3.pretty"
    local.mkdir(exist_ok=True)
    sch.write(local / "Jingdao_MMBTA42_nominal.kicad_mod", [
        '(footprint "Jingdao_MMBTA42_nominal" (version 20241229) (generator pcbnew)',
        '(layer "F.Cu") (attr smd) (descr "Jingdao 2020.12 p.3 nominal metric copper")',
        '(fp_text reference "REF**" (at 0 -2.5) (layer "F.SilkS") '
        '(effects (font (size 0.8 0.8) (thickness 0.12))))',
        '(fp_text value "Jingdao_MMBTA42_nominal" (at 0 2.5) (layer "F.Fab") '
        '(effects (font (size 0.8 0.8) (thickness 0.12))))',
        '(fp_rect (start -.68 -1.48) (end .68 1.48) (stroke (width .1) (type default)) '
        '(fill none) (layer "F.Fab"))',
        '(fp_rect (start -1.8 -1.75) (end 1.8 1.75) (stroke (width .05) (type default)) '
        '(fill none) (layer "F.CrtYd"))',
        '(pad "1" smd rect (at -1 -.95) (size .9 .8) (layers "F.Cu" "F.Paste" "F.Mask"))',
        '(pad "2" smd rect (at -1 .95) (size .9 .8) (layers "F.Cu" "F.Paste" "F.Mask"))',
        '(pad "3" smd rect (at 1 0) (size .9 .8) (layers "F.Cu" "F.Paste" "F.Mask"))', ")"])
    return local


def build_board(items, footprints):
    board = pcb.BOARD()
    local = footprint_library()
    rule = FROZEN / "NXT-M3-R14.kicad_dru"
    extra = """\n(rule "Reverse-block copper screening across diode"
    (condition "(A.NetName == 'DRV*' && B.NetName == 'FIELD*') || (B.NetName == 'DRV*' && A.NetName == 'FIELD*')")
    (constraint clearance (min 2.00mm)))\n"""
    (EDA / f"{STEM}.kicad_dru").write_bytes(rule.read_bytes() + extra.encode())
    shutil.copyfile(FROZEN / "NXT-M3-R14.kicad_pro", EDA / f"{STEM}.kicad_pro")
    nets = {}
    pads = {}
    for name in sorted({net for item in items for net in item["nets"].values()}):
        nets[name] = pcb.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    for item in items:
        library, name = item["fp"].split(":")
        directory = local if library == "R14_3" else footprints / f"{library}.pretty"
        fp = pcb.FootprintLoad(str(directory), name)
        if fp is None:
            raise RuntimeError(f"could not load {item['fp']}")
        fp.SetFPID(pcb.LIB_ID(library, name))
        fp.SetReference(item["ref"])
        fp.SetValue(item["value"])
        fp.GetField(pcb.FIELD_T_DATASHEET).SetText(item["url"])
        fp.SetPosition(point(item["px"], item["py"]))
        fp.SetOrientationDegrees(item["angle"])
        fp.SetPath(pcb.KIID_PATH(f"/{sch.ROOT}/{sch.uid(item['ref'])}"))
        board.Add(fp)
        for pad in fp.Pads():
            pin = pad.GetNumber()
            pad.SetNet(nets[item["nets"][pin]])
            pads[item["ref"], pin] = pad

    def at(ref, pin=1):
        return pads[ref, str(pin)].GetPosition()

    def trace(net, *positions):
        for a, b in zip(positions, positions[1:]):
            if a == b:
                continue
            item = pcb.PCB_TRACK(board)
            item.SetStart(a)
            item.SetEnd(b)
            item.SetLayer(pcb.F_Cu)
            item.SetWidth(pcb.FromMM(.30))
            item.SetNet(nets[net])
            board.Add(item)

    def net_of(ref, pin=1):
        return pads[ref, str(pin)].GetNetname()

    for i, y in enumerate((34, 50, 66), 1):
        diode, resistor, pull, q = f"D{i}", f"R{i}", f"R{i+3}", f"Q{i}"
        trace(f"DRV{i}", at(f"TP{i}"), at(diode, 2))
        trace(f"FIELD{i}", at(diode), at(resistor))
        trace(f"BASE{i}", at(resistor, 2), point(58, y-.95), at(q))
        trace(f"BASE{i}", point(58, y-.95), point(58, y+2.55), at(pull))
        trace(f"K{i}", at(q, 3), at(f"TP{i+3}"))
        trace("GND", at(q, 2), point(69, y+5), point(99, y+5))
        ground = at(pull, 2)
        trace("GND", ground, pcb.VECTOR2I(ground.x, point(0, y+5).y), point(69, y+5))

    trace("PWM_PERMIT", at("TP7"), point(58,81.05), at("Q4"))
    trace("PWM_PERMIT", point(58,81.05), point(58,84.55), at("R7"))
    gpad = at("R7",2)
    epad = at("Q4",2)
    trace("GND", gpad, pcb.VECTOR2I(gpad.x, point(0,87).y), point(69,87),
          point(99,87))
    trace("GND", epad, point(69,87))
    trace("DRV_IN_MINUS", at("Q4",3), point(90,82), at("TP8"))
    trace("DRV_IN_MINUS", at("R8",2), point(90,77), point(90,82))
    trace("GATE_BIAS", at("TP9"), point(78,77), at("R8"))
    trace("3V3_TAP", at("TP10"), at("R9"))
    trace("GND", at("R9",2), point(56,93), at("TP11"))
    trace(net_of("TP11"), *(point(99,y) for y in (39,55,71,87,93)))

    edge = [point(23,24), point(105,24), point(105,98), point(23,98)]
    for a, b in zip(edge, edge[1:]+edge[:1]):
        segment = pcb.PCB_SHAPE(board)
        segment.SetShape(pcb.SHAPE_T_SEGMENT)
        segment.SetStart(a)
        segment.SetEnd(b)
        segment.SetLayer(pcb.Edge_Cuts)
        segment.SetWidth(pcb.FromMM(.05))
        board.Add(segment)
    for label, x, y in (("LOW VOLTAGE ONLY", 58, 27), ("R14.3 HOLD", 92, 27),
                        ("DRIVER", 39, 30), ("COLLECTOR", 90, 30)):
        text = pcb.PCB_TEXT(board)
        text.SetText(label)
        text.SetPosition(point(x, y))
        text.SetTextSize(point(1, 1))
        text.SetTextThickness(pcb.FromMM(.15))
        text.SetLayer(pcb.F_SilkS)
        board.Add(text)
    file = EDA / f"{STEM}.kicad_pcb"
    pcb.SaveBoard(str(file), board)
    return file


def check(cli, file, items):
    evidence = HERE / "evidence" / "candidate"
    evidence.mkdir(parents=True, exist_ok=True)
    env = dict(__import__("os").environ, KICAD10_3RD_PARTY=str(EDA))
    calls = {
        "ERC": ["sch", "erc", "--severity-all", "--exit-code-violations", "--format", "json",
                "-o", str(evidence / "ERC.json"), str(file.with_suffix(".kicad_sch"))],
        "DRC": ["pcb", "drc", "--severity-all", "--schematic-parity", "--exit-code-violations",
                "--format", "json", "-o", str(evidence / "DRC.json"), str(file)],
        "netlist": ["sch", "export", "netlist", "--format", "kicadxml", "-o",
                    str(evidence / "netlist.xml"), str(file.with_suffix(".kicad_sch"))],
    }
    statuses = {}
    for name, args in calls.items():
        run = subprocess.run([cli, *args], env=env, cwd=EDA, capture_output=True, check=False)
        (evidence / f"{name}.log").write_bytes(run.stdout + run.stderr)
        statuses[name] = run.returncode
        if run.returncode not in (0, 5):
            raise RuntimeError(f"KiCad {name} failed: {run.returncode}")
    design = pcb.LoadBoard(str(file))
    if not design.BuildConnectivity():
        raise RuntimeError("KiCad failed to build copper connectivity")
    pad_nets = {(fp.GetReference(), pad.GetNumber()): pad.GetNetname()
                for fp in design.GetFootprints() for pad in fp.Pads()}
    expected = {(item["ref"], pin): net for item in items for pin, net in item["nets"].items()}
    xml = ElementTree.parse(evidence / "netlist.xml")
    pin_nets = {(node.attrib["ref"], node.attrib["pin"]): net.attrib["name"]
                for net in xml.findall("./nets/net") for node in net.findall("node")}
    if not (pin_nets == pad_nets == expected):
        raise AssertionError(dict(pcb_missing=expected.items()-pad_nets.items(),
                                  sch_missing=expected.items()-pin_nets.items()))
    owner = {}
    nets = {}
    for footprint in design.GetFootprints():
        for pad in footprint.Pads():
            nets.setdefault(pad.GetNetname(), []).append(pad)
            owner[str(pad.m_Uuid.AsString())] = footprint.GetReference()
    copper_pairs = []
    copper = design.GetConnectivity()
    for net, pads in sorted(nets.items()):
        a = pads[0]
        connected = {str(p.m_Uuid.AsString()) for p in copper.GetConnectedItems(a)}
        for b in pads[1:]:
            copper_pairs.append([net, owner[str(a.m_Uuid.AsString())], a.GetNumber(),
                                 owner[str(b.m_Uuid.AsString())], b.GetNumber(),
                                 str(b.m_Uuid.AsString()) in connected])
    drc = json.loads((evidence / "DRC.json").read_text(encoding="utf-8"))
    erc = json.loads((evidence / "ERC.json").read_text(encoding="utf-8"))
    result = dict(statuses=statuses, pin_assignments=len(expected), native_copper_pairs=copper_pairs,
                  erc=Counter(item["type"] for sheet in erc["sheets"] for item in sheet["violations"]),
                  drc=Counter(v["type"] for v in drc["violations"]),
                  opens=len(drc["unconnected_items"]), parity=len(drc["schematic_parity"]),
                  nominal_C_to_B_or_E_mm=math.hypot(2-.9,.95-.8),
                  nominal_SMA_pad_gap_mm=4-2.5,
                  low_voltage_only=True)
    (evidence / "audit.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "native_copper_pairs"}))
    assert all(row[-1] for row in copper_pairs)
    assert not result["opens"] and not result["parity"] and not result["erc"]
    assert result["drc"] == {"clearance": 18}, result["drc"]


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Program Files/KiCad/10.0")
    EDA.mkdir(exist_ok=True)
    inventory = list(parts())
    schematic(inventory)
    board = build_board(inventory, root / "share/kicad/footprints")
    check(str(root / "bin/kicad-cli.exe"), board, inventory)
