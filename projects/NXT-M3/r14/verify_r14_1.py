"""Capture native reports and verify terminal-to-terminal PCB connectivity."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

from close_r14_1 import BASE, CLI, EVIDENCE, HERE, STEM, all_errors
from route_r14_1 import gap, xy

CATHODE = (
    ("drive", "U20.15", "R100.1"),
    ("base_feed", "R100.2", "Q1.1"),
    ("base_pulldown", "R200.1", "Q1.1"),
    ("return_local", "R200.2", "Q1.2"),
    ("return_driver", "U20.8", "Q1.2"),
    ("cathode_socket", "Q1.3", "V1.3"),
)
STOP = (
    ("contact", "J6.1", "R509.1"),
    ("ESD", "J6.1", "D15.1"),
    ("gate", "R509.2", "Q35.1"),
    ("gate_bias", "R510.2", "Q35.1"),
    ("gate_cap", "C64.1", "Q35.1"),
    ("loop_return", "J6.2", "Q35.2"),
    ("latch_return", "J6.2", "U8.4"),
    ("gate_supply", "R510.1", "U8.8"),
    ("fault", "Q35.3", "U9.2"),
    ("fault_watchdog", "U25.8", "U9.2"),
    ("fault_ovp", "U13.1", "U9.2"),
    ("fault_ocp", "U13.7", "U9.2"),
    ("fault_log", "Q35.3", "U3.9"),
    ("latch_reset", "U9.4", "U8.6"),
    ("latch_clock", "J4.2", "U8.1"),
    ("latch_preset", "U8.7", "U8.8"),
    ("latch_vdd", "U8.8", "U9.5"),
    ("reset_supervisor", "U4.1", "U9.1"),
    ("residual_pullup", "R28.2", "U8.2"),
    ("residual_observer", "U14.1", "U8.2"),
    ("clear_to_cutoff_en", "U8.5", "U11.1"),
    ("clear_to_pwm_gate", "U8.5", "U15.1"),
    ("bias_comp", "U14.7", "U15.2"),
    ("pwm_gate_supply", "U15.5", "U8.8"),
    ("pwm_gate_return", "U15.3", "J6.2"),
    ("pwm_to_blanking", "U15.4", "U19.1"),
    ("pwm_to_converter", "U15.4", "R77.1"),
    ("ready_to_blanking", "U17.11", "U19.2"),
    ("blanking_to_request_gate", "U19.4", "U10.1"),
    ("display_request", "U3.7", "U10.2"),
    ("blanking_gate", "U10.4", "Q31.1"),
    ("blanking_pulldown", "Q31.1", "R25.1"),
    ("blanking_source_return", "Q31.2", "J6.2"),
    ("blanking_pulldown_return", "R25.2", "J6.2"),
    ("blanking_oe_pullup", "Q31.3", "R24.2"),
    *((f"blanking_u{n}", "Q31.3", f"U{n}.13") for n in range(20,24)),
    ("efuse_input", "R40.2", "U11.5"),
    ("efuse_output_cap", "U11.6", "C28.1"),
    ("efuse_output_converter", "U11.6", "U17.1"),
    ("efuse_ground", "U11.8", "C27.2"),
    ("efuse_ovlo_high", "U11.2", "R41.2"),
    ("efuse_ovlo_low", "U11.2", "R42.1"),
    ("efuse_ilim", "U11.9", "R43.1"),
    ("efuse_timer", "U11.10", "C26.1"),
    ("efuse_dvdt", "U11.7", "C25.1"),
    ("efuse_pgth", "U11.4", "R44.1"),
)
FIRST = ("contact", "gate", "loop_return", "latch_return", "fault", "latch_reset",
         "latch_clock", "latch_preset", "latch_vdd", "clear_to_cutoff_en")


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def native(eda):
    out = EVIDENCE
    calls = (["version"],
             ["sch","export","netlist","--format","kicadxml","-o",str(out/"netlist.xml"),str(eda.with_suffix(".kicad_sch"))],
             *(["sch","erc","--severity-all","--exit-code-violations","--format",fmt,
                "-o",str(out/f"ERC.{suffix}"),str(eda.with_suffix(".kicad_sch"))]
               for fmt,suffix in (("json","json"),("report","rpt"))),
             *(["pcb","drc","--schematic-parity","--severity-all","--exit-code-violations","--format",fmt,
                "-o",str(out/f"DRC.{suffix}"),str(eda.with_suffix(".kicad_pcb"))]
               for fmt,suffix in (("json","json"),("report","rpt"))))
    records = []
    for call in calls:
        run = subprocess.run([str(CLI),*call],capture_output=True,cwd=HERE)
        records.append({"args":call,"exit":run.returncode,"stdout":run.stdout.decode("utf-8","replace"),
                        "stderr":run.stderr.decode("utf-8","replace")})
        assert run.returncode in (0,5),records[-1]
    return records


def pins(path):
    tree = ET.parse(path)
    return {(n.get("ref"),n.get("pin")):net.get("name") for net in tree.findall("./nets/net")
            for n in net.findall("node")}


def string_id(item):
    return str(item.m_Uuid.AsString())


def audit_board(path):
    board = pcb.LoadBoard(str(path))
    assert board.BuildConnectivity()
    connection = board.GetConnectivity()
    refs = {fp.GetReference():fp for fp in board.GetFootprints()}

    def ends(label):
        ref,pin = label.split(".")
        result = [p for p in refs[ref].Pads() if p.GetNumber()==pin]
        assert result, label
        return result

    def check_pair(label,left,right):
        a,b = ends(left),ends(right)
        assert all(p.GetNetCode()==a[0].GetNetCode() for p in a+b), (label,left,right)
        linked = {string_id(item) for p in a for item in connection.GetConnectedItems(p)}
        matched = linked & {string_id(p) for p in b}
        return {"item":label,"a":left,"b":right,"net":a[0].GetNetname(),
                "copper_connected":bool(matched),"connected_item_count":len(linked)}

    track = Counter()
    for item in board.GetTracks():
        if not isinstance(item,pcb.PCB_VIA):
            track[(item.GetLayerName(),gap(item.GetNetname())>1)] += 1
    assert not any(hv and layer.startswith("In") for layer,hv in track)
    r40 = refs["R40"]
    result = {
        "copper_layers":board.GetCopperLayerCount(),
        "tracks":[{"layer":layer,"hv_screened":hv,"count":count}
                  for (layer,hv),count in sorted(track.items())],
        "r40_dnp":r40.IsDNP(),"u11_dnp":refs["U11"].IsDNP(),
        "cathode":[check_pair(*pair) for pair in CATHODE],
        "stop":[check_pair(*pair) for pair in STOP],
        "selected_footprints":{r:{"footprint":refs[r].GetFPIDAsString(),
                                   "at_mm":xy(refs[r].GetPosition()),
                                   "pads":[{"pin":p.GetNumber(),"position_mm":xy(p.GetPosition()),
                                            "size_mm":xy(p.GetSize()),"net":p.GetNetname(),
                                            "layers":[board.GetLayerName(l) for l in p.GetLayerSet().Seq()]}
                                           for p in refs[r].Pads()]}
                               for r in ("Q1","R100","R200","V1","U8","U11","J6","R40")},
        "mounts":{r:{"at_mm":xy(fp.GetPosition()),"holes_mm":[xy(p.GetDrillSize()) for p in fp.Pads()]}
                  for r,fp in refs.items() if r.startswith("MH")},
    }
    assert result["r40_dnp"] and result["u11_dnp"]
    return result


def main():
    EVIDENCE.mkdir(exist_ok=True,parents=True)
    eda = HERE/"eda"/STEM
    commands = native(eda)
    original_path = f"projects/NXT-M3/r14/eda/{STEM}"
    pre_board = Path(sys.argv[1])
    pre_board.parent.mkdir(exist_ok=True,parents=True)
    pre_board.write_bytes(subprocess.check_output(["git","show",f"{BASE}:{original_path}.kicad_pcb"],cwd=HERE))
    base = audit_board(pre_board)
    result = audit_board(eda.with_suffix(".kicad_pcb"))
    assert base["mounts"]==result["mounts"]
    assert all(x["copper_connected"] for x in result["cathode"]),result["cathode"]
    assert all(x["copper_connected"] for x in result["stop"] if x["item"] in FIRST),result["stop"]
    assert pins(HERE/"evidence/pcb/netlist.xml")==pins(EVIDENCE/"netlist.xml")
    for ext in ("kicad_dru","kicad_pro"):
        before = subprocess.check_output(["git","show",f"{BASE}:{original_path}.{ext}"],cwd=HERE)
        actual = eda.with_suffix("."+ext).read_bytes()
        if ext=="kicad_pro":
            old_project,new_project = json.loads(before),json.loads(actual)
            assert new_project["schematic"]["top_level_sheets"][0]["filename"]==f"{STEM}.kicad_sch"
            old_project["schematic"]["top_level_sheets"] = new_project["schematic"]["top_level_sheets"]
            assert old_project==new_project
        else:
            assert before.replace(b"\r\n",b"\n")==actual.replace(b"\r\n",b"\n")
    old = load(HERE/"evidence/drc/DRC.json")
    new = load(EVIDENCE/"DRC.json")
    erc = load(EVIDENCE/"ERC.json")
    old_pairs,new_pairs = all_errors(old),all_errors(new)
    q1 = [e for e in new["violations"] if any("Q1 " in i["description"] for i in e["items"])]
    assert len(q1)==2,q1
    assert all("0.6552 mm" in e["description"] for e in q1)
    assert not new["schematic_parity"]
    result["qa"] = {"baseline_drc":len(old["violations"]),"drc":len(new["violations"]),
                    "drc_types":Counter(e["type"] for e in new["violations"]),
                    "new_violations":[new_pairs[k] for k in sorted(new_pairs.keys()-old_pairs.keys())],
                    "removed_violations":[old_pairs[k] for k in sorted(old_pairs.keys()-new_pairs.keys())],
                    "q1_violations":q1,"erc":Counter(v["severity"] for s in erc["sheets"] for v in s["violations"]),
                    "baseline_opens":len(old["unconnected_items"]),"opens":len(new["unconnected_items"]),
                    "parity":len(new["schematic_parity"]),"pin_net_assignments_identical":True,
                    "rules_sha256":hashlib.sha256(eda.with_suffix(".kicad_dru").read_bytes()).hexdigest()}
    result["baseline"] = {"commit":BASE,"copper_layers":base["copper_layers"],
                          "cathode":base["cathode"],"stop":base["stop"]}
    (EVIDENCE/"terminal_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (EVIDENCE/"native_commands.json").write_text(json.dumps(commands,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Q1:",sum(x["copper_connected"] for x in result["cathode"]),"of",len(result["cathode"]))
    print("STOP gaps:",[x["item"] for x in result["stop"] if not x["copper_connected"]])
    print("DRC:",result["qa"]["drc"],"opens:",result["qa"]["opens"],"parity:",result["qa"]["parity"])


if __name__=="__main__":
    main()
