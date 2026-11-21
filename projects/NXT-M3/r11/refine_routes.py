"""Refine selected open power and interface routes on the saved R3 draft."""
import json
import math

import pcbnew as pcb

import route

CRITICAL = {"MCU_SDA","MCU_SCL","OLED_SDA","OLED_SCL","HC_CLEAR_N","SR_CLK_BUS","SR_LATCH_BUS",
            "SER1","SER2","SER3","5V_PROT","5V_FUSED","HV_ISOLATE_IN","LV_SW",
            "5V_HV","GATE_HV","GATE_SRC","GATE_SNK","HV_CS","UART_HDR_RX","UART_HDR_TX",
            "BOOT_N","FAULT_N","BIAS_OK","PWM_PERMIT"}


def main():
    route.STEP,route.NX,route.NY = .125,1041,641
    board = pcb.LoadBoard(str(route.EDA))
    for zone in list(board.Zones()):
        if zone.GetZoneName().startswith("R11 LV GND draft"):
            board.Remove(zone)
    design = route.Draft(board)
    for item in board.GetTracks():
        via = isinstance(item,pcb.PCB_VIA)
        layers = (0,1) if via else (route.LAYERS.index(item.GetLayer()),)
        design.obstacles.append((item.GetNetname(), layers, route.box(item), "via" if via else "track"))
    raw = json.loads((route.HERE/"evidence/r3/return_initial.json").read_text(encoding="utf-8-sig"))
    ids = {str(p.m_Uuid.AsString()):net for net,entries in design.pads.items() for ref,p,side in entries}
    ids.update({str(t.m_Uuid.AsString()):t.GetNetname() for t in board.GetTracks()})
    jobs = []
    for issue in raw["unconnected_items"]:
        one,two = issue["items"]
        net = ids.get(one["uuid"], ids.get(two["uuid"]))
        if net not in CRITICAL:
            continue
        d = []
        for endpoint in (one,two):
            x,y = endpoint["pos"]["x"],endpoint["pos"]["y"]
            d.append(sorted(design.pads[net], key=lambda entry:math.dist((x,y),route.pos(entry[1])))[:3])
        options = [(math.dist(route.pos(a[1]),route.pos(b[1])),a,b) for a in d[0] for b in d[1] if a!=b]
        if options:
            jobs.append((net, sorted(options,key=lambda job:job[0])))
    accepted = set()
    for net, options in jobs:
        for score,a,b in options[:3]:
            key = tuple(sorted((str(a[1].m_Uuid.AsString()), str(b[1].m_Uuid.AsString()))))
            if key in accepted:
                break
            before = len(design.saved)
            design.route(net,a,b,70000)
            if len(design.saved)>before:
                accepted.add(key)
                break
    # Store this checkpoint for R4, including the native pre-pour rule check.
    data = design.save_drc("refinement_candidate")
    bad = {item["uuid"] for violation in data["violations"] for item in violation["items"]}
    for record in list(design.saved):
        if any(item.m_Uuid.AsString() in bad for item in record[3]):
            for item in record[3]:
                board.Remove(item)
            design.saved.remove(record)
    design.save_drc("refinement")
    print("New route intents retained", len(design.saved), flush=True)
    (route.HERE/"evidence/r4/refinement_paths.json").write_text(
        json.dumps([{"net":net,"from":a,"to":b,"items":len(items)} for net,a,b,items in design.saved],indent=2)+"\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
