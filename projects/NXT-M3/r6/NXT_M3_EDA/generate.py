"""Build a native KiCad 10 hierarchy and local symbol/footprint libraries."""
from collections import defaultdict
import json
from pathlib import Path
import uuid
from design import parts, types

HERE = Path(__file__).resolve().parent
PROJECT = 'NXT-M3'
LIB = 'NXT_M3'

def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'nxt-m3/r6/'+name))

def quote(value):
    return json.dumps(str(value), ensure_ascii=False)

def effect(size=.9, more=''):
    return f'(effects(font(size {size} {size})){more})'

def write(file, contents):
    (HERE/file).write_text(contents+'\n', encoding='utf-8', newline='\n')

def symbol(kind, embedded=False):
    pins = types[kind]
    mid = (len(pins)+1)//2
    rows = max(1,mid)
    halfheight = max(5.08, (rows+1)*1.27)
    positions = {}
    body = []
    for idx,(num,(name,electrical)) in enumerate(pins.items()):
        left = idx < mid
        row = idx if left else idx-mid
        x = -20.32 if left else 20.32
        y = 2.54*((rows-1)//2-row)
        positions[num] = (x,y)
        body.append(f'(pin {electrical} line(at {x} {y} {0 if left else 180})(length 5.08)'
                    f'(name {quote(name)} {effect(.8)})(number {quote(num)} {effect(.8)}))')
    sid = LIB+':'+kind if embedded else kind
    properties = f'(property "Reference" "U" (at 0 {halfheight+3} 0){effect()})'
    properties += f'(property "Value" {quote(kind)}(at 0 {-halfheight-3} 0){effect()})'
    if kind in ('R','C'):
        if kind == 'R':
            center = '(rectangle(start -3.81 1.27)(end 3.81 -1.27)(stroke(width .254)(type default))(fill(type none)))'
            edge = 3.81
        else:
            edge = 1.27
            center = ''.join(f'(polyline(pts(xy {p} -2.54)(xy {p} 2.54))(stroke(width .254)(type default))(fill(type none)))' for p in (-edge,edge))
        center += ''.join(f'(polyline(pts(xy {a} 0)(xy {b} 0))(stroke(width .254)(type default))(fill(type none)))' for a,b in ((-15.24,-edge),(edge,15.24)))
    else:
        center = f'(rectangle(start -15.24 {halfheight})(end 15.24 {-halfheight})(stroke(width .254)(type default))(fill(type background)))'
    definition = (f'(symbol {quote(sid)} (pin_names(offset .8))(exclude_from_sim no)(in_bom yes)(on_board yes)'
                  f'{properties}(symbol {quote(kind+"_0_1")}{center})'
                  f'(symbol {quote(kind+"_1_1")}{"".join(body)}))')
    return definition, positions, halfheight

def label_text(value,x,y,size=1.1):
    return f'(text {quote(value)}(at {x} {y} 0){effect(size,"(justify left)")}(uuid "{uid(value+str(x)+str(y))}"))'

def title(name, identity, library=''):
    return (f'(kicad_sch(version 20250114)(generator "eeschema")(uuid "{identity}")(paper "A3")'
            f'(title_block(title "{PROJECT} - {name}")(rev "R6 P1 - HOLD")(comment 1 "Engineering candidate"))'
            f'(lib_symbols {library})')

def place(part,x,y,sheet_path):
    ref = part['ref']
    kind = part['kind']
    _,positions,height = symbol(kind,True)
    flag = kind == 'FLAG'
    instance = (f'(symbol(lib_id "{LIB}:{kind}")(at {x} {y} 0)(unit 1)(exclude_from_sim no)'
                f'(in_bom {"no" if flag else "yes"})(on_board {"no" if flag else "yes"})'
                f'(dnp {"yes" if part["status"]=="HOLD_DNP" else "no"})(uuid "{uid(ref)}")')
    for key, value, dy, visible in (
            ('Reference',ref,-height-5,True),('Value',part['value'],-height-2,True),
            ('Footprint',part['footprint'],0,False),('Datasheet',part['source'],0,False),
            ('MPN',part['mpn'],0,False),('Status',part['status'],0,False)):
        instance += f'(property "{key}" {quote(value)}(at {x} {y+dy:.4f} 0){effect(.9, "" if visible else "(hide yes)")})'
    for n in positions:
        instance += f'(pin "{n}" (uuid "{uid(ref+"/"+n)}"))'
    instance += f'(instances(project "{PROJECT}"(path "{sheet_path}"(reference "{ref}")(unit 1)))))'
    wires = [instance]
    for n,net in part['pins'].items():
        xx,yy = positions[n]
        px,py = round(x+xx,4),round(y-yy,4)
        marker = uid(ref+'-marker-'+n)
        if net is None:
            wires.append(f'(no_connect(at {px} {py})(uuid "{marker}"))')
            continue
        lx = round(px+(2.54 if xx>0 else -2.54),4)
        angle = 0 if xx>0 else 180
        wires.append(f'(wire(pts(xy {px} {py})(xy {lx} {py}))(stroke(width 0)(type default))(uuid "{marker}"))')
        wires.append(f'(global_label "{net}" (shape bidirectional)(at {lx} {py} {angle})'
                     f'{effect(.85,"(justify left)")}(uuid "{uid(ref+"-label-"+n)}")'
                     f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}"(at {lx} {py} 0){effect(.8,"(hide yes)")}))')
    return wires

def write_library():
    write('NXT_M3.kicad_sym','\n'.join(['(kicad_symbol_lib(version 20250114)(generator "kicad_symbol_editor")',
          *(symbol(kind)[0] for kind in sorted(types)),')']))
    write('sym-lib-table','(sym_lib_table\n(version 7)\n(lib (name "NXT_M3")(type "KiCad")'
          '(uri "${KIPRJMOD}/NXT_M3.kicad_sym")(options "")(descr "Candidate pin definitions")))')
    write('fp-lib-table','(fp_lib_table\n(version 7)\n(lib (name "NXT_M3")(type "KiCad")'
          '(uri "${KIPRJMOD}/NXT_M3.pretty")(options "")(descr "Candidate module footprints")))')
    (HERE/'NXT_M3.pretty').mkdir(exist_ok=True)
    pads = []
    for number, x in ((1,0),(2,2.54),(4,7.62),(6,12.70)):
        shape = 'rect' if number == 1 else 'circle'
        pads.append(f'(pad "{number}" thru_hole {shape}(at {x} 0)(size 1.7 1.7)(drill .9)(layers "*.Cu" "*.Mask"))')
    write('NXT_M3.pretty/TRACO_TMR1_SIP6_SINGLE.kicad_mod',
          '(footprint "TRACO_TMR1_SIP6_SINGLE"(version 20241229)(generator pcbnew)(layer "F.Cu")(attr through_hole)'
          '(fp_rect(start -2.15 -2.5)(end 14.85 5.12)(stroke(width .1)(type solid))(fill none)(layer "F.Fab"))'
          '(fp_rect(start -2.65 -3)(end 15.35 5.62)(stroke(width .05)(type solid))(fill none)(layer "F.CrtYd"))'
          '(fp_text reference "REF**"(at 6 -3.7)(layer "F.SilkS")(effects(font(size 1 1)(thickness .15))))'
          '(fp_text value "TRACO_TMR1_SIP6_SINGLE"(at 6 6.5)(layer "F.Fab")(effects(font(size 1 1)(thickness .15))))'
          +''.join(pads)+')')

def build():
    write_library()
    groups = defaultdict(list)
    for part in parts:
        groups[part['group']].append(part)
    root_id = uid('root')
    root = [title('Overview',root_id),label_text('NXT-M3    Autonomous 3-digit display',18,15,2.0),
            label_text('12V input  |  Local HV170  |  Local MCU + HV5622  |  RS-485',18,23),
            label_text('HOLD: J4 open; socket and insulation geometry pending. See project qualification.',18,30)]
    pages = []
    for group,group_parts in groups.items():
        large = [p for p in group_parts if len(p['pins'])>25]
        small = [p for p in group_parts if p not in large]
        for index in range(0,len(small),12):
            pages.append((f'{group}_{1+index//12}', small[index:index+12]))
        for part in large:
            pages.append((f'{group}_{part["ref"]}', [part]))
    for idx,(name,components) in enumerate(pages):
        sid = uid('sheet-'+name)
        x,y = 20+130*(idx%3),47+40*(idx//3)
        root.append(f'(sheet(at {x} {y})(size 109 28)(stroke(width .254)(type default))(fill(color 0 0 0 0))'
                    f'(uuid "{sid}")(property "Sheetname" "{name}"(at {x} {y-1} 0){effect(1.2,"(justify left)")})'
                    f'(property "Sheetfile" "{name}.kicad_sch"(at {x} {y+29} 0){effect(.9,"(justify left)")})'
                    f'(instances(project "{PROJECT}"(path "/{root_id}"(page "{idx+2}")))))')
        used = sorted({p['kind'] for p in components})
        page = [title(name,uid('file-'+name),''.join(symbol(kind,True)[0] for kind in used)),
                label_text(PROJECT+'    '+name,15,15,1.7)]
        for i,p in enumerate(components):
            px,py = (160.02,91.44) if len(p['pins'])>25 else (60.96+127*(i%3),48.26+60.96*(i//3))
            page.extend(place(p,px,py,'/'+root_id+'/'+sid))
        write(name+'.kicad_sch','\n'.join(page+[')']))
    write(PROJECT+'.kicad_sch','\n'.join(root+['(sheet_instances(path "/"(page "1")))',' )']))
    write(PROJECT+'.kicad_pro',json.dumps(dict(meta=dict(filename=PROJECT+'.kicad_pro',version=1),
        erc=dict(erc_exclusions=[],meta=dict(version=0)), schematic=dict(meta=dict(version=1)),
        text_variables=dict(QUALIFICATION='HOLD')),indent=2))

if __name__ == '__main__':
    build()
