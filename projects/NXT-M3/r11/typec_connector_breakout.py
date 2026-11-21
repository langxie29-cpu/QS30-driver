"""Edit the short Type-C connector corridor and accept only native-DRC-clean copper."""
import json
import re
from uuid import uuid4

from typec_pcb import EDA, OUT, drc

BLOCK = re.compile(r"(?m)^\t\((segment|via)\n.*?^\t\)\n",re.S)


def segments(net,side,points,width):
    return [f'\t(segment\n\t\t(start {x} {y})\n\t\t(end {xx} {yy})\n\t\t(width {width})\n'
            f'\t\t(layer "{side}.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid4()}")\n\t)\n'
            for (x,y),(xx,yy) in zip(points,points[1:])]


def via(net,xy):
    return (f'\t(via\n\t\t(at {xy[0]} {xy[1]})\n\t\t(size 0.6)\n\t\t(drill 0.3)\n'
            f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid4()}")\n\t)\n')


def net(block):
    return re.search(r'\(net "([^"]+)"\)',block)[1]


def xy(block,key):
    return tuple(map(float,re.search(r"\("+key+r" ([0-9.]+) ([0-9.]+)\)",block).groups()))


def trim_input(board):
    def edit(match):
        value = match[0]
        signal = net(value)
        if signal=="5V_RAW":
            if match[1]=="via" and xy(value,"at")== (120.27,54.25):
                return ""
            if match[1]=="segment":
                endpoints={xy(value,"start"),xy(value,"end")}
                discarded=({(117.23,55.905),(117.23,54.25)},{(117.23,54.25),(120.27,54.25)},
                           {(120.27,54.25),(120.27,55.905)},
                           {(117.23,55.905),(117.375,56.125)}, {(117.375,56.125),(117.375,57.)},
                           {(117.375,57.),(120.125,57.)},{(120.125,57.),(120.125,56.125)},
                           {(120.27,55.905),(120.125,56.125)})
                if endpoints in discarded:
                    return ""
        if signal=="FAULT_N" and match[1]=="segment" and {
            xy(value,"start"),xy(value,"end")}=={(105.,54.5),(138.75,54.5)}:
            return ""
        return value
    return BLOCK.sub(edit,board)


def append(board, items):
    return board.rstrip()[:-1]+"".join(items)+")\n"


def verdict(label,board,items):
    candidate=append(board,items)
    EDA.write_text(candidate,encoding="utf-8")
    output=drc(label,fill=True)
    ids={re.search(r'\(uuid "([^"]+)"\)',piece)[1] for piece in items}
    new=[row for row in output["violations"] if any(item["uuid"] in ids for item in row["items"])]
    return not new,candidate


def main():
    original=EDA.read_text(encoding="utf-8")
    base=trim_input(original)
    stroke=segments("FAULT_N","F",[(105,54.5),(114.75,54.5),(115.75,53.45),(121.75,53.45),
                                     (122.75,54.5),(138.75,54.5)],.2)
    stroke+=segments("5V_RAW","F",[(117.23,55.905),(117.23,54.32),(120.27,54.32),(120.27,55.905)],.5)
    good,current=verdict("connector_corridor",base,stroke)
    if not good:
        # Return to the no-extra-rule-violation local tie around the inner side of J1.
        board=trim_input(original)
        paths=segments("FAULT_N","F",[(105,54.5),(138.75,54.5)],.2)
        paths+=segments("5V_RAW","F",[(117.23,55.905),(117.375,56.125),(117.375,57),
                                     (120.125,57),(120.125,56.125),(120.27,55.905)],.5)
        good,current=verdict("connector_restore",board,paths)
        assert good,"Review the connector region before release"
    retained={"reworked_corridor":"connector_corridor" if good and "53.45" in current else "original"}
    if retained["reworked_corridor"]!="original":
        for name,x,options in (
            ("USBC_CC1",119.25,[
                [(119.25,57),(119.25,58.4375),(117.95,58.4375)],
                [(119.25,57),(118.95,57.55),(118.95,58.44),(117.95,58.4375)]]),
            ("USBC_CC2",118.25,[
                [(118.25,57),(118.25,54.7),(116.05,54.7),(116.05,58.4375)],
                [(118.25,57),(118.25,55.1),(115.9,55.1),(115.9,58.25),(116.05,58.4375)]]),
        ):
            retained[name]=False
            for index,path in enumerate(options,1):
                trial=segments(name,"F",[(x,55.905),(x,57)],.2)+[via(name,(x,57))]
                trial+=segments(name,"B",path,.2)
                fit,new=verdict(f"connector_{name}_{index}",current,trial)
                if fit:
                    current=new
                    retained[name]=True
                    break
    EDA.write_text(current,encoding="utf-8")
    drc("connector_breakout_final",fill=True)
    (OUT/"connector_breakout.json").write_text(json.dumps(retained,indent=2)+"\n",encoding="utf-8")
    print(retained)


if __name__=="__main__":
    main()
