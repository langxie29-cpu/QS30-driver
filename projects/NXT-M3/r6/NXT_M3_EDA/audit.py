"""Compare real KiCad XML with schematic intent and inspect actual footprint pad sets."""
import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from design import parts, types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVIDENCE = ROOT/'evidence'

def write(name, rows):
    with (ROOT/name).open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def check(footprints):
    legacy_path = ROOT.parents[2]/'design'/'model.py'
    legacy = ast.parse(legacy_path.read_text(encoding='utf-8'))
    db = next(stmt.value for stmt in legacy.body if isinstance(stmt, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'PIN_DB' for target in stmt.targets))
    pin_db = ast.literal_eval(db)
    driver_table = pin_db['HV5622-PQFP44']
    tubes = pin_db['QS30-1']

    tree = ET.parse(EVIDENCE/'native.xml')
    net_for = {}
    net_members = defaultdict(set)
    for net in tree.findall('./nets/net'):
        name = net.attrib['name']
        for endpoint in net.findall('./node'):
            key = (endpoint.attrib['ref'],endpoint.attrib['pin'])
            assert key not in net_for, key
            net_for[key] = name
            net_members[name].add(key)
    installed = {comp.attrib['ref']:comp for comp in tree.findall('./components/comp')}
    pin_rows, fp_rows, mismatch = [], [], []
    for part in parts:
        ref = part['ref']
        pin_dict = part['pins']
        fw = part['footprint']
        if not ref.startswith('#'):
            if ref not in installed or (installed[ref].findtext('footprint') or '') != fw:
                mismatch.append(ref+' footprint export')
        for number, expected in pin_dict.items():
            observed = net_for.get((ref,number))
            name, kind = types[part['kind']][number]
            if expected is None:
                match = observed is None or (observed.startswith('unconnected-') and len(net_members[observed])==1)
            else:
                match = expected == observed or (ref.startswith('#') and observed is None and expected in net_members)
            if not match:
                mismatch.append(f'{ref}:{number}')
            if ref=='U12':
                legacy_name = {'DATA OUT':'DOUT','DATA IN':'DIN'}.get(driver_table[number],driver_table[number])
                assert name == legacy_name
            if part['kind']=='QS30_1':
                legacy_name = {'A':'ANODE','IC_KEEP_OPEN':'IC1','IC8_KEEP_OPEN':'IC8'}.get(tubes[number],tubes[number])
                assert name == legacy_name
            pin_rows.append(dict(ref=ref,pin=number,function=name,type=kind,expected=expected or 'NC',
                                 kicad_export=observed or 'NONE',match=match,source=part['source'] or
                                 ('Legacy QS30-1 factory pin map' if part['kind']=='QS30_1' else 'R6 connection intent')))
        if ref.startswith('#'):
            continue
        path = None
        pads = set()
        if fw:
            lib, pkg = fw.split(':')
            path = (HERE if lib=='NXT_M3' else footprints)/(lib+'.pretty')/(pkg+'.kicad_mod')
            if path.is_file():
                pads = {p for p in re.findall(r'\(pad\s+"([^"]*)"',path.read_text(encoding='utf-8')) if p}
        state = 'HOLD_GEOMETRY'
        if not fw:
            state = 'HOLD_SOCKET_UNASSIGNED'
        elif path is None or not path.is_file():
            state = 'MISSING_FILE'
            mismatch.append(ref+' footprint file')
        elif pads != set(pin_dict):
            state = 'PAD_MISMATCH'
            mismatch.append(ref+' pad set')
        fp_rows.append(dict(ref=ref,mpn=part['mpn'],footprint=fw or 'NONE',
                            pins=' '.join(pin_dict),pads=' '.join(sorted(pads)),
                            state=state,sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                            if path is not None and path.is_file() else 'NONE'))

    # Unique tube nets must each join exactly one tube pin and one driver pin.
    k = {net: nodes for net,nodes in net_members.items() if re.match(r'^K[123]_\d$',net)}
    assert len(k)==30
    for net,nodes in k.items():
        assert {ref for ref,pin in nodes}=={'U12','V'+net[1]} and len(nodes)==2
    for digit in range(1,4):
        assert {ref for ref,pin in net_members['ANODE'+str(digit)]}=={'V'+str(digit),'R'+str(71+digit*2)}
    assert net_members['HV170'].isdisjoint({('J1','1'),('J1','2'),*((j,str(p)) for j in ('J2','J3') for p in range(1,4))})
    assert len(installed)==sum(not p['ref'].startswith('#') for p in parts)
    assert net_for.keys() <= {(row['ref'],row['pin']) for row in pin_rows}
    write('PIN_MAPPING.csv',pin_rows)
    write('FOOTPRINT_REVIEW.csv',fp_rows)
    counts = Counter()
    erc = json.loads((EVIDENCE/'erc.json').read_text(encoding='utf-8'))
    for sheet in erc['sheets']:
        for violation in sheet['violations']:
            counts[violation['severity']+'/'+violation['type']] += 1
    out = dict(components=len(installed), pin_slots=len(pin_rows), checks=Counter(p['match'] for p in pin_rows),
               cathodes=len(k), net_count=len(net_members), erc=counts, mismatch=mismatch,
               footprints=Counter(f['state'] for f in fp_rows), PCB=False, DRC=False)
    (EVIDENCE/'eda_audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out))
    return not mismatch

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--footprints',type=Path,
                        default=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints'))
    args = parser.parse_args()
    raise SystemExit(0 if check(args.footprints) else 1)
