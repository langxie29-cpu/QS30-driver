"""Close specific R11 open nets, retaining only native-reviewed route changes."""
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

import pcbnew as pcb

from precision_route import Grid,Terminal
from route import EDA,CLI,width
from socket_fuse_edge import OLD_FUSED
from socket_route_repair import BLOCK
from typec_connector_breakout import append,segments,via,xy

HERE=Path(__file__).resolve().parent
OUT=HERE/"evidence/blocker_closure"
SYMBOLS=re.compile(r"\[([^\[\]]+)\]")
CAPTURE=[("5V_RAW","U26","24","J1","A9"),
         ("USBC_CC1","J1","A5","D5","1"),
         ("USBC_1V2","U26","21","C53","1"),
         ("USBC_2V7","U26","23","C54","1"),
         ("USBC_VALID_N","Q33","1","R230","2"),
         ("USBC_3A_N","U26","20","R233","1"),
         ("USBC_3A_N","R232","2","R233","1"),
         ("5V_RAW","F1","1","R230","1"),
         ("5V_RAW","R232","1","U26","24"),
         ("LV_SW","U2","7","L1","1"),
         ("ANODE_1","V1","1","R303","2"),
         ("ANODE_2","V2","1","R305","2"),
         ("SER1","U20","9","U21","14"),
         ("SER2","U21","9","U22","14"),
         ("SER3","U22","9","U23","14"),
         ("SR_CLK_BUS","U21","11","U22","11"),
         ("SR_CLK_BUS","U22","11","U23","11"),
         ("HV_CS","C42","1","R72","2"),
         ("HV_CS","U17","5","C42","1")]


def native(stage):
    OUT.mkdir(parents=True,exist_ok=True)
    filename=OUT/f"{stage}.json"
    command=[str(CLI),"pcb","drc","--refill-zones","--save-board","--schematic-parity",
             "--all-track-errors","--format","json","--exit-code-violations","-o",str(filename),str(EDA)]
    call=subprocess.run(command,capture_output=True)
    if call.returncode not in (0,5):
        raise RuntimeError((command,call.stdout,call.stderr))
    data=json.loads(filename.read_text(encoding="utf-8-sig"))
    print(stage,len(data["violations"]),len(data["unconnected_items"]),flush=True)
    return data,{"command":command,"exit":call.returncode,"raw":filename.name}


def open_nets(check):
    names=Counter()
    for item in check["unconnected_items"]:
        net=SYMBOLS.search(item["items"][0]["description"])
        if net:
            names[net[1]]+=1
    return names


def route_items(track,net,w):
    result=[]
    for a,b in zip(track,track[1:]):
        if a[2]!=b[2]:
            result.append(via(net,a[:2]))
        elif a[:2]!=b[:2]:
            result+=segments(net,"F" if a[2]==0 else "B",[a[:2],b[:2]],w)
    return result


def pad_at(board,ref,number):
    return next(p for fp in board.GetFootprints() if fp.GetReference()==ref for p in fp.Pads()
                if p.GetNumber()==number)


def geometry(board,net,source,target,around,w=None):
    w=w or width(net)
    x,y=source.point
    a,b=target.point
    extent=(max(50,min(x,a)-around),max(50,min(y,b)-around),
            min(180,max(x,a)+around),min(130,max(y,b)+around))
    shape=Grid(board,extent)
    track=shape.trace(net,w,source,target,via_ok=net not in {"LV_SW","SW_HV"})
    return route_items(track,net,w)


def prior_issue_ids(report):
    return {(row["type"],tuple(sorted(item["uuid"] for item in row["items"]))) for row in report["violations"]}


