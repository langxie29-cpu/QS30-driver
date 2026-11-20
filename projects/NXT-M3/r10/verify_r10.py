"""Rebuild and check native R10 engineering artifacts without clearing the release hold."""
from collections import Counter
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
KICAD=Path(os.environ.get("KICAD_BIN",r"C:\Program Files\KiCad\10.0\bin"))
CLI=KICAD/"kicad-cli.exe"
KPY=KICAD/"python.exe"
EVID=HERE/"evidence"
SCH="eda/NXT-M3-R10.kicad_sch"
PCB="eda/NXT-M3-R10.kicad_pcb"

def audit_cathodes():
    root=ET.parse(EVID/"native_netlist.xml")
    nodes={}
    for net in root.findall("./nets/net"):
        for n in net.findall("node"):
            nodes[(n.get("ref"),n.get("pin"))]=net.get("name")
    def eq(ref,pin,net):
        actual=nodes.get((ref,str(pin)))
        if actual!=net:
            raise AssertionError(f"{ref}.{pin}: {actual!r} expected {net!r}")
    with (HERE/"CATHODE_MAP.csv").open(encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=32 or len(set(row["logical_socket_pin"] for row in rows[:-2]))!=30:
        raise AssertionError("Expected 30 unique logical socket endpoints and two spare bits")
    for i,row in enumerate(rows[:30]):
        bank,digit=divmod(i,10)
        out_pin=(15,1,2,3,4,5,6,7)[i%8]
        dpin=(3,13,12,11,10,9,7,6,5,4)[digit]
        drv,base,cat=f"DRV_{i:02}",f"BASE_{i:02}",f"K{bank+1}_{digit}"
        eq(f"U{20+i//8}",out_pin,drv)
        eq(f"R{100+i}",1,drv)
        eq(f"R{100+i}",2,base)
        eq(f"R{200+i}",1,base)
        eq(f"R{200+i}",2,"GND")
        eq(f"Q{i+1}",1,base)
        eq(f"Q{i+1}",2,"GND")
        eq(f"Q{i+1}",3,cat)
        eq(f"V{bank+1}",dpin,cat)
    for i in range(4):
        eq(f"U{20+i}",13,"HC_OE_N")
        if i:
            eq(f"U{19+i}",9,f"SER{i}")
            eq(f"U{20+i}",14,f"SER{i}")
    for pin in (6,7):
        if not nodes[("U23",str(pin))].startswith("unconnected-"):
            raise AssertionError(f"Expected U23.{pin} NC")
    return {"cathode_paths":30,"spare_outputs_nc":2,"shift_registers":4}

def run():
    EVID.mkdir(exist_ok=True)
    runs=[]
    def invoke(name, cmd, expected=0, cwd=HERE):
        args=[str(a) for a in cmd]
        proc=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        output=proc.stdout.decode("utf-8",errors="replace").strip()
        runs.append({"name":name,"command":subprocess.list2cmdline(args),"cwd":str(cwd),
                     "exit":proc.returncode,"expected_exit":expected,"output":output})
        (EVID/"commands.json").write_text(json.dumps(runs,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        if proc.returncode!=expected:
            raise RuntimeError(f"{name}: expected exit {expected}, got {proc.returncode}. See evidence/commands.json")
        print(f"{name}: {proc.returncode}")
    invoke("KiCad version",[CLI,"version"])
    invoke("Generate native hierarchy",[sys.executable,"build_schematic.py"])
    invoke("Native ERC",[CLI,"sch","erc","--exit-code-violations","-o","evidence/ERC.rpt",SCH])
    invoke("Native netlist",[CLI,"sch","export","netlist","--format","kicadxml","-o","evidence/native_netlist.xml",SCH])
    invoke("Native BOM",[CLI,"sch","export","bom","--fields","Reference,Value,Footprint,MPN,Status,${DNP}",
                         "--group-by","Value,Footprint,MPN,Status","-o","evidence/native_bom.csv",SCH])
    invoke("Native schematic PDF rendering",[CLI,"sch","export","pdf","-o","evidence/NXT-M3-R10.pdf",SCH])
    invoke("Native footprint/load and pad sync",[KPY,"build_pcb.py"])
    invoke("Native DRC/ECAD parity",[CLI,"pcb","drc","--schematic-parity","--format","json","--exit-code-violations",
                                   "-o","evidence/DRC.json",PCB],expected=5)
    invoke("Mechanical projection",[sys.executable,"mechanical_layout.py"])
    invoke("ngspice bounded transient",[KPY,"run_residual_spice.py"])
    invoke("R9 BOM delta",[sys.executable,"revise_cost.py"])
    invoke("Inherited R9 display tests",[sys.executable,"-m","unittest","-q","test_low_voltage_display"],cwd=HERE.parent/"r9")
    d=json.loads((EVID/"DRC.json").read_text(encoding="utf-8-sig"))
    types=Counter(v["type"] for v in d["violations"])
    parity=Counter(v["type"] for v in d["schematic_parity"])
    placements=list(csv.DictReader((EVID/"footprint_sync.csv").open(encoding="utf-8")))
    payload={"GATE_0":"REWORK","ENGINEERING_RELEASE":"HOLD",
             "Native_KiCad":d["kicad_version"],"ERC_errors":0,"ERC_warnings":0,
             **audit_cathodes(),"installed_candidate_footprints":sum(bool(r["footprint"]) for r in placements),
             "logical_sockets_missing_footprint":[r["ref"] for r in placements if not r["footprint"]],
             "DRC_violations":len(d["violations"]),"DRC_violations_by_type":dict(types),
             "DRC_violations_by_severity":dict(Counter(v["severity"] for v in d["violations"])),
             "DRC_unconnected_items":len(d["unconnected_items"]),
             "DRC_schematic_parity":dict(parity),"DRC_status":"FAIL_PRELAYOUT"}
    (EVID/"summary.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    if parity!=Counter({"missing_footprint":3}):
        raise AssertionError(f"Unexpected schematic parity result: {parity}")
    print(json.dumps(payload,indent=2))

if __name__=="__main__":
    run()
