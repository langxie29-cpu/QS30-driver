"""Join J1 VBUS to F1 using a DRC-checked top-edge bottom-layer corridor."""
import json

from typec_connector_breakout import EDA,OUT,drc,segments,via,verdict


def main():
    original=EDA.read_text(encoding="utf-8")
    source=(120.27,54.32)
    approved=False
    for index,(landing,height) in enumerate((
        ((80.1,54.0),53.50),((80.1,54.35),53.625),((79.75,54.25),53.50),
        ((79.5,53.6),53.50),((80.9,54.1),53.625),((79.0,52.5),53.55),
    ),1):
        x,y=landing
        xs,ys=source
        top=segments("5V_RAW","F",[(80.1,52.5),landing],.5)
        bottom=segments("5V_RAW","B",[landing,(x,height),(xs,height),source],.5)
        available,candidate=verdict(f"connector_fuse_south_{index}",original,
            top+[via("5V_RAW",landing),via("5V_RAW",source)]+bottom)
        if available:
            approved=True
            break
    EDA.write_text(candidate if approved else original,encoding="utf-8")
    drc("connector_fuse_final",fill=True)
    (OUT/"connector_fuse_summary.json").write_text(json.dumps(
        {"connector_to_fuse_copper_retained":approved},indent=2)+"\n",encoding="utf-8")
    print("J1-to-F1 candidate accepted",approved)


if __name__ == "__main__":
    main()
