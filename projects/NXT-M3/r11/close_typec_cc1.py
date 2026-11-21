"""Escape CC1 on the connector side while preserving the completed VBUS feed."""
import json

import pcbnew as pcb

from close_r11_blockers import OUT,geometry,native,pad_at,verify_candidate
from precision_route import Terminal
from route import EDA
from socket_route_repair import BLOCK
from typec_connector_breakout import append,segments,via,xy

VBUS_EDGES=(
    {(117.23,55.905),(117.23,54.32)},
    {(117.23,54.32),(120.27,54.32)},
    {(120.27,54.32),(120.27,55.905)},
    {(117.23,55.905),(117.375,55.625)},
    {(117.375,55.625),(117.375,54.75)},
    {(117.375,54.75),(120.125,54.75)},
    {(120.125,54.75),(120.125,55.625)},
    {(120.125,55.625),(120.27,55.905)},
)
FAULT_EDGES=(
    {(114.75,54.5),(115.75,53.45)},
    {(115.75,53.45),(121.75,53.45)},
    {(121.75,53.45),(122.75,54.5)},
)


def remove(block):
    if "(segment" not in block:
        return False
    pair={xy(block,"start"),xy(block,"end")}
    return (('(net "5V_RAW")' in block and pair in VBUS_EDGES) or
            ('(net "FAULT_N")' in block and pair in FAULT_EDGES))


def main():
    baseline,_=native("cc1_before")
    original=EDA.read_bytes()
    removed=[]
    def filter_block(match):
        if remove(match[0]):
            removed.append(match[0])
            return ""
        return match[0]
    board=BLOCK.sub(filter_block,EDA.read_text(encoding="utf-8"))
    assert len(removed)==11,len(removed)
    kept=False
    attempts=[]
    for index,(track_y,fault_y,cc_via) in enumerate(((54.,53.425,(119.25,54.87)),
            (53.975,53.39,(119.25,54.84)),(54.025,53.44,(119.17,54.88))),1):
        power=segments("5V_RAW","F",[(117.23,55.905),(117.23,track_y),(120.27,track_y),(120.27,55.905)],.5)
        alarm=segments("FAULT_N","F",[(114.75,54.5),(115.75,fault_y),(121.75,fault_y),(122.75,54.5)],.2)
        breakout=segments("USBC_CC1","F",[(119.25,55.905),cc_via],.2)+[via("USBC_CC1",cc_via)]
        proposed=power+alarm+breakout
        EDA.write_text(append(board,proposed),encoding="utf-8")
        current=pcb.LoadBoard(str(EDA))
        end=Terminal.pad(pad_at(current,"D5","1"))
        extra=geometry(current,"USBC_CC1",Terminal(cc_via,(0,1)),end,7.)
        if not extra:
            # Both vias were geometrically cleared in the four-layer test.
            # The corresponding two-layer path still has to find a legal detour.
            land=(117.2,59.15)
            tail=[via("USBC_CC1",land)]+segments("USBC_CC1","B",[land,(117.2,58.75)],.2)
            EDA.write_text(append(board,proposed+tail),encoding="utf-8")
            current=pcb.LoadBoard(str(EDA))
            detour=geometry(current,"USBC_CC1",Terminal(cc_via,(0,1)),Terminal(land,(0,1)),7.)
            if detour:
                extra=tail+detour
        if not extra:
            EDA.write_bytes(original)
            attempts.append({"case":index,"reason":"no legal escape to D5 in search"})
            continue
        EDA.write_text(append(board,proposed+extra),encoding="utf-8")
        _,receipt=verify_candidate(f"cc1_edge_{index}",original,baseline,proposed+extra)
        attempts.append(receipt)
        if receipt["accepted"]:
            kept=True
            break
    (OUT/"cc1_layout_trials.json").write_text(json.dumps({"closed":kept,"trials":attempts},indent=2)+"\n",
                                             encoding="utf-8")
    print("CC1 closed:",kept)


if __name__=="__main__":
    main()
