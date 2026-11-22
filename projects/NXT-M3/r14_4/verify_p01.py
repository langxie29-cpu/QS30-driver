"""Run the native P01 regression and emit traceable engineering audit tables."""

import argparse
from collections import Counter
import csv
from itertools import combinations
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as xml

import pcbnew as pcb

from build_p01 import FROZEN, FPID, HERE, OLD_STEM, Q2_SHIFT, STEM, pads, point, q1_terminals, uid, xy
sys.path.insert(0, str(FROZEN.parent))
from verify_r14_1 import audit_board

CLI = Path(sys.executable).with_name("kicad-cli.exe")
CASES = {
    "before": FROZEN / OLD_STEM,
    "coupon": HERE.parent / "r14_3/candidate/R14_3-protection-coupon",
    "after": HERE / "eda" / STEM,
}
LAYERS = pcb.F_Cu, pcb.B_Cu, pcb.In1_Cu, pcb.In2_Cu
INTERFACES = {"J2", "J3", "J4", "J5", "J6", "U3", "U4"}
SWITCH = {"SW_HV", "SNUB"}
DISPLAY_Q = {f"Q{number}" for number in range(1, 31)}
TERMINALS = (
    ("R302", "2", "R303", "1"), ("R303", "2", "V1", "1"),
    ("R60", "2", "R61", "1"), ("R61", "2", "R62", "1"),
    ("R62", "2", "R63", "1"), ("R63", "2", "R64", "1"),
    ("R65", "2", "R66", "1"), ("R66", "2", "R67", "1"),
    ("R81", "2", "R82", "1"), ("R82", "2", "R83", "1"),
    ("R84", "2", "R85", "1"), ("L3", "2", "Q32", "2"),
    ("D3", "2", "Q32", "2"), ("D3", "2", "R86", "1"),
    ("R86", "2", "C48", "1"),
    ("R60", "1", "R306", "1"), ("R60", "1", "C47", "1"),
    ("R304", "2", "R305", "1"), ("R305", "2", "V2", "1"),
    ("R306", "1", "R65", "1"), ("R85", "1", "U17", "8"),
    ("R83", "2", "R84", "1"),
)
Q2_TERMINALS = (
    ("U20", "1", "R101", "1"), ("R101", "2", "Q2", "1"), ("R201", "1", "Q2", "1"),
    ("R201", "2", "Q2", "2"), ("U20", "8", "Q2", "2"), ("Q2", "3", "V1", "13"),
)

# Targets are intentionally voltage- and pin-specific. The same-layer connector
# sweep below also includes vias, routed copper and filled zones.
TARGETS = (
    ("R302", "1", "U3", "18"), ("R302", "1", "U3", "17"),
    ("R302", "1", "U3", "15"), ("R302", "1", "U3", "16"),
    ("R302", "1", "C11", "1"), ("R302", "1", "J2", "1"),
    ("R302", "2", "U4", "3"), ("R302", "2", "U4", "4"),
    ("R302", "2", "J2", "3"), ("R303", "1", "U4", "3"),
    ("R303", "1", "U4", "4"), ("R303", "1", "J2", "4"),
    ("R303", "2", "C12", "1"), ("R303", "2", "C12", "2"),
    ("R303", "2", "U24", "1"), ("R303", "2", "U24", "5"),
    ("R60", "1", "R52", "1"), ("R60", "1", "R52", "2"),
    ("R60", "1", "R53", "1"), ("R60", "1", "C34", "2"),
    ("R61", "1", "U13", "5"), ("R61", "2", "U14", "4"),
    ("R61", "2", "U14", "3"), ("R62", "1", "D1", "1"),
    ("R62", "1", "J3", "1"), ("R65", "1", "R64", "2"),
    ("R305", "2", "C33", "1"), ("R81", "2", "C42", "2"),
    ("R81", "2", "C43", "1"), ("R83", "1", "C44", "1"),
    ("R84", "1", "R67", "2"), ("R81", "1", "R65", "2"),
    ("Q2", "3", "R101", "2"),
    ("D3", "2", "U17", "7"), ("D3", "2", "U17", "8"),
    ("D3", "1", "D3", "2"), ("C48", "1", "C48", "2"),
    ("C48", "1", "R82", "1"), ("R86", "1", "R65", "1"),
    ("R86", "2", "R66", "1"), ("Q32", "2", "Q32", "1"),
    ("Q32", "2", "Q32", "3"),
)


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def eda_file(stem, ext):
    return stem.parent / f"{stem.name}.kicad_{ext}"


