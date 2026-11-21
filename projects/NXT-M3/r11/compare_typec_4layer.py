"""Compare a four-layer routing candidate without changing the two-layer board."""
import json

import pcbnew as pcb

from close_r11_blockers import OUT, native, open_nets, prior_issue_ids
from close_typec_cc1 import remove
from route import EDA
from socket_route_repair import BLOCK
from typec_connector_breakout import append,segments,via


def main():
    baseline,_=native("layer_comparison_before")
    original=EDA.read_bytes()
    project=EDA.with_suffix(".kicad_pro")
    project_backup=project.read_bytes()
    winner={}
    try:
        board=pcb.LoadBoard(str(EDA))
        board.SetCopperLayerCount(4)
        module = next(fp for fp in board.GetFootprints() if fp.GetReference() == "U3")
        keepout_layers = pcb.LSET()
        for layer in (pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu):
            keepout_layers.AddLayer(layer)
        for zone in module.Zones():
            if zone.GetIsRuleArea():
                zone.SetLayerSet(keepout_layers)
        pcb.SaveBoard(str(EDA),board)
        setup=BLOCK.sub(lambda m:"" if remove(m[0]) else m[0],EDA.read_text(encoding="utf-8"))
        power=segments("5V_RAW","F",[(117.23,55.905),(117.23,54),(120.27,54),(120.27,55.905)],.5)
        alarm=segments("FAULT_N","F",[(114.75,54.5),(115.75,53.425),(121.75,53.425),(122.75,54.5)],.2)
        source=(119.25,54.87)
        target_options=[
            ((116.75,59.625),None),((116.75,59.125),None),((116.75,58.75),None),
            ((117.25,58.75),None),((117.60,59.15),(117.75,58.75)),
            ((117.60,59.25),(117.75,58.75)),((115.95,59.625),None),
            ((118.12,58.45),None),((118.05,58.9),(117.75,58.75)),
            ((117.2,59.15),(117.2,58.75)),((117.35,59.15),(117.35,58.75)),
            ((116.30,59.625),None),((116.0,59.625),None)]
        first=segments("USBC_CC1","F",[(119.25,55.905),source],.2)+[via("USBC_CC1",source)]
        for index,(target,join) in enumerate(target_options,1):
            wire=segments("USBC_CC1","In1",[source,target],.2)+[via("USBC_CC1",target)]
            if join:
                wire+=segments("USBC_CC1","B",[target,join],.2)
            EDA.write_text(append(setup,power+alarm+first+wire),encoding="utf-8")
            attempt,receipt=native(f"four_layer_cc1_{index}")
            extra=prior_issue_ids(attempt)-prior_issue_ids(baseline)
            if all(kind=="lib_footprint_mismatch" for kind,_ in extra) and not open_nets(attempt)["USBC_CC1"]:
                preview=OUT/"four_layer_cc1_preview.kicad_pcb"
                preview.write_bytes(EDA.read_bytes())
                winner={"candidate":preview.name,"native":receipt["raw"],"cc1_closed":True,
                        "raw_drc_items":len(attempt["violations"]),"unconnected":len(attempt["unconnected_items"]),
                        "pcb_layers":4,"remaining_new_warning_types":sorted({kind for kind,_ in extra})}
                break
    finally:
        EDA.write_bytes(original)
        project.write_bytes(project_backup)
    (OUT/"four_layer_comparison.json").write_text(json.dumps(winner or {"cc1_closed":False},
                                             indent=2)+"\n",encoding="utf-8")
    print(winner or "Four-layer CC1 trials did not qualify")


if __name__=="__main__":
    main()
