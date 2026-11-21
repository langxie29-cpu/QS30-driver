"""Try preserving the fuse output land while reaching its input from the edge."""
import json
import re

import pcbnew as pcb

from route import EDA,pos,vec
from socket_route_repair import OUT,native
from typec_connector_breakout import append,segments,via


def main():
    original=EDA.read_bytes()
    baseline=native("fuse_pivot_baseline")
    board=pcb.LoadBoard(str(EDA))
    fuse=next(fp for fp in board.GetFootprints() if fp.GetReference()=="F1")
    pads={p.GetNumber():p for p in fuse.Pads()}
    output=pos(pads["2"])
    home=pos(fuse)
    accepted=None
    for angle in (156,158,160,162,164,166,168):
        fuse.SetPosition(vec(*home))
        fuse.SetOrientationDegrees(angle)
        dx,dy=(target-located for target,located in zip(output,pos(pads["2"])))
        fuse.SetPosition(vec(home[0]+dx,home[1]+dy))
        raw=pos(pads["1"])
        edge=(120.27,50.675)
        entry=(120.27,54.32)
        copper=segments("5V_RAW","F",[raw,(raw[0],edge[1]),edge],.5)
        copper+=segments("5V_RAW","B",[edge,entry],.5)+[via("5V_RAW",edge),via("5V_RAW",entry)]
        ids={re.search(r'\(uuid "([^"]+)"\)',piece)[1] for piece in copper}
        ids.update(str(pad.m_Uuid.AsString()) for pad in fuse.Pads())
        pcb.SaveBoard(str(EDA),board)
        eda=EDA.read_text(encoding="utf-8")
        EDA.write_text(append(eda,copper),encoding="utf-8")
        check=native(f"fuse_pivot_{angle}")
        near_fuse=[issue for issue in check["violations"] if any(i["uuid"] in ids for i in issue["items"])]
        if not near_fuse and len(check["violations"])<=len(baseline["violations"]):
            accepted={"fuse_angle_deg":angle,"fuse_output_mm":output,
                      "fuse_input_mm":raw,"J1_to_F1_VBUS_path":True}
            break
    if not accepted:
        EDA.write_bytes(original)
    (OUT/"fuse_pivot_summary.json").write_text(json.dumps(accepted or {"J1_to_F1_VBUS_path":False},
                                                        indent=2)+"\n",encoding="utf-8")
    print("Accepted:",accepted)


if __name__=="__main__":
    main()
