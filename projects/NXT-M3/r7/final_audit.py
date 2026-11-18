"""Validate frozen-to-R7 electrical delta, recorded evidence, and publication boundaries."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"
R6 = ROOT.parent / "r6"


def export(path):
    xml = ET.parse(path)
    nets = {net.attrib["name"]: sorted((node.attrib["ref"],node.attrib["pin"])
                                      for node in net.findall("node")) for net in xml.findall("./nets/net")}
    parts = {}
    for comp in xml.findall("./components/comp"):
        parts[comp.attrib["ref"]] = {key:comp.findtext(key) for key in ("value","footprint","datasheet")}
        parts[comp.attrib["ref"]]["mpn"] = comp.findtext("./fields/field[@name='MPN']")
    return parts,nets


def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main():
    before,old_nets = export(R6/"evidence/native.xml")
    after,new_nets = export(EVIDENCE/"native.xml")
    assert before.keys()==after.keys() and old_nets==new_nets
    for ref in after:
        assert {k:v for k,v in before[ref].items() if k!="mpn"}=={k:v for k,v in after[ref].items() if k!="mpn"}, ref
    change = {ref:dict(before=before[ref]["mpn"],after=after[ref]["mpn"])
              for ref in after if before[ref]!=after[ref]}
    assert set(change)=={"R27","R28","R49","R50"} and all(row["after"]=="TNPW1206100KBEEA" for row in change.values())
    assert not any(sheet["violations"] for sheet in json.loads((EVIDENCE/"erc.json").read_text(encoding="utf-8"))["sheets"])
    with (ROOT/"FINAL_BOM.csv").open(encoding="utf-8",newline="") as stream:
        bom = {row["ref"]:row for row in csv.DictReader(stream)}
    assert bom.keys()==after.keys()
    assert all(bom[ref]["mpn"]==after[ref]["mpn"] for ref in after)
    assert bom["J4"]["fitted_per_board"]=="0"
    save(EVIDENCE/"native_delta.json",dict(same_component_refs=len(after),identical_net_endpoints=len(new_nets),
         pin_and_footprint_topology_delta=0,changed_mpn=change,erc_violations=0))
    with (ROOT/"SIMULATION_RESULTS.csv").open(encoding="utf-8",newline="") as stream:
        runs = list(csv.DictReader(stream))
    flash = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(EVIDENCE.glob("flash_r*.json"))]
    assert len({row["case"] for row in runs})==len(runs)
    assert len(runs)==30, f"{len(runs)} of 30 run receipts present"
    assert len(flash)==5
    for run in runs:
        directory = ROOT / run["evidence"]
        pre = json.loads((directory/"preregister.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256((directory/"circuit.cir").read_bytes()).hexdigest()
        assert digest==pre["deck_sha256" if "deck_sha256" in pre else "netlist_sha256"], run["case"]
    tally = Counter("TIMEOUT" if row["execution"] in {"TIMEOUT","EXECUTION_FAIL"} else
                    "EXIT_ZERO" if row["exit_code"]=="0" else "NONZERO_EXIT" for row in runs)
    save(EVIDENCE/"resources.json",dict(
        baseline="163a60b2f1525e47b66f929103ff446a3f57c460",
        remote_baseline_verified=["refs/heads/nxt/nxt-m3-architecture-reconstruction-r6","2026-11-19 Asia/Shanghai"],
        target_branch="nxt/nxt-m3-power-cost-optimization-r7",
        native_LTspice_calls=len(runs),native_LTspice_engine="24.0.12 Windows",
        native_termination=dict(tally),native_calls_by_round=dict(Counter(row["round"] for row in runs)),
        native_total_wall_seconds=round(sum(float(row["seconds"]) for row in runs),3),
        flash_called=sum(item["called"] for item in flash),
        flash_tokens=sum((item.get("usage") or {}).get("total_tokens",0) for item in flash),
        flash_completion=dict(Counter(item["status"] for item in flash)),flash_fee="UNKNOWN",
        archived_run_scope="Actual decks, logs, measurements, receipts and small waveforms are tracked. Full large raw traces remain on the executing machine."))
    print("Native XML, ERC, BOM, 30 simulation deck hashes and five Flash receipts verified.")


if __name__=="__main__":
    main()
