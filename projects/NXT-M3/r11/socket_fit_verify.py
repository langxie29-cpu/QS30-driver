"""Verify the GZC13-F hand-wire release inputs with native PCB and drill output."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

from route import EDA,box,pos
from socket_fit import PIN,coordinates,crosses_disk,distance,meta,rows

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else HERE/"evidence/socket_fit/final"


def pins(filename):
    return {(n.get("ref"),n.get("pin")):net.get("name")
            for net in ET.parse(filename).findall("./nets/net") for n in net.findall("node")}


def drill_positions(path,diameter):
    active=False
    loc=set()
    tools={}
    for line in path.read_text(encoding="ascii").splitlines():
        definition=re.fullmatch(r"(T\d+)C([\d.]+)",line)
        if definition:
            tools[definition[1]]=float(definition[2])
        elif re.fullmatch(r"T\d+",line):
            active=abs(tools.get(line,0)-diameter)<1e-6
        elif active:
            hit=re.fullmatch(r"X([+-]?[\d.]+)Y([+-]?[\d.]+)",line)
            if hit:
                loc.add((float(hit[1]),-float(hit[2])))
    return loc


def main():
    board=pcb.LoadBoard(str(EDA))
    fps={f.GetReference():f for f in board.GetFootprints()}
    original=pins(HERE/"evidence/typec/final/native_netlist.xml")
    current=pins(OUT/"native_netlist.xml")
    skipped={(f"V{i}",str(pin)) for i in range(1,4) for pin in (2,8)}
    assert {node:net for node,net in original.items() if node not in skipped}==current
    hw=meta()
    holes={ref:(50+x,50+y) for ref,(x,y) in hw["pcb_holes_mm"].items()}
    observed_drill=drill_positions(Path(sys.argv[1]),hw["pcb_npth_drill_mm"])
    assert observed_drill==set(holes.values()),(observed_drill,holes)
    for ref,xy in holes.items():
        [pad]=list(fps[ref].Pads())
        assert pos(pad)==xy and pad.GetAttribute()==pcb.PAD_ATTRIB_NPTH
        assert pcb.ToMM(pad.GetDrillSize().x)==pcb.ToMM(pad.GetDrillSize().y)==3.5
    handoffs=rows()
    pads_by_id={}
    for row in handoffs:
        ref,function=row["tube"],row["function"]
        target=next(p for p in fps[ref].Pads() if p.GetNumber()==PIN[function])
        assert target.GetNetname()==row["pcb_net"]==current[(ref,PIN[function])]
        assert pos(target)==coordinates(row) and target.GetDrillSize().x==0
        assert target.IsOnLayer(pcb.F_Cu) and not target.IsOnLayer(pcb.B_Cu)
        assert (pcb.ToMM(target.GetSize().x),pcb.ToMM(target.GetSize().y))==(1.8,2.6)
        pads_by_id[str(target.m_Uuid.AsString())]=[ref,function,row["pcb_net"]]
    tracks=list(board.GetTracks())
    copper=[(fp.GetReference(),p.GetNetname(),box(p)) for fp in fps.values() for p in fp.Pads() if p.GetNetname()]
    conflicts={}
    for ref,xy in holes.items():
        hit=sorted({t.GetNetname() for t in tracks if crosses_disk(t,xy,4)})
        found=sorted({(f,n) for f,n,b in copper if distance(xy,b)<4})
        if hit or found:
            conflicts[ref]={"tracks":hit,"pads":found}
    check=json.loads((OUT/"DRC.json").read_text(encoding="utf-8-sig"))
    unconnected=set()
    for issue in check["unconnected_items"]:
        for item in issue["items"]:
            if item["uuid"] in pads_by_id:
                unconnected.add(pads_by_id[item["uuid"]][2])
    result={"verified_socket_drills":{ref:list(xy) for ref,xy in holes.items()},
            "npth_diameter_mm":3.5,"mount_fastener_envelope_copper_hits":conflicts,
            "all_handoffs_with_net":len(handoffs),"handoff_nets_drc_open":sorted(unconnected),
            "handoff_nets_without_drc_open":sorted({r["pcb_net"] for r in handoffs}-unconnected),
            "connected_schematic_pins_changed":0,"removed_unused_logical_pins":len(skipped),
            "native_rule_types":dict(Counter(v["type"] for v in check["violations"])),
            "native_open_items":len(check["unconnected_items"]),"native_parity_count":len(check["schematic_parity"]),
            "drill_evidence_sha256":hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()}
    (OUT/"socket_fit_audit.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