def native(out):
    logs = []

    def run(args, allowed):
        proc = subprocess.run([CLI, *args], cwd=HERE.parent, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        logs.append(dict(args=args, exit_code=proc.returncode, stdout=proc.stdout,
                         stderr=proc.stderr))
        write_json(out / "native_commands.json", logs)
        if proc.returncode not in allowed or proc.stderr.strip():
            raise RuntimeError(logs[-1])
        return proc.stdout.strip()

    assert run(["version"], {0}) == "10.0.8"
    relative = lambda path: Path(os.path.relpath(path, HERE.parent)).as_posix()
    for case, stem in CASES.items():
        dest = out / case
        dest.mkdir(exist_ok=True)
        native_project = relative(eda_file(stem, "sch"))
        native_board = relative(eda_file(stem, "pcb"))
        run(["sch", "export", "netlist", "--format", "kicadxml", "-o",
             relative(dest / "netlist.xml"), native_project], {0})
        for kind, fmt in (("json", "json"), ("rpt", "report")):
            run(["sch", "erc", "--severity-all", "--exit-code-violations", "--format", fmt,
                 "-o", relative(dest / f"ERC.{kind}"), native_project], {0})
            run(["pcb", "drc", "--schematic-parity", "--severity-all", "--exit-code-violations",
                 "--format", fmt, "-o", relative(dest / f"DRC.{kind}"), native_board], {0, 5})
    # All-track reporting can find extra objects near the same route. Keep it
    # alongside the like-for-like baseline mode instead of mixing the counts.
    for case in ("before", "after"):
        run(["pcb", "drc", "--all-track-errors", "--schematic-parity", "--severity-all",
             "--exit-code-violations", "--format", "json",
             "-o", relative(out / case / "DRC-all-tracks.json"),
             relative(eda_file(CASES[case], "pcb"))], {0, 5})
    with tempfile.TemporaryDirectory(prefix=".p01-rule-probe-", dir=HERE) as temp:
        scratch = Path(temp)
        stem = scratch / OLD_STEM
        # Replay the frozen placements with the candidate rules. The real
        # overlapping pairs exercise rule resolution without editing either PCB.
        for extension in ("pcb", "pro"):
            shutil.copyfile(eda_file(CASES["before"], extension), eda_file(stem, extension))
        shutil.copyfile(FROZEN / "fp-lib-table", scratch / "fp-lib-table")
        shutil.copytree(FROZEN / "R10_R10.pretty", scratch / "R10_R10.pretty")
        shutil.copyfile(eda_file(CASES["after"], "dru"), eda_file(stem, "dru"))
        run(["pcb", "drc", "--severity-all", "--exit-code-violations", "--format", "json",
             "-o", relative(scratch / "probe.json"), relative(eda_file(stem, "pcb"))], {5})
        probe = read_json(scratch / "probe.json")
    rules = Counter(re.search(r"'([^']+)'", v["description"]).group(1)
                    for v in probe["violations"] if re.search(r"'([^']+)'", v["description"]))
    assert rules["P01 HV to interface and MCU copper screen"] == 13, rules
    assert rules["HV bus and display conservative creepage screen"] == 188, rules
    assert rules["Switch node provisional repetitive-peak screen"] == 18, rules
    assert {drc_key(v) for v in probe["violations"]} == {
        drc_key(v) for v in read_json(out / "before/DRC.json")["violations"]}
    write_json(out / "native_rule_resolution.json", dict(
        method="KiCad CLI native DRC on frozen geometry with delivered R14.4 rules",
        total=len(probe["violations"]), resolved_rule_counts=rules,
        examples=[
            entry for entry in probe["violations"] if
            any(re.search(r"\b(R302|R60|D3|Q1)\b", item["description"]) for item in entry["items"])
        ],
    ))


def category_of_net(net):
    if net in SWITCH:
        return "switch"
    if re.fullmatch(r"K\d+_\d+", net) or net.startswith(("ALIM_", "ANODE_")):
        return "display"
    if net == "HV_BUS":
        return "bus"
    if net.startswith(("BLEED_", "HV_FB_", "HV_OVP_S_", "HV_RES_S_")):
        return "divider"
    return "lv"


class Board:
    def __init__(self, stem):
        self.board = pcb.LoadBoard(str(eda_file(stem, "pcb")))
        assert self.board.BuildConnectivity()
        self.conn = self.board.GetConnectivity()
        self.refs = {f.GetReference(): f for f in self.board.GetFootprints()}
        self.pads = [pad for fp in self.refs.values() for pad in fp.Pads()]
        self.copper = [*self.pads, *self.board.GetTracks(),
                       *(z for z in self.board.Zones() if z.IsFilled())]
        self.by_id = {uid(item): item for item in [*self.refs.values(), *self.copper]}
        self.shapes = {}

    def pad(self, ref, pin):
        return pads(self.refs[ref])[pin]

    def layers(self, item):
        return tuple(layer for layer in LAYERS if item.IsOnLayer(layer))

    def info(self, item):
        if isinstance(item, pcb.PAD):
            ref = item.GetParentFootprint().GetReference()
            return ref, item.GetNumber(), item.GetNetname()
        if isinstance(item, pcb.FOOTPRINT):
            return item.GetReference(), "", ""
        return "", "", item.GetNetname() if hasattr(item, "GetNetname") else ""

    def polygon(self, item, layer):
        key = uid(item), layer
        if key not in self.shapes:
            if isinstance(item, pcb.ZONE):
                poly = item.GetFilledPolysList(layer)
            else:
                poly = pcb.SHAPE_POLY_SET()
                item.TransformShapeToPolygon(poly, layer, 0, pcb.FromMM(.0001), pcb.ERROR_OUTSIDE)
            segments, points = [], []
            for i in range(poly.OutlineCount()):
                rings = [poly.COutline(i)] + [poly.CHole(i, j) for j in range(poly.HoleCount(i))]
                for ring in rings:
                    edge = [ring.CPoint(j) for j in range(ring.PointCount())]
                    if edge:
                        points.append(edge[0])
                    segments.extend(pcb.SEG(a, b) for a, b in zip(edge, edge[1:] + edge[:1]))
            self.shapes[key] = poly, segments, points
        return self.shapes[key]

    def copper_gap(self, a, b, layer):
        ap, aa, ax = self.polygon(a, layer)
        bp, ba, bx = self.polygon(b, layer)
        if not aa or not ba:
            return math.inf
        if any(ap.Contains(v) for v in bx) or any(bp.Contains(v) for v in ax):
            return 0.0
        return pcb.ToMM(min(u.Distance(v) for u in aa for v in ba))

    def nearest(self, left, right):
        best = math.inf
        result = None
        right = [(item, self.layers(item), item.GetBoundingBox()) for item in right]
        for a in left:
            al = self.layers(a)
            ab = a.GetBoundingBox()
            for b, bl, bb in right:
                layers = set(al).intersection(bl)
                if not layers or uid(a) == uid(b) or self.info(a)[2] == self.info(b)[2]:
                    continue
                ax, ay = xy(ab.GetOrigin())
                ar, at = xy(ab.GetEnd())
                bx, by = xy(bb.GetOrigin())
                br, bt = xy(bb.GetEnd())
                if math.hypot(max(ax-br, bx-ar, 0), max(ay-bt, by-at, 0)) >= best:
                    continue
                for layer in sorted(layers):
                    gap = self.copper_gap(a, b, layer)
                    if gap < best:
                        best, result = gap, (a, b, layer)
        return best, result

    def connected(self, left, right):
        return uid(right) in {uid(item) for item in self.conn.GetConnectedItems(left)}

    def pad_components(self):
        remaining = {uid(p): p for p in self.pads if p.GetNumber() and p.GetNetname()}
        result = {}
        while remaining:
            ident, pad = next(iter(remaining.items()))
            found = {uid(item) for item in self.conn.GetConnectedItems(pad)
                     if isinstance(item, pcb.PAD) and item.GetNumber()}
            found.add(ident)
            assert all(self.by_id[k].GetNetname() == pad.GetNetname() for k in found)
            group = frozenset(found)
            for key in group:
                assert key not in result or result[key] == group
                result[key] = group
                remaining.pop(key, None)
        return result


def get_open_nets(board, report):
    nets = Counter()
    for entry in report["unconnected_items"]:
        linked = {board.info(board.by_id[obj["uuid"]])[2] for obj in entry["items"]}
        assert len(linked) == 1 and "" not in linked, entry
        nets[linked.pop()] += 1
    return nets


def schematic_pins(path):
    tree = xml.parse(path)
    return {(pin.get("ref"), pin.get("pin")): net.get("name") for net in tree.findall("nets/net")
            for pin in net.findall("node")}


def metrics(report, erc):
    result = dict(Counter(entry["severity"] for sheet in erc["sheets"]
                          for entry in sheet["violations"]))
    return dict(erc_errors=result.get("error", 0), erc_warnings=result.get("warning", 0),
                clearance=sum(v["type"] == "clearance" for v in report["violations"]),
                drc_other=sum(v["type"] != "clearance" for v in report["violations"]),
                unconnected=len(report["unconnected_items"]),
                parity=len(report["schematic_parity"]))


def drc_key(entry):
    return entry["type"], tuple(sorted(item["uuid"] for item in entry["items"]))


def classify(infos, required):
    refs = [ref for ref, _, _ in infos]
    nets = {net for _, _, net in infos}
    kinds = {category_of_net(net) for net in nets}
    same = len(refs) == 2 and refs[0] and refs[0] == refs[1]
    if "switch" in kinds:
        return "switch_package" if same else "switch_external"
    if same and refs[0] in DISPLAY_Q and {pin for _, pin, _ in infos} in ({"1", "3"}, {"2", "3"}):
        return "mmbta42_candidate_exception"
    if required is not None and required >= 2:
        if same:
            return "hv_other_same_package"
        if INTERFACES.intersection(refs):
            return "hv_interface_mcu"
        return "hv_lv_external" if "lv" in kinds else "hv_internal_external"
    return "lv_same_package" if same else "other"


def objects_record(board, entry):
    details = []
    for raw in sorted(entry["items"], key=lambda item: item["uuid"]):
        obj = board.by_id.get(raw["uuid"])
        info = board.info(obj) if obj is not None else ("", "", "")
        layers = "|".join(board.board.GetLayerName(l) for l in board.layers(obj)) if obj else ""
        pos = raw["pos"]
        details.append((*info, layers, pos["x"], pos["y"], raw["uuid"], raw["description"]))
    return details


def drc_distances(entry):
    mm = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*mm", entry["description"])
    return (float(mm[0]), float(mm[1])) if len(mm) == 2 else (None, None)


def diff_drc(out, before, after, a, b):
    raw = [{drc_key(entry): entry for entry in report["violations"]} for report in (a, b)]
    rows = []
    for key in sorted(set(raw[0]) | set(raw[1])):
        old, new = [index.get(key) for index in raw]
        prior = objects_record(before, old) if old else []
        final = objects_record(after, new) if new else []
        required, _ = drc_distances(new or old)
        category = classify([info[:3] for info in (final or prior)], required)
        action = ("retained" if old and new else "removed" if old else "added")
        row = dict(type=key[0], category=category, disposition=action,
                   signature="|".join(key[1]), required_mm=required)
        if action == "removed":
            row["handling"] = "Relayout / land or route changed; pair absent in native DRC"
            if len(key[1]) == 2 and all(ident in after.by_id for ident in key[1]):
                left, right = (after.by_id[ident] for ident in key[1])
                gap, result = after.nearest([left], [right])
                if result:
                    row["after_geometry_mm"] = f"{gap:.6f}"
        elif category == "mmbta42_candidate_exception":
            row["handling"] = "Open candidate exception; no DRC suppression or insulation approval"
        elif category == "switch_package":
            row["handling"] = "Retained 3.20 mm; qualify package and peaks or change package"
        elif category == "lv_same_package":
            row["handling"] = "Separate low-voltage land-pattern DFM review"
        else:
            row["handling"] = "Retained for placement, routing or manufacturing review"
        for when, entry, records in (("before", old, prior), ("after", new, final)):
            _, actual = drc_distances(entry) if entry else (None, None)
            row[f"{when}_mm"] = actual
            row[f"{when}_native"] = entry["description"] if entry else ""
            for i, details in enumerate(records, 1):
                for field, value in zip(("ref", "pad", "net", "layers", "x", "y", "uuid", "description"), details):
                    row[f"{when}_{i}_{field}"] = value
            if entry:
                common = set.intersection(*(set(detail[3].split("|")) for detail in records)) if records else set()
                row[f"{when}_common_layers"] = "|".join(sorted(common - {""}))
        rows.append(row)
    fields = ["type", "category", "disposition", "handling", "signature", "required_mm", "after_geometry_mm"]
    for when in ("before", "after"):
        fields.extend([f"{when}_mm", f"{when}_native", f"{when}_common_layers"])
        fields.extend(f"{when}_{i}_{field}" for i in (1, 2)
                      for field in ("ref", "pad", "net", "layers", "x", "y", "uuid", "description"))
    write_csv(out.parent / "P01_DRC_BEFORE_AFTER.csv", fields, rows)
    return rows


def local_gap(pad_a, pad_b):
    assert all(pad.GetOrientation().AsDegrees() == 0 for pad in (pad_a, pad_b))
    ax, ay = xy(pad_a.GetPosition())
    bx, by = xy(pad_b.GetPosition())
    aw, ah = xy(pad_a.GetSize())
    bw, bh = xy(pad_b.GetSize())
    rr = sum(pcb.ToMM(pad.GetRoundRectCornerRadius()) for pad in (pad_a, pad_b)
             if pad.GetShape() == pcb.PAD_SHAPE_ROUNDRECT)
    return math.hypot(max(0, abs(ax-bx)-(aw+bw)/2+rr),
                      max(0, abs(ay-by)-(ah+bh)/2+rr)) - rr


def q_audit(out, before, after):
    rows = []
    for k in range(30):
        ref = f"Q{k+1}"
        old, new = (board.refs[ref] for board in (before, after))
        assert new.GetFPIDAsString() == FPID and new.GetOrientation().AsDegrees() == 0 and new.IsFlipped()
        assert new.GetPosition() - old.GetPosition() == point(*(Q2_SHIFT if ref == "Q2" else (0, 0)))
        assert len(list(new.Pads())) == 3
        expected = (f"BASE_{k:02d}", "GND", f"K{k//10+1}_{k%10}")
        prior, final = pads(old), pads(new)
        pair_columns = {}
        for i, j in combinations(final, 2):
            for when, group in (("before", prior), ("after", final)):
                pair_columns[f"{when}_{i}_{j}_gap_mm"] = f"{local_gap(group[i], group[j]):.6f}"
        for i, (pin, role, dx, dy) in enumerate((("1", "B", -1, .95), ("2", "E", -1, -.95),
                                                ("3", "C", 1, 0))):
            old_pad, pad = prior[pin], final[pin]
            offset = pad.GetPosition() - new.GetPosition()
            assert uid(old_pad) == uid(pad)
            assert old_pad.GetNetname() == pad.GetNetname() == expected[i]
            assert pad.GetShape() == pcb.PAD_SHAPE_RECT and xy(offset) == (dx, dy)
            assert xy(pad.GetSize()) == (.9, .8)
            assert set(pad.GetLayerSet().Seq()) == {pcb.B_Cu, pcb.B_Mask, pcb.B_Paste}
            assert pad.GetSolderMaskExpansion(pcb.B_Mask) == 0
            assert xy(pad.GetSolderPasteMargin(pcb.B_Paste)) == (0, 0)
            connected_count = [len(board.conn.GetConnectedItems(item))
                               for board, item in ((before, old_pad), (after, pad))]
            if ref == "Q2":
                assert connected_count[0] == 1 and connected_count[1] > 1, (pin, connected_count)
            elif k:
                assert connected_count == [1, 1], (ref, pin, connected_count)
            rows.append(dict(ref=ref, pin=pin, pin_function=role, net=expected[i], uuid=uid(pad),
                             layers="B.Cu|B.Mask|B.Paste", angle=new.GetOrientation().AsDegrees(),
                             before_x=xy(old_pad.GetPosition())[0], before_y=xy(old_pad.GetPosition())[1],
                             after_x=xy(pad.GetPosition())[0], after_y=xy(pad.GetPosition())[1],
                             after_size_x_mm=.9, after_size_y_mm=.8, mask_expansion_mm=0, paste_margin_mm=0,
                             before_direct_tracks=len(before.conn.GetConnectedTracks(old_pad)),
                             after_direct_tracks=len(after.conn.GetConnectedTracks(pad)),
                             before_copper_component_items=connected_count[0],
                             after_copper_component_items=connected_count[1], **pair_columns))
    write_csv(out.parent / "MMBTA42_PAD_INTEGRATION.csv", list(rows[0]), rows)
    return rows


def coupon_audit(coupon):
    results = []
    for n in range(1, 4):
        transistor = pads(coupon.refs[f"Q{n}"])
        diode = pads(coupon.refs[f"D{n}"])
        cb = local_gap(transistor["1"], transistor["3"])
        ce = local_gap(transistor["2"], transistor["3"])
        # Coupon diode orientation is 180 degrees; use its native pad shapes.
        diode_gap, measured = coupon.nearest([diode["1"]], [diode["2"]])
        assert measured and round(diode_gap, 4) == 1.5000
        assert round(cb, 4) == round(ce, 4) == 1.1102
        results.append(dict(channel=n, collector_base_mm=round(cb, 6),
                            collector_emitter_mm=round(ce, 6), diode_mm=round(diode_gap, 6)))
    return results


def mechanical(before, after):
    def signature(board):
        items = {ref: footprint for ref, footprint in board.refs.items()
                 if ref.startswith("MH") or ref in INTERFACES or re.fullmatch(r"V[1-9]", ref)}
        footprints = {ref: (xy(fp.GetPosition()), fp.GetOrientation().AsDegrees(),
                            tuple((p.GetNumber(), xy(p.GetPosition()), xy(p.GetDrillSize()))
                                  for p in fp.Pads()))
                      for ref, fp in items.items()}
        outline = [(xy(x.GetStart()), xy(x.GetEnd())) for x in board.board.GetDrawings()
                   if x.GetLayer() == pcb.Edge_Cuts]
        return footprints, outline

    a, b = signature(before), signature(after)
    assert a == b and a[1]
    return dict(unchanged_footprints=sorted(a[0]), edge_cuts_mm=a[1])


def boundary_audit(out, before, after):
    screens = ("bus", "display", "divider", "switch")
    rows = []
    for bb, name in ((before, "before"), (after, "after")):
        for a, i, b, j in TARGETS:
            left, right = bb.pad(a, i), bb.pad(b, j)
            distance, result = bb.nearest([left], [right])
            if result:
                rows.append(boundary_row(bb, name, f"{a}.{i}/{b}.{j}", distance, result))
        for ref in sorted(INTERFACES):
            for screen in screens:
                right = [item for item in bb.copper if category_of_net(bb.info(item)[2]) == screen]
                distance, result = bb.nearest(bb.refs[ref].Pads(), right)
                if result:
                    rows.append(boundary_row(bb, name, f"{ref}/nearest_{screen}", distance, result))
    fields = ["state", "target", "required_mm", "actual_mm", "layer", "ref_a", "pad_a", "net_a",
              "uuid_a", "x_a", "y_a", "ref_b", "pad_b", "net_b", "uuid_b", "x_b", "y_b", "scope"]
    write_csv(out.parent / "P01_HV_LV_BOUNDARY_AUDIT.csv", fields, rows)
    return rows


def boundary_row(board, state, target, distance, result):
    a, b, layer = result
    required = 3.2 if {board.info(a)[2], board.info(b)[2]} & SWITCH else 2
    row = dict(state=state, target=target, required_mm=required, actual_mm=f"{distance:.6f}",
               layer=board.board.GetLayerName(layer), scope="Same-layer copper projection")
    for side, obj in (("a", a), ("b", b)):
        ref, pin, net = board.info(obj)
        x, y = xy(obj.GetPosition())
        row.update({f"ref_{side}": ref, f"pad_{side}": pin, f"net_{side}": net,
                    f"uuid_{side}": uid(obj), f"x_{side}": x, f"y_{side}": y})
    return row


def unresolved(out, drc, integrated):
    rows = []
    for item in (row for row in drc if row["after_native"]):
        category = item["category"]
        objects = [item[f"after_{n}_description"] for n in (1, 2)]
        refs = {item[f"after_{n}_ref"] for n in (1, 2)}
        nets = [item[f"after_{n}_net"] for n in (1, 2)]
        if category == "mmbta42_candidate_exception":
            cause = "Manufacturer land geometry; solder/lead spacing and laminate/mould CTI unknown"
            next_change = "Qualify isolated same-device pad pair and route exits or evaluate ECR-01"
        elif category == "switch_package":
            cause = "Package land spacing under the unidentified repetitive peak"
            next_change = "Evaluate ECR-02, or qualify this exact package and all route exits with measured peaks"
        elif category == "lv_same_package":
            cause = "Same IC manufacturer land pitch under the existing LV netclass rule"
            next_change = "Record fabricator/assembler capability and validate exact LV pins before any local rule"
        elif refs & DISPLAY_Q:
            cause = "Copper of adjacent cathode cells or bias routing too close to HV collector"
            next_change = "Separate the two listed cells / bias landmarks and reserve an outward collector route"
        elif any(net.startswith(("HV_FB_", "HV_RES_S_", "HV_OVP_S_", "BLEED_")) for net in nets):
            cause = "Monitor / bleed chain copper still adjacent to another voltage domain"
            next_change = "Re-space listed chain component and retie its existing copper in a dedicated corridor"
        else:
            cause = "External bus/display copper against unlike adjacent copper"
            next_change = "Move the listed footprint or fan-out; re-run 2.00 mm screen and endpoint audit"
        rows.append(dict(category=category, object_a=objects[0], object_b=objects[1],
                         net_a=nets[0], net_b=nets[1], layer=item["after_common_layers"],
                         x_a=item["after_1_x"], y_a=item["after_1_y"],
                         x_b=item["after_2_x"], y_b=item["after_2_y"],
                         actual_mm=item["after_mm"], required_mm=item["required_mm"],
                         reason=cause, minimum_change_or_evidence=next_change, required_before_fab="yes"))
    for row in integrated:
        if row["ref"] != "Q1" and not row["after_direct_tracks"]:
            rows.append(dict(category="inherited_cathode_open", object_a=f'{row["ref"]}.{row["pin"]}',
                             net_a=row["net"], layer="B.Cu", x_a=row["after_x"], y_a=row["after_y"],
                             reason="Pad is an isolated native copper component in the frozen and revised PCB",
                             minimum_change_or_evidence="Complete local driver return and socket wiring at full clearance",
                             required_before_fab="yes"))
    for obj, net, reason, change in (
        ("R61.2/R62.1", "HV_OVP_S_2", "Existing open after split-layer relocation",
         "Place upper OVP stages and controlled through-via in a common HV corridor; close whole OVP chain"),
        ("U20.1/R101.1", "DRV_01", "Existing open upstream of the newly routed Q2 cell",
         "Provide a low-voltage driver route through the congested cathode fan-out"),
        ("R83.2/R84.1", "HV_FB_3", "Existing open between upper feedback stages",
         "Lay out the feedback and residual dividers in separate corridors and complete the feedback ladder"),
        ("R86.1/D3.2", "SW_HV", "Existing open; switch-to-snubber loop remains incomplete",
         "Route a short 3.20 mm switch branch using actual power-loop geometry"),
        ("R86.2/C48.1", "SNUB", "Existing open; C48 current land blocks a compliant launch",
         "Evaluate long-land-spacing C48 replacement and reconnect R86, C48 and power return"),
        ("SW_HV/SNUB peaks", "SW_HV/SNUB", "Maximum transient and repetitive peak UNKNOWN",
         "Archive v(SW_HV), v(SNUB) and differential positive/negative peaks across applicable states"),
        ("PCB + assembled solder joints", "", "Laminate grade/CTI and worst-case assembly paths unqualified",
         "Obtain material/CTI, tolerances and measured air/creepage paths before approving fabrication"),
    ):
        rows.append(dict(category="release_gate", object_a=obj, net_a=net, reason=reason,
                         minimum_change_or_evidence=change, required_before_fab="yes"))
    fields = ("category", "object_a", "object_b", "net_a", "net_b", "layer", "x_a", "y_a", "x_b", "y_b",
              "actual_mm", "required_mm", "reason", "minimum_change_or_evidence", "required_before_fab")
    write_csv(out.parent / "P01_UNRESOLVED_ITEMS.csv", fields, rows)


def divider_audit(out):
    tree = xml.parse(out / "after/netlist.xml")
    pins = schematic_pins(out / "after/netlist.xml")
    values = {c.get("ref"): c.findtext("value") for c in tree.findall("components/comp")}
    rows = []
    chains = {
        "HV_OVP": range(60, 65), "HV_RES": range(65, 70), "HV_FB": range(81, 86),
        "BLEED_1": range(400, 404), "BLEED_2": range(404, 408),
    }
    for name, indices in chains.items():
        refs = [f"R{i}" for i in indices]
        nets = [pins[(ref, "1")] for ref in refs] + [pins[(refs[-1], "2")]]
        assert all(pins[(ref, "2")] == right for ref, right in zip(refs, nets[1:]))
        assert nets[0] == "HV_BUS" and nets[-1] == "GND"
        r = [1000 * float(re.match(r"([0-9.]+)k\b", values[ref]).group(1)) for ref in refs]
        for mode, fault_index in [("nominal", None), *[(f"{mode} {ref}", i)
                                                       for mode in ("open", "short")
                                                       for i, ref in enumerate(refs)]]:
            rv = r.copy()
            if mode.startswith("short"):
                rv[fault_index] = 0
            for i, (left, right, ref) in enumerate(zip(nets, nets[1:], refs)):
                a_ratio, b_ratio = (float(i <= fault_index), float(i < fault_index)) if mode.startswith("open") else (
                    sum(rv[i:]) / sum(rv), sum(rv[i+1:]) / sum(rv))
                rows.append(dict(chain=name, state=mode, resistor=ref, upper_net=left, lower_net=right,
                                 upper_to_gnd_170_V=round(170*a_ratio, 4), lower_to_gnd_170_V=round(170*b_ratio, 4),
                                 across_170_V=round(170*(a_ratio-b_ratio), 4),
                                 upper_to_gnd_195_V=round(195*a_ratio, 4), lower_to_gnd_195_V=round(195*b_ratio, 4),
                                 across_195_V=round(195*(a_ratio-b_ratio), 4)))
    write_csv(out / "divider_dc_screen.csv", list(rows[0]), rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-cli", action="store_true", help="Use the native reports in evidence/")
    args = parser.parse_args()
    out = HERE / "evidence"
    if not args.skip_cli:
        native(out)
    reports = {case: read_json(out / case / "DRC.json") for case in CASES}
    counts = {case: metrics(report, read_json(out / case / "ERC.json"))
              for case, report in reports.items()}
    before, coupon, after = (Board(CASES[case]) for case in ("before", "coupon", "after"))
    old, new = reports["before"], reports["after"]
    opens = {case: get_open_nets(board, reports[case])
             for case, board in (("before", before), ("coupon", coupon), ("after", after))}
    pad_before, pad_after = before.pad_components(), after.pad_components()
    losses = sorted(key for key, group in pad_before.items() if not group <= pad_after[key])
    assert pad_before.keys() == pad_after.keys()
    assert not losses, [(key, before.info(before.by_id[key])) for key in losses]
    assert not (opens["after"] - opens["before"]), opens["after"] - opens["before"]
    assert schematic_pins(out / "before/netlist.xml") == schematic_pins(out / "after/netlist.xml")
    assert all(count["parity"] == count["erc_errors"] == count["erc_warnings"] == 0
               for count in counts.values()), counts
    assert (counts["before"]["clearance"], counts["before"]["unconnected"]) == (253, 337)
    assert (counts["coupon"]["clearance"], counts["coupon"]["unconnected"]) == (18, 0)
    qa = {name: q1_terminals(board.board) for name, board in (("before", before), ("after", after))}
    assert all(all(result.values()) for result in qa.values())
    rows = q_audit(out, before, after)
    diff = diff_drc(out, before, after, old, new)
    assert not [row for row in diff if row["disposition"] == "added"]
    all_tracks = {case: read_json(out / case / "DRC-all-tracks.json") for case in ("before", "after")}
    extra = {drc_key(v) for v in all_tracks["after"]["violations"]} - {
        drc_key(v) for v in all_tracks["before"]["violations"]}
    assert not extra, extra
    boundary = boundary_audit(out, before, after)
    unresolved(out, diff, rows)
    divider_audit(out)
    terminals = []
    for a, i, b, j in (*TERMINALS, *Q2_TERMINALS):
        row = dict(first=f"{a}.{i}", second=f"{b}.{j}", net=after.pad(a, i).GetNetname())
        for state, board in (("before", before), ("after", after)):
            x, y = board.pad(a, i), board.pad(b, j)
            assert x.GetNetname() == y.GetNetname()
            row[state] = board.connected(x, y)
        terminals.append(row)
    q2 = terminals[-len(Q2_TERMINALS):]
    assert [row["after"] for row in q2] == [False, True, True, True, True, True], q2
    write_csv(out / "terminal_pairs.csv", list(terminals[0]), terminals)
    write_csv(out / "opens_by_net.csv", ("net", "before", "after", "delta"), [
        dict(net=net, before=opens["before"][net], after=opens["after"][net],
             delta=opens["after"][net]-opens["before"][net])
        for net in sorted({*opens["before"], *opens["after"]})])
    stop = {}
    for name, board, report, components in (("before", before, old, pad_before),
                                            ("after", after, new, pad_after)):
        audit = audit_board(eda_file(CASES[name], "pcb"))
        stop[name] = audit["stop"]
        write_json(out / name / "stop_copper_audit.json", audit)
        write_json(out / name / "copper_components.json", {
            "pad_groups": [
                [dict(uuid=pid, ref=board.info(board.by_id[pid])[0],
                      pad=board.info(board.by_id[pid])[1], net=board.info(board.by_id[pid])[2])
                 for pid in sorted(group)]
                for group in sorted(set(components.values()), key=min)
            ],
            "unconnected_signatures": [objects_record(board, entry) for entry in report["unconnected_items"]],
        })
    assert stop["before"] == stop["after"] or all(
        not old["copper_connected"] or new["copper_connected"]
        for old, new in zip(stop["before"], stop["after"]))
    summary = dict(counts=counts, baseline_q1_and_candidate_q1=qa,
                   coupon_land_gaps=coupon_audit(coupon),
                   frozen_mechanical_geometry=mechanical(before, after),
                   before_pad_components=len(set(pad_before.values())),
                   after_pad_components=len(set(pad_after.values())),
                   comparable_pads=len(pad_before), lost_pad_memberships=losses,
                   change_in_native_open_nets={net: opens["after"][net] - opens["before"][net]
                                              for net in sorted(opens["before"])
                                              if opens["before"][net] != opens["after"][net]},
                   all_track_drc={case: len(report["violations"]) for case, report in all_tracks.items()},
                   added_all_track_signatures=len(extra),
                   stop_terminals={name: sum(x["copper_connected"] for x in records)
                                   for name, records in stop.items()},
                   categories={state: dict(Counter(row["category"] for row in diff if row[f"{state}_native"]))
                               for state in ("before", "after")},
                   q2_through_q30_pins_without_local_track=sum(row["ref"] != "Q1" and
                                                               not row["after_direct_tracks"] for row in rows),
                   q2_terminal_check={state: sum(row[state] for row in q2) for state in ("before", "after")},
                   boundary_rows=len(boundary), terminals=terminals)
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