def verify_candidate(stage,original,baseline,copper):
    ids={re.search(r'\(uuid "([^"]+)"\)',piece)[1] for piece in copper}
    result,receipt=native(stage)
    old=prior_issue_ids(baseline)
    new=[issue for issue in result["violations"] if
         (issue["type"],tuple(sorted(item["uuid"] for item in issue["items"]))) not in old]
    acceptable=(not new and len(result["unconnected_items"])<len(baseline["unconnected_items"])
                and len(result["schematic_parity"])<=len(baseline["schematic_parity"]))
    if not acceptable:
        EDA.write_bytes(original)
    receipt.update(accepted=acceptable,added_violations=[i["type"] for i in new],
                   new_trace_items=len(ids),open_before=len(baseline["unconnected_items"]),
                   open_after_trial=len(result["unconnected_items"]))
    return (result if acceptable else baseline),receipt


def fuse(baseline):
    original=EDA.read_bytes()
    board=pcb.LoadBoard(str(EDA))
    part=next(fp for fp in board.GetFootprints() if fp.GetReference()=="F1")
    if part.GetOrientationDegrees()!=0:
        raise ValueError("F1 orientation has already changed")
    part.SetOrientationDegrees(180)
    pcb.SaveBoard(str(EDA),board)
    patterns=(*OLD_FUSED,{(82.9,52.5),(83.,52.75)},{(83.,52.75),(83.,54.5)})
    def drop(match):
        block=match[0]
        if '(net "5V_FUSED")' in block and "(segment" in block:
            if {xy(block,"start"),xy(block,"end")} in patterns:
                return ""
        return block
    candidate=BLOCK.sub(drop,EDA.read_text(encoding="utf-8"))
    fused=segments("5V_FUSED","F",[(71.75,51),(80.1,51),(80.1,52.5)],.5)
    edge=(120.27,50.675)
    entry=(120.27,54.32)
    raw=segments("5V_RAW","F",[(82.9,52.5),(82.9,edge[1]),edge],.5)
    raw+=segments("5V_RAW","B",[edge,entry],.5)+[via("5V_RAW",edge),via("5V_RAW",entry)]
    copper=[*fused,*raw]
    EDA.write_text(append(candidate,copper),encoding="utf-8")
    edited=pcb.LoadBoard(str(EDA))
    repair=geometry(edited,"5V_FUSED",Terminal.pad(pad_at(edited,"F1","2")),Terminal((83.,54.5),(0,)),7.)
    if not repair:
        EDA.write_bytes(original)
        print("Failed to find layout-compatible fused spur",flush=True)
        return baseline,{"case":"fuse","accepted":False,"reason":"no FUSED spur candidate"}
    EDA.write_text(append(candidate,copper+repair),encoding="utf-8")
    return verify_candidate("fuse_rotated_reconnected",original,baseline,copper+repair)


def task(baseline,item,stage):
    net,rf,pin,rt,pout=item
    original=EDA.read_bytes()
    board=pcb.LoadBoard(str(EDA))
    a=Terminal.pad(pad_at(board,rf,pin))
    b=Terminal.pad(pad_at(board,rt,pout))
    if not open_nets(baseline)[net]:
        return baseline,{"case":stage,"accepted":False,"reason":"net already closed"}
    copper=geometry(board,net,a,b,9.)
    if not copper:
        return baseline,{"case":stage,"accepted":False,"reason":"no candidate with existing pad geometry and rules"}
    EDA.write_text(append(EDA.read_text(encoding="utf-8"),copper),encoding="utf-8")
    return verify_candidate(stage,original,baseline,copper)


def main():
    initial,base_record=native("start")
    stages=[base_record]
    state=initial
    if len(sys.argv)==1 or sys.argv[1]=="fuse":
        state,record=fuse(state)
        stages.append(record)
    if len(sys.argv)==1 or sys.argv[1]!="fuse":
        for i,item in enumerate(CAPTURE,1):
            if len(sys.argv)>1 and item[0] not in sys.argv[1:]:
                continue
            stage=f"route_{i:02d}_{item[0]}"
            state,record=task(state,item,stage)
            stages.append(record)
            print(stage,record["accepted"],flush=True)
    result,receipt=native("end")
    stages.append(receipt)
    (OUT/"layout_trials.json").write_text(json.dumps(stages,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(open_nets(initial).total(),"->",open_nets(result).total(),"unconnected items",flush=True)


if __name__=="__main__":
    main()
