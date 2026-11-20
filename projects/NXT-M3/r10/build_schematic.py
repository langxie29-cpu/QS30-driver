"""Emit a native KiCad schematic and engineering placement inputs."""
import csv
import json
import re
from uuid import uuid5, NAMESPACE_URL
from circuit import HERE, parts, kinds, mapping, gpio

EDA = HERE / "eda"
PROJECT = "NXT-M3-R10"
LIB = "R10_R10"
ROOT = None

def uid(name):
    return str(uuid5(NAMESPACE_URL, "nxt-m3/r10/" + name))

ROOT = uid("root")

def quote(value):
    return json.dumps(str(value), ensure_ascii=False)

def effect(size=1, other=""):
    return f"(effects (font (size {size} {size})) {other})"

def write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

def symbol(name, embedded=False):
    pins, _, _ = kinds[name]
    if name in ("R","C","L","Diode","Switch","Fuse","MOS","NPN","TP"):
        layout = {"R":[(-7.62,0),(7.62,0)], "C":[(-7.62,0),(7.62,0)],
                  "L":[(-7.62,0),(7.62,0)], "Diode":[(-7.62,0),(7.62,0)],
                  "Switch":[(-7.62,0),(7.62,0)], "Fuse":[(-7.62,0),(7.62,0)],
                  "TP":[(-7.62,0)], "NPN":[(-10.16,0),(10.16,-2.54),(10.16,2.54)],
                  "MOS":[(-10.16,0),(10.16,-2.54),(10.16,2.54)]}
        points = dict(zip(pins,layout[name]))
        halfheight = 3.81
    else:
        side = (len(pins)+1)//2
        halfheight = max(3.81,(side+1)*1.27)
        points = {n: ((-17.78 if i<side else 17.78),
                     ((side-1)//2 - i%side)*2.54) for i,n in enumerate(pins)}
    sid = LIB+":"+name if embedded else name
    stroke = "(stroke (width 0.254) (type default))"
    def line(*xy):
        return "(polyline (pts "+" ".join(f"(xy {x} {y})" for x,y in xy)+f") {stroke} (fill (type none)))"
    def box(x1,y1,x2,y2):
        return f"(rectangle (start {x1} {y1}) (end {x2} {y2}) {stroke} (fill (type background)))"
    if name == "R":
        graphic = box(-3.81,1.27,3.81,-1.27)
    elif name == "C":
        graphic = line((-3.81,0),(-1.27,0))+line((1.27,0),(3.81,0))
        graphic += line((-1.27,-2.54),(-1.27,2.54))+line((1.27,-2.54),(1.27,2.54))
    elif name == "Diode":
        graphic = line((-1.27,2.54),(-1.27,-2.54))+line((1.27,2.54),(-1.27,0),(1.27,-2.54),(1.27,2.54))
        graphic += line((-3.81,0),(-1.27,0))+line((1.27,0),(3.81,0))
    elif name == "Switch":
        graphic = line((-3.81,0),(-2.54,0))+line((2.54,0),(3.81,0))+line((-2.54,0),(2.54,2.54))
    elif name == "L":
        graphic = "(polyline (pts (xy -3.81 0) (xy -2.54 1.27) (xy -1.27 0) (xy 0 1.27) (xy 1.27 0) (xy 2.54 1.27) (xy 3.81 0)) "+stroke+" (fill (type none)))"
    else:
        margin = abs(next(iter(points.values()))[0])-3.81
        graphic = box(-margin,halfheight,margin,-halfheight)
    conventional = name in ("R","C","L","Diode","Switch","Fuse")
    pin_vis = "(pin_names (hide yes)) (pin_numbers (hide yes))" if conventional else "(pin_names (offset 0.508))"
    definition = [f"(symbol {quote(sid)} {pin_vis} (exclude_from_sim no) (in_bom yes) (on_board yes)",
                  f'(property "Reference" "U" (at 0 {halfheight+3} 0) {effect()})',
                  f'(property "Value" {quote(name)} (at 0 {-halfheight-3} 0) {effect()})',
                  f'(symbol "{name}_0_1" {graphic})', f'(symbol "{name}_1_1"']
    for n,(label,electrical) in pins.items():
        x,y = points[n]
        definition.append(f"(pin {electrical} line (at {x} {y} {0 if x<0 else 180}) (length 3.81)"
                          f" (name {quote(label)} {effect(0.84)}) (number {quote(n)} {effect(0.84)}))")
    return " ".join(definition) + "))", points, halfheight

def note(value,x,y,size=1.25):
    return (f"(text {quote(value)} (at {x} {y} 0) {effect(size,'(justify left)')}"
            f' (uuid "{uid(value+str(x)+str(y))}"))')

def page(title, identity, symbols=""):
    return [f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{identity}") (paper "A3")',
            f'(title_block (title "{PROJECT} / {title}") (rev "R10 engineering HOLD")'
            ' (comment 1 "GATE_0 REWORK / no high-voltage energization or manufacturing"))',
            f"(lib_symbols {symbols})"]

def place(part,x,y,sid):
    x,y = (round(round(n/1.27)*1.27, 4) for n in (x,y))
    ref,name=part["ref"],part["kind"]
    _,points,h=symbol(name,True)
    physical = name != "Flag"
    yesno = "yes" if physical else "no"
    dnp = "yes" if part["status"]=="HOLD_DNP" else "no"
    st = [f'(symbol (lib_id "{LIB}:{name}") (at {x} {y} 0) (unit 1) (exclude_from_sim no)'
          f' (in_bom {yesno}) (on_board {yesno}) (dnp {dnp}) (uuid "{uid(ref)}")']
    fields = [("Reference",ref,-h-4,True),("Value",part["value"],-h-1.7,True),
              ("Footprint",part["fp"],0,False),("Datasheet",part["url"],0,False),
              ("MPN",part["mpn"],0,False),("Status",part["status"],0,False)]
    for field,val,dy,visible in fields:
        st.append(f'(property "{field}" {quote(val)} (at {x} {y+dy:.4f} 0)'
                  f' {effect(.95,"" if visible else "(hide yes)")})')
    for n in points:
        st.append(f'(pin "{n}" (uuid "{uid(ref+"/"+n)}"))')
    st.append(f'(instances (project "{PROJECT}" (path "/{ROOT}/{sid}" (reference "{ref}") (unit 1)))))')
    for n,net in part["nets"].items():
        xx,yy=points[n]
        px,py=round(x+xx,4),round(y-yy,4)
        tag=uid(f"{ref}-pin-{n}")
        if net is None:
            st.append(f'(no_connect (at {px} {py}) (uuid "{tag}"))')
            continue
        lx=round(px+(-2.54 if xx<0 else 2.54),4)
        st.append(f'(wire (pts (xy {px} {py}) (xy {lx} {py})) (stroke (width 0) (type default)) (uuid "{tag}"))')
        st.append(f'(global_label "{net}" (shape bidirectional) (at {lx} {py} {180 if xx<0 else 0})'
                  f' {effect(.78,"(justify left)")} (uuid "{uid(ref+"-label-"+n)}")'
                  f' (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {lx} {py} 0) {effect(.8,"(hide yes)")}))')
    return st

NOTES = {
    "ESP32":"UART0 ROM recovery uses 3.3 V logic. Hold SW1 low and pulse J2 reset. No external supply through J2.",
    "Input_and_3V3":"Input protection and power ramp remain engineering candidates. Fixed 3.3 V feedback uses VOS.",
    "OLED":"A-side is the switched OLED domain. Confirm module pinout, pull-up loading and 3.3 V function before fitting.",
    "Hardware_inhibit":"OE_N is pulled high. Local ARM and the MCU request must both be true to pull it low. Fault or reset clears ARM.",
    "Shift_registers":"Send frame bit 31 first. Bits 31 and 30 are zero. Shift then latch zero while blanked after reset.",
    "Tube_interfaces":"Logical pins inherit the R8/R7 candidate tube map. Socket footprint, key and hole coordinates are TBD.",
    "HV_cutoff":"R40 open DNP. eFuse branch and converter DNP for engineering HOLD. Components downstream of R40 can still store energy.",
    "Analog_protection":"Separate divider inputs for OVP and residual voltage. Detection coverage, hysteresis, delay and diagnostics remain open.",
    "Gate_bias":"Provisional 11.6 V cell from the switched feed. Qualification includes disabled precharge, backfeed and sequencing.",
    "HV_boost":"DCM boost design candidate. Bias, RT, slope/current limit, loop compensation, peak stress and snubber are unqualified.",
    "HV_bleeders":"Two independent passive paths. Each chain has four series resistors and must retain separate layout paths.",
}

def build():
    EDA.mkdir(exist_ok=True)
    groups={}
    for part in parts:
        groups.setdefault(part["sheet"],[]).append(part)
    root = page("Overview",ROOT)
    root.extend([note("NXT / THREE STATIC DIGITS / R10",22,20,2.3),
                 note("5 V / ESP32-S3 / 0.91 inch I2C OLED / 4 x 74HC595 / 30 x MMBTA42",22,28,1.3),
                 note("GATE_0 = REWORK     ENGINEERING_RELEASE = HOLD     R40 OPEN DNP",22,36,1.4),
                 note("Logical socket pins are reviewable. Physical socket lands remain undefined.",22,44)])
    for number,(name,group) in enumerate(groups.items(),2):
        sid = uid("sheet-"+name)
        i=number-2
        x,y=25+125*(i%3),60+37*(i//3)
        root.append(f'(sheet (at {x} {y}) (size 105 24) (stroke (width .254) (type default))'
                    f' (fill (color 0 0 0 0)) (uuid "{sid}")'
                    f' (property "Sheetname" "{name}" (at {x} {y-1} 0) {effect(1.2,"(justify left)")})'
                    f' (property "Sheetfile" "{name}.kicad_sch" (at {x} {y+25} 0) {effect(.9,"(justify left)")})'
                    f' (instances (project "{PROJECT}" (path "/{ROOT}" (page "{number}")))))')
        content = page(name,uid("file-"+name)," ".join(symbol(k,True)[0] for k in sorted({p["kind"] for p in group})))
        content.append(note(name.replace("_"," "),16,14,1.8))
        content.append(note(NOTES.get(name,"Static sink stages. Each channel: series base resistor, base-emitter pull-down, emitter to GND."),16,22))
        if name.startswith("Cathodes_"):
            for i,part in enumerate(group):
                digit, stage=divmod(i,3)
                x=45+(digit%5)*79
                y=48+(digit//5)*112+stage*29
                content.extend(place(part,x,y,sid))
        elif name=="ESP32":
            content.extend(place(group[0],73,85,sid))
            for i,part in enumerate(group[1:]):
                x=148+68*(i%4)
                y=46+41*(i//4)
                content.extend(place(part,x,y,sid))
        else:
            for i,part in enumerate(group):
                x=48+80*(i%5)
                y=52+45*(i//5)
                content.extend(place(part,x,y,sid))
        write(EDA/f"{name}.kicad_sch",content+[")"])
    write(EDA/f"{PROJECT}.kicad_sch",root+['(sheet_instances (path "/" (page "1")))',")"])
    write(EDA/f"{LIB}.kicad_sym",['(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor")',
                                *(symbol(k)[0] for k in sorted(kinds)),")"])
    write(EDA/"sym-lib-table",['(sym_lib_table (version 7)',
          f' (lib (name "{LIB}") (type "KiCad") (uri "${{KIPRJMOD}}/{LIB}.kicad_sym") (options "") (descr "R10 reviewed candidate pin definitions")))'])
    write(EDA/"fp-lib-table",['(fp_lib_table (version 7)',
          f' (lib (name "{LIB}") (type "KiCad") (uri "${{KIPRJMOD}}/{LIB}.pretty") (options "") (descr "R10 candidate package land patterns")))'])
    tables = {
        "GPIO.csv": (("gpio","module_pin","net","mode","reset_or_function"),gpio),
        "CATHODE_MAP.csv": (("frame_bit","transmit_index","register","register_pin","output",
                            "bjt_B_E_C_pads","base","cathode","logical_socket_pin","status"),mapping),
        "COMPONENT_FOOTPRINT_MAP.csv": (("ref","sheet","symbol","value","mpn","footprint","status","datasheet"),
            [[p["ref"],p["sheet"],p["kind"],p["value"],p["mpn"],p["fp"],p["status"],p["url"]]
             for p in parts if p["kind"]!="Flag"]),
        "PHYSICAL_PIN_MAP.csv": (("ref","pad","function","net"),
            [[p["ref"],n,kinds[p["kind"]][0][n][0],net]
             for p in parts if p["kind"]!="Flag" for n,net in p["nets"].items()]),
    }
    for name,(columns,rows) in tables.items():
        with (HERE/name).open("w",newline="",encoding="utf-8") as stream:
            writer=csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)
    project = EDA/f"{PROJECT}.kicad_pro"
    if not project.exists():
        write(project,[json.dumps({"meta":{"filename":project.name,"version":1},
            "erc":{"erc_exclusions":[],"meta":{"version":0}},
            "schematic":{"meta":{"version":1}},
            "text_variables":{"QUALIFICATION":"HOLD"}},indent=2)])

def build_patterns():
    path=EDA/f"{LIB}.pretty"
    path.mkdir(exist_ok=True)
    # TI RPW0010A candidate. CAD overlay against drawing 4225183/A remains open.
    pads=[]
    for i,y in enumerate((-0.7125,-0.2375,0.2375,0.7125)):
        for side,pin in ((-1,1+i),(1,10-i)):
            pads.append((pin,side*.9,y,.6,.25))
    for i,y in enumerate((-.7125,.7125)):
        for side,pin in ((-1,(1,4)[i]),(1,(10,7)[i])):
            pads.append((pin,side*.65,y,.25,.325))
    pads.extend([(5,-.2375,0,.25,1.75),(6,.2375,0,.25,1.75)])
    def smd(p):
        n,x,y,w,h=p
        return f' (pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio .15))'
    write(path/"TI_RPW0010A.kicad_mod",[
        '(footprint "TI_RPW0010A" (version 20241229) (generator pcbnew) (layer "F.Cu") (attr smd)',
        ' (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))',
        ' (fp_text value "TI_RPW0010A" (at 0 1.8) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))',
        ' (fp_rect (start -1 -1) (end 1 1) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))',
        ' (fp_rect (start -1.5 -1.3) (end 1.5 1.3) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))',
        *map(smd,pads),')'])
    # B32774M family drawing: lead spacing 27.5 +/-0.4 mm; leads 0.8 mm.
    write(path/"TDK_B32774M4335K000.kicad_mod",[
        '(footprint "TDK_B32774M4335K000" (version 20241229) (generator pcbnew) (layer "F.Cu") (attr through_hole)',
        ' (fp_text reference "REF**" (at 0 -7) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))',
        ' (fp_text value "TDK_B32774M4335K000" (at 0 7) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))',
        ' (fp_rect (start -15.75 -5.5) (end 15.75 5.5) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))',
        ' (fp_rect (start -16.25 -6) (end 16.25 6) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))',
        ' (pad "1" thru_hole rect (at -13.75 0) (size 2.3 2.3) (drill 1.3) (layers "*.Cu" "*.Mask"))',
        ' (pad "2" thru_hole circle (at 13.75 0) (size 2.3 2.3) (drill 1.3) (layers "*.Cu" "*.Mask"))',')'])

if __name__ == "__main__":
    build()
    build_patterns()
