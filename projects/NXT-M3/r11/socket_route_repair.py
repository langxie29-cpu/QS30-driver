"""Route the new hand-wire nets and repair local copper affected by the six holes."""
from collections import Counter
import itertools
import json
import math
import re
import subprocess

import pcbnew as pcb

import route

HERE=route.HERE
OUT=HERE/"evidence/socket_fit"
BASE=route.EDA
BLOCK=re.compile(r"(?ms)^\t\((?:segment|via)\n.*?^\t\)\n")


def native(stage):
    output=OUT/(stage+".json")
    args=[str(route.CLI),"pcb","drc","--refill-zones","--save-board","--all-track-errors","--schematic-parity",
          "--format","json","--exit-code-violations","-o",str(output),str(BASE)]
    completed=subprocess.run(args,capture_output=True)
    record={"command":args,"exit":completed.returncode,"stdout":completed.stdout.decode("utf-8","replace"),
            "stderr":completed.stderr.decode("utf-8","replace")}
    (OUT/(stage+".command.json")).write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if completed.returncode not in (0,5):
        raise RuntimeError(record)
    data=json.loads(output.read_text(encoding="utf-8-sig"))
    print(stage,len(data["violations"]),len(data["unconnected_items"]),len(data["schematic_parity"]),flush=True)
    return data


def identity(item):
    return str(item.m_Uuid.AsString())


def prune(ids):
    before=BASE.read_text(encoding="utf-8")
    def filter_block(match):
        return "" if re.search(r'\(uuid "([^"]+)"\)',match[0])[1] in ids else match[0]
    BASE.write_text(BLOCK.sub(filter_block,before),encoding="utf-8")


def colliding_tracks(drc):
    board=pcb.LoadBoard(str(BASE))
    pad_names={identity(pad):fp.GetReference() for fp in board.GetFootprints() for pad in fp.Pads()}
    tracks={identity(item):item.GetNetname() for item in board.GetTracks()}
    deleted={}
    for issue in drc["violations"]:
        keys={item["uuid"] for item in issue["items"]}
        if not any(pad_names.get(key) in {"V1","V2","V3","C47","SW1","TP4","MH5L","MH5R","MH6L",
                                         "MH6R","MH7L","MH7R"} for key in keys):
            continue
        for key in keys:
            if key in tracks:
                deleted[key]=tracks[key]
    return deleted


def connect(stage, nets, limit):
    board=pcb.LoadBoard(str(BASE))
    draft=route.Draft(board)
    for item in board.GetTracks():
        via=isinstance(item,pcb.PCB_VIA)
        layers=(0,1) if via else (route.LAYERS.index(item.GetLayer()),)
        draft.obstacles.append((item.GetNetname(),layers,route.box(item),"via" if via else "track"))
    jobs=[]
    for net in sorted(nets):
        entries=draft.pads[net]
        if len(entries)>35:
            continue
        for a,b in itertools.combinations(entries,2):
            distance=math.dist(route.pos(a[1]),route.pos(b[1]))
            jobs.append((distance,net,a,b))
    root={}
    def find(n):
        while n in root:
            n=root[n]
        return n
    for _,net,a,b in sorted(jobs,key=lambda row:row[0]):
        first,second=(find(identity(entry[1])) for entry in (a,b))
        if first==second:
            continue
        count=len(draft.saved)
        draft.route(net,a,b,limit)
        if len(draft.saved)>count:
            root[first]=second
    groups=[(net,a,b,{identity(t) for t in items}) for net,a,b,items in draft.saved]
    pcb.SaveBoard(str(BASE),board)
    trial=native(stage+"_trial")
    bad={item["uuid"] for rule in trial["violations"] for item in rule["items"]}
    discard=set().union(*(ids for net,a,b,ids in groups if ids&bad))
    prune(discard)
    result=native(stage)
    retained=[(net,a,b,len(ids)) for net,a,b,ids in groups if not ids&discard]
    return result,retained


def main():
    route.STEP,route.NX,route.NY=.125,1041,641
    initial=native("before_repair")
    removed=colliding_tracks(initial)
    prune(removed)
    (OUT/"placement_conflict_tracks.json").write_text(json.dumps(removed,indent=2)+"\n",encoding="utf-8")
    hv={f"K{tube}_{digit}" for tube in range(1,4) for digit in range(10)}
    hv|={"ANODE_1","ANODE_2","ANODE_3","HV_BUS"}
    _,h=connect("handoff_routing",hv,74000)
    local=set(removed.values())|{"BOOT_N","SR_LATCH","DRV_27","UART_RX","UART_TX","UART_HDR_RX"}
    local.discard("HV_BUS")
    _,l=connect("local_repair",local,48000)
    essential={"5V_RAW","USBC_CC1","USBC_CC2","USBC_1V2","USBC_2V7","USBC_3A_N","USBC_VALID_N",
               "LV_SW","SER1","SER2","SER3","HC_CLEAR_N","MCU_SDA","MCU_SCL"}
    final,c=connect("input_and_control",essential,64000)
    result={"socket_routes_retained":h,"local_repairs_retained":l,"critical_routes_retained":c,
            "native_rule_counts":dict(Counter(v["type"] for v in final["violations"])),
            "unconnected":len(final["unconnected_items"]),"parity":len(final["schematic_parity"])}
    (OUT/"routing_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result,flush=True)


if __name__=="__main__":
    main()
