"""Replay the R14.1 native baseline and calculate the R14.2 evidence."""
from collections import Counter
import argparse
import csv
import hashlib
from itertools import combinations
import json
from math import hypot
import os
from pathlib import Path
import re
import subprocess
import sys

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
BASELINE = "5470020e10f5d6d98f6e21cc93951ca573e20965"
R14 = HERE.parent / "r14"
sys.path.insert(0, str(R14))
import simulate_faults as sim
import verify_r14_1 as baseline


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def native_checks(out):
    cli = Path(sys.executable).with_name("kicad-cli.exe")
    eda = Path("eda") / baseline.STEM
    out_arg = Path(os.path.relpath(out, R14))
    args = [
        (0, ["version"]),
        (0, ["sch", "export", "netlist", "--format", "kicadxml", "-o",
             str(out_arg / "netlist.xml"), str(eda.with_suffix(".kicad_sch"))]),
    ]
    for fmt, ext in (("json", "json"), ("report", "rpt")):
        for exit_code, topic, command, file, source, extra in (
            (0, "sch", "erc", "ERC", ".kicad_sch", []),
            (5, "pcb", "drc", "DRC", ".kicad_pcb", ["--schematic-parity"]),
        ):
            args.append((exit_code, [topic, command, *extra, "--severity-all",
                         "--exit-code-violations", "--format", fmt,
                         "-o", str(out_arg / f"{file}.{ext}"), str(eda.with_suffix(source))]))
    logs = []
    for expected, command in args:
        result = subprocess.run([str(cli), *command], cwd=R14, capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        logs.append(dict(args=command, exit_code=result.returncode,
                         stdout=result.stdout, stderr=result.stderr))
        write_json(out / "native_commands.json", logs)
        if result.returncode != expected:
            raise RuntimeError(logs[-1])
    if logs[0]["stdout"].strip() != "10.0.8":
        raise RuntimeError("This evidence gate requires KiCad 10.0.8")


def geometry(out, board, q1_drc):
    if not board.BuildConnectivity():
        raise RuntimeError("KiCad could not build PCB copper connectivity")
    fp = next(f for f in board.GetFootprints() if f.GetReference() == "Q1")
    origin = baseline.xy(fp.GetPosition())
    if not fp.IsFlipped() or fp.GetOrientation().AsDegrees() != 0:
        raise ValueError("Expected a 0-degree back-side footprint")
    copper, mask = {}, {}
    details = []
    for pad in fp.Pads():
        if pad.GetShape() != pcb.PAD_SHAPE_ROUNDRECT or pad.GetOrientation().AsDegrees() != 0:
            raise ValueError(f"Unexpected Q1 pad shape/rotation: {pad.GetNumber()}")
        x, y = baseline.xy(pad.GetPosition())
        local_x, local_y = x - origin[0], y - origin[1]
        size_x, size_y = baseline.xy(pad.GetSize())
        radius = pcb.ToMM(pad.GetRoundRectCornerRadius())
        layers = [board.GetLayerName(layer) for layer in pad.GetLayerSet().Seq()]
        pin = pad.GetNumber()
        assignment = pin or ({0.95: "1", -0.95: "2", 0.0: "3"}[round(local_y, 6)])
        geom = (x, y, size_x, size_y, radius)
        if pin:
            if layers != ["B.Cu"]:
                raise ValueError(layers)
            copper[pin] = geom
        else:
            if set(layers) != {"B.Mask", "B.Paste"}:
                raise ValueError(layers)
            expansion = pad.GetSolderMaskExpansion(pcb.B_Mask)
            paste = baseline.xy(pad.GetSolderPasteMargin(pcb.B_Paste))
            if expansion != 0 or tuple(paste) != (0.0, 0.0):
                raise ValueError("Unexpected mask or paste margin")
            mask[assignment] = geom
        details.append(("baseline_native", "copper" if pin else "mask_and_paste",
                        assignment, pad.GetNetname(), "|".join(layers),
                        x, y, round(local_x, 6), round(local_y, 6), size_x, size_y, radius,
                        baseline.string_id(pad)))

    # Jingdao p. 3, mm labels. Bottom-side placement mirrors the local Y axis.
    offsets = {"1": (-1, 0.95), "2": (-1, -0.95), "3": (1, 0)}
    recommended = {pin: (origin[0] + dx, origin[1] + dy, 0.9, 0.8, 0)
                   for pin, (dx, dy) in offsets.items()}
    nets = {pad.GetNumber(): pad.GetNetname() for pad in fp.Pads() if pad.GetNumber()}
    for pin, (dx, dy) in offsets.items():
        x, y, width, height, radius = recommended[pin]
        details.append(("jingdao_nominal_projection", "copper", pin, nets[pin],
                        "B.Cu", x, y, dx, dy, width, height, radius, ""))
    write_csv(out / "q1_pad_details.csv",
              ("state", "purpose", "pin", "net", "layers", "x_mm", "y_mm",
               "placed_dx_mm", "placed_dy_mm", "size_x_mm", "size_y_mm", "radius_mm", "uuid"),
              details)

    def gaps(source, i, j):
        ax, ay, aw, ah, ar = source[i]
        bx, by, bw, bh, br = source[j]
        dx, dy = abs(ax - bx), abs(ay - by)
        # Distance between the inset rectangular cores minus the radii.
        r = ar + br
        edge = hypot(max(0, dx - (aw+bw)/2 + r), max(0, dy - (ah+bh)/2 + r)) - r
        return hypot(dx, dy), edge

    baseline_distance = []
    rows = []
    for i, j in combinations(("1", "2", "3"), 2):
        before_center, before = gaps(copper, i, j)
        _, original_opening = gaps(mask, i, j)
        after_center, after = gaps(recommended, i, j)
        if before < 1.0:
            baseline_distance.append(f"{before:.4f}")
        pair = {"12": "B-E", "13": "C-B", "23": "C-E"}[i+j]
        rows.append([pair, f"{i}-{j}", nets[i], nets[j],
                     *(f"{v:.6f}" for v in (before_center, before, original_opening,
                                           before, after_center, after, after-before))])
    write_csv(out.parent / "Q1_PAD_GEOMETRY_BEFORE_AFTER.csv",
              ("pair", "pins", "net_a", "net_b", "baseline_copper_center_mm",
               "baseline_copper_edge_mm", "baseline_mask_opening_edge_mm",
               "delivered_copper_edge_mm", "jingdao_projection_center_mm",
               "jingdao_projection_edge_mm", "jingdao_projection_minus_baseline_mm"),
              rows)
    assert sorted(baseline_distance) == sorted(
        re.search(r"([0-9]+\.[0-9]+) mm\)$", item["description"]).group(1) for item in q1_drc)

    connections = []
    for pad in (p for p in fp.Pads() if p.GetNumber()):
        pin = pad.GetNumber()
        x, y, width, height, _ = recommended[pin]
        projected = pcb.SHAPE_RECT(pcb.FromMM(x-width/2), pcb.FromMM(y-height/2),
                                   pcb.FromMM(width), pcb.FromMM(height))
        for track in board.GetConnectivity().GetConnectedTracks(pad):
            if track.GetClass() != "PCB_TRACK" or track.GetLayer() != pcb.B_Cu:
                raise ValueError(track.GetClass())
            segment = pcb.SEG(track.GetStart(), track.GetEnd())
            connections.append(dict(pin=pin, net=track.GetNetname(), layer="B.Cu",
                                    uuid=baseline.string_id(track), start_mm=baseline.xy(track.GetStart()),
                                    end_mm=baseline.xy(track.GetEnd()), width_mm=pcb.ToMM(track.GetWidth()),
                                    intersects_jingdao_copper=projected.Collide(
                                        segment, track.GetWidth() // 2)))
    assert {entry["pin"] for entry in connections} == set(nets)
    assert not any(entry["intersects_jingdao_copper"] for entry in connections)
    write_json(out / "q1_track_contacts.json", connections)


def voltage_matrix(out):
    cases = {
        "off": ("正常截止及170V稳态", "理想电源与无寄生模型"),
        "on": ("正常导通", "130V固定管压降，C-B按同一时刻的VCE减VBE"),
        "off_195": ("195V持续异常供能并截止", "R14截止网表仅母线及C47初值升至195V"),
        "half_170_sustain": ("170V持续半导通", "19.8k欧等效故障，持续供能"),
        "half_195_sustain": ("195V持续半导通", "19.8k欧等效故障，持续供能"),
        "half_195_isolated": ("195V理想切断后储能", "C47=3.63uF，切断从初始时刻生效"),
        "half_195_tube130": ("195V半导通有管压降", "130V管压降敏感性"),
        "ce_short": ("C-E短路", "0.1欧短路，误点亮及阳极耗散"),
        "cb_10meg": ("C-B高阻泄漏", "10M欧，接近完整母线应力"),
        "cb_1meg": ("C-B高阻泄漏", "1M欧"),
        "cb_100k": ("C-B泄漏", "100k欧，局部功率上升"),
        "cb_10k": ("C-B泄漏", "10k欧"),
        "cb_short": ("C-B短路", "0.1欧，GPIO通路为代理"),
        "leak_ce_1meg": ("C-E泄漏", "1M欧"),
        "leak_ce_100k": ("C-E泄漏", "100k欧"),
        "leak_ce_10k": ("C-E泄漏", "10k欧"),
        "open_cathode": ("开路阴极且驱动开启", "模型无实际浮置耦合或点火"),
        "erroneous_on": ("195V误导通", "0V管压降的包络工况"),
        "three_half": ("195V三路半导通", "各支路与总电流须分别考虑"),
        "logic_off_cb_short": ("逻辑失供与C-B短路", "简单驱动及钳位代理"),
        "highz_cb_short": ("驱动高阻与C-B短路", "简单钳位代理，可回灌"),
        "intermediate_output": ("驱动中间电平", "0.82V代理输出"),
    }
    sim.OUT = out
    case_195 = (195, *sim.CONDITIONS["off"][1:])
    sim.run_case("off_195", sim.cathode(case_195))
    (out / "off_195" / "run.log").replace(out / "off_195" / "ngspice.txt")
    rows = []
    for case, (label, limitation) in cases.items():
        path = (out if case == "off_195" else R14 / "evidence" / "simulation") / case / "waveform.raw"
        names, samples = sim.read_raw(path)
        idx = [names.index(f"v({name})") for name in ("hv", "vce", "vbe")]
        hv, ce, be = zip(*(tuple(row[i] for i in idx) for row in samples))
        cb = [c - b for c, b in zip(ce, be)]
        reported = [max(abs(v) for v in series) for series in (hv, cb, ce, be)]
        rows.append([case, label, "NGSPICE_PROXY", *(f"{v:.10g}" for v in reported),
                     "UNKNOWN", str(Path(os.path.relpath(path, out.parent))).replace("\\", "/"), limitation])
    rows.extend([
        ["startup", "启动及首次点火", "UNBOUNDED", "", "", "", "", "UNKNOWN",
         "../r14/HV_STOP_VALIDATION.md", "含高压上升超调、欠压高阻、点火跃迁及寄生；无板级Q1波形"],
        ["shutdown", "关断与STOP", "UNBOUNDED", "", "", "", "", "UNKNOWN",
         "../r14/HV_STOP_VALIDATION.md", "正常关断、掉电次序及切断卡通；代理不提供Q1逐针峰值"],
        ["feedback_fault", "反馈短路及OVP动作", "HISTORICAL_HV_BUS_ONLY", "188.876",
         "", "", "", "UNKNOWN", "../r11/GATE0_SAFETY_ASSESSMENT.md", "R11空载代理母线峰值；R14 Q1瞬态未定"],
        ["floating", "阴极积荷、寄生耦合及实际重复峰值", "UNBOUNDED", "", "", "", "",
         "UNKNOWN", "../r14/INSULATION_COORDINATION.md", "缺寄生、真实管模型和最坏实测，需覆盖正负峰及频谱"],
        ["base_fault", "基极回路开路、关断负向及故障回灌", "UNBOUNDED", "", "", "", "",
         "UNKNOWN", "../r14/FAULT_COVERAGE_MATRIX.csv", "V_EBO 5V为器件额定；真实反向V_BE及失供状态未限定"],
    ])
    write_csv(out.parent / "INSULATION_VOLTAGE_MATRIX.csv",
              ("case", "condition", "evidence_kind", "model_peak_abs_bus_V", "model_peak_abs_CB_V",
               "model_peak_abs_CE_V", "model_peak_abs_BE_V", "qualified_actual_peak", "evidence", "limits"),
              rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "evidence")
    out = parser.parse_args().out.resolve()
    subprocess.run(["git", "diff", "--quiet", BASELINE, "--", "eda"], cwd=R14, check=True)
    out.mkdir(exist_ok=True, parents=True)
    native_checks(out)
    drc = baseline.load(out / "DRC.json")
    erc = baseline.load(out / "ERC.json")
    stem = R14 / "eda" / baseline.STEM
    board = pcb.LoadBoard(str(stem.with_suffix(".kicad_pcb")))
    q1_fp = next(fp for fp in board.GetFootprints() if fp.GetReference() == "Q1")
    q1_ids = {baseline.string_id(pad) for pad in q1_fp.Pads() if pad.GetNumber()}
    q1 = [item for item in drc["violations"]
          if q1_ids.intersection(obj["uuid"] for obj in item["items"])]
    assert len(q1) == 2
    assert all("2.0000 mm" in item["description"] for item in q1)
    audit = baseline.audit_board(stem.with_suffix(".kicad_pcb"))
    archived = baseline.load(R14 / "evidence" / "r14_1" / "DRC.json")
    def item_ids(report, key):
        return Counter((entry["type"], tuple(sorted(item["uuid"] for item in entry["items"])))
                       for entry in report[key])

    for key in ("violations", "schematic_parity"):
        assert item_ids(drc, key) == item_ids(archived, key)
    # Ratsnest endpoints may change between invocations. Compare opens by actual net.
    net_by_uuid = {baseline.string_id(item): item.GetNetname() for item in board.GetTracks()}
    net_by_uuid.update({baseline.string_id(pad): pad.GetNetname()
                        for fp in board.GetFootprints() for pad in fp.Pads()})
    net_by_uuid.update({baseline.string_id(zone): zone.GetNetname() for zone in board.Zones()})

    def open_nets(report):
        return Counter(tuple(sorted({net_by_uuid[item["uuid"]] for item in entry["items"]}))
                       for entry in report["unconnected_items"])

    assert open_nets(drc) == open_nets(archived)
    replay_open_ids = item_ids(drc, "unconnected_items")
    archive_open_ids = item_ids(archived, "unconnected_items")
    pins = baseline.pins(out / "netlist.xml")
    assert pins == baseline.pins(R14 / "evidence" / "r14_1" / "netlist.xml")
    audit["qa"] = dict(
        baseline_sha=BASELINE, version="10.0.8",
        erc=Counter(v["severity"] for sheet in erc["sheets"] for v in sheet["violations"]),
        drc=Counter(v["type"] for v in drc["violations"]), opens=len(drc["unconnected_items"]),
        parity=len(drc["schematic_parity"]), q1_violations=q1, clearance_and_parity_uuid_sets_match_archive=True,
        opens_per_net_match_archive=True,
        native_open_endpoint_pairs_changed=sum((replay_open_ids - archive_open_ids).values()),
        pin_net_assignments_identical=True, source_sha256={
            file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in
            sorted(stem.parent.glob("NXT-M3-R14.kicad_*")) if file.suffix != ".kicad_prl"
        })
    terminal_counts = [sum(row["copper_connected"] for row in audit[key]) for key in ("cathode", "stop")]
    assert (audit["qa"]["erc"], audit["qa"]["drc"], audit["qa"]["opens"], audit["qa"]["parity"],
            terminal_counts) == ({}, {"clearance": 253}, 337, 0, [6, 36])
    write_json(out / "terminal_audit.json", audit)
    geometry(out, board, q1)
    voltage_matrix(out)
    print("KiCad 10.0.8: ERC 0/0, DRC 253 clearance and 337 opens, parity 0, Q1 6/6, J6 36/49")


if __name__ == "__main__":
    main()
