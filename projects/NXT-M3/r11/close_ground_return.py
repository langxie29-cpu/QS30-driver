"""Extend the existing LV ground plane and connect the module's castellated grounds."""
import json

import pcbnew as pcb

from close_r11_blockers import OUT, native, pad_at, prior_issue_ids
from route import EDA, pos
from typec_connector_breakout import append, segments, via

ZONE = "R11 LV GND draft, outside RF reserve"


def add_ground_return(board):
    zone = next(item for item in board.Zones() if item.GetZoneName() == ZONE)
    outline = zone.Outline()
    polygon = [(70, 54), (120, 54), (120, 87), (50.35, 87), (50.35, 62), (70, 62)]
    outline.RemoveAllContours()
    outline.NewOutline()
    for x, y in polygon:
        outline.Append(pcb.FromMM(x), pcb.FromMM(y))
    return polygon


def main():
    baseline, reference = native("ground_return_before")
    original = EDA.read_bytes()
    retain = False
    try:
        board = pcb.LoadBoard(str(EDA))
        polygon = add_ground_return(board)
        pcb.SaveBoard(str(EDA), board)
        proposal = []
        terminals = []
        for pin in ("1", "40"):
            start = pos(pad_at(board, "U3", pin))
            offset = 1.25 if pin == "1" else -1.25
            end = (start[0], round(start[1] + offset, 6))
            proposal += segments("GND", "F", [start, end], .25) + [via("GND", end)]
            terminals.append({"pin": pin, "pad": start, "via": end})
        EDA.write_text(append(EDA.read_text(encoding="utf-8"), proposal), encoding="utf-8")
        result, run = native("ground_return_trial")
        added = sorted(prior_issue_ids(result) - prior_issue_ids(baseline))
        less_open = len(result["unconnected_items"]) < len(baseline["unconnected_items"])
        retain = not added and less_open and result["schematic_parity"] == baseline["schematic_parity"]
        record = {"retained": retain, "before": reference, "trial": run,
                  "open_before": len(baseline["unconnected_items"]),
                  "open_trial": len(result["unconnected_items"]),
                  "new_rule_violations": added, "zone_outline": polygon,
                  "u3_connections": terminals}
        (OUT / "ground_return_comparison.json").write_text(json.dumps(record, indent=2) + "\n",
                                                           encoding="utf-8")
        print(record, flush=True)
    finally:
        if not retain:
            EDA.write_bytes(original)


if __name__ == "__main__":
    main()
