"""Test moving the long protected 5 V trunk below the USB-C control area."""
import json

from close_r11_blockers import OUT,native,open_nets,prior_issue_ids,task
from route import EDA
from socket_route_repair import BLOCK
from typec_connector_breakout import append,segments,via,xy


def main():
    preview=OUT/"four_layer_cc1_preview.kicad_pcb"
    if not preview.exists():
        raise ValueError("Generate the four-layer CC1 preview first")
    original=EDA.read_bytes()
    project=EDA.with_suffix(".kicad_pro")
    config=project.read_bytes()
    summary={}
    try:
        EDA.write_bytes(preview.read_bytes())
        start,_=native("four_layer_trunk_start")
        raw=EDA.read_text(encoding="utf-8")
        near=(86.5,58.25)
        far=(136.75,58.25)
        count=[]
        def drop(match):
            text=match[0]
            if '(net "5V_PROT")' in text and "(segment" in text and {xy(text,"start"),xy(text,"end")}=={near,far}:
                count.append(1)
                return ""
            return text
        altered=BLOCK.sub(drop,raw)
        assert len(count)==1,len(count)
        passed=False
        receipts=[]
        for shift in (.65,.8,1.0,1.2,1.4):
            left=(near[0]+shift,near[1])
            paths=segments("5V_PROT","F",[near,left],.5)+segments("5V_PROT","In2",[left,far],.5)
            paths += [via("5V_PROT",left),via("5V_PROT",far)]
            EDA.write_text(append(altered,paths),encoding="utf-8")
            trial,record=native(f"four_layer_power_trunk_{int(shift*100)}")
            receipts.append(record)
            passed=(not (prior_issue_ids(trial)-prior_issue_ids(start))
                    and open_nets(trial)["5V_PROT"]<=open_nets(start)["5V_PROT"])
            if passed:
                break
        summary={"protected_trunk_routed_on_in2":passed,"trunk_trials":receipts}
        if passed:
            changes=[]
            for item in (("USBC_1V2","U26","21","C53","1"),("USBC_2V7","U26","23","C54","1")):
                trial,after=task(trial,item,"four_layer_"+item[0])
                changes.append(after)
            summary.update(route_trials=changes,unconnected_after=len(trial["unconnected_items"]))
            if len(trial["unconnected_items"])<len(start["unconnected_items"]):
                result=OUT/"four_layer_controls_preview.kicad_pcb"
                result.write_bytes(EDA.read_bytes())
                summary["retained_alternate"]=result.name
    finally:
        EDA.write_bytes(original)
        project.write_bytes(config)
    (OUT/"four_layer_trunk_comparison.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(summary)


if __name__=="__main__":
    main()
