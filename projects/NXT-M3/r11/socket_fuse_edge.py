"""Turn the symmetric fuse so the Type-C VBUS edge feed can reach its input."""
import json
import re

import pcbnew as pcb

from route import EDA
from socket_route_repair import BLOCK,OUT,native
from typec_connector_breakout import append,segments,via,xy

OLD_FUSED = (
    {(71.75,51),(81.25,51)},
    {(81.25,51),(81.25,52.25)},
    {(81.25,52.25),(82.75,52.25)},
    {(82.75,52.25),(82.9,52.5)},
)


def remove_old(match):
    block=match[0]
    if '(net "5V_FUSED")' in block and "(segment" in block and {xy(block,"start"),xy(block,"end")} in OLD_FUSED:
        return ""
    return block


def main():
    original=EDA.read_bytes()
    board=pcb.LoadBoard(str(EDA))
    fuse=next(fp for fp in board.GetFootprints() if fp.GetReference()=="F1")
    assert fuse.GetOrientationDegrees()==0
    fuse.SetOrientationDegrees(180)
    pcb.SaveBoard(str(EDA),board)
    boardtext=BLOCK.sub(remove_old,EDA.read_text(encoding="utf-8"))
    repaired=segments("5V_FUSED","F",[(71.75,51),(80.1,51),(80.1,52.5)],.5)
    accepted=False
    for index,height in enumerate((50.625,50.675,50.7),1):
        land_a,land_b=(120.27,height),(120.27,54.32)
        feed=segments("5V_RAW","F",[(82.9,52.5),(82.9,height),land_a],.5)
        feed+=segments("5V_RAW","B",[land_a,land_b],.5)
        additions=repaired+feed+[via("5V_RAW",land_a),via("5V_RAW",land_b)]
        EDA.write_text(append(boardtext,additions),encoding="utf-8")
        data=native(f"fuse_clockwise_{index}")
        ids={re.search(r'\(uuid "([^"]+)"\)',piece)[1] for piece in additions}
        if not any(item["uuid"] in ids for issue in data["violations"] for item in issue["items"]):
            accepted=True
            break
    if not accepted:
        EDA.write_bytes(original)
    (OUT/"fuse_edge_feed.json").write_text(json.dumps({"vbus_to_fuse_retained":accepted},indent=2)+"\n",
                                          encoding="utf-8")
    print("VBUS edge-feed copper retained:",accepted)


if __name__=="__main__":
    main()
