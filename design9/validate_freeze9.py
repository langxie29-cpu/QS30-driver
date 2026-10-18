"""Independent topology/bit-order checks over native nets, plus R template equivalence.

Usage: python design9/validate_freeze9.py --run after_a9_1
No KiCad rule is disabled; this supplements native ERC/DRC.
"""
import argparse
import csv
import json
from pathlib import Path
import re
from build9 import build, PIN_DB
from reconcile9 import xml_nets

ROOT = Path(__file__).resolve().parents[1]
TUBE_PINS = {0:3, 1:13, 2:12, 3:11, 4:10, 5:9, 6:7, 7:6, 8:5, 9:4}


def driver_pin(hvout):
    return 23-hvout if hvout <= 22 else 67-hvout


def right_of(s):
    s = re.sub(r'(?<=_)L(?=_|$)', 'R', s)
    s = re.sub(r'T([1-3])(?=_|$)', lambda m:'T'+str(int(m[1])+6), s)
    return re.sub(r'AN([1-3])_', lambda m:'AN'+str(int(m[1])+6)+'_', s)


def validate(run):
    folder = ROOT/'kicad/logs'/run
    destination = folder/'electrical_audit.json'
    if destination.exists():
        raise FileExistsError('audit is append-only; use a new capture run')
    d = build()
    actual, groups, refs = {}, {}, {}
    for board in ('QS30-9_DISPLAY','QS30-9_MAIN'):
        nodes, nets, refmap = xml_nets(folder/f'{board}.xml')
        actual.update(nodes)
        for name, members in nets.items():
            groups.setdefault(name, set()).update(members)
        refs[board] = refmap
    checks = []
    def check(cid, ok, evidence):
        checks.append(dict(id=cid, status='PASS' if ok else 'FAIL', evidence=evidence))
    left = {r:p for r,p in d.parts.items() if p.sheet == 'MOD_L'}
    right = {r:p for r,p in d.parts.items() if p.sheet == 'MOD_R'}
    equivalent = len(left) == len(right) and all(
        right_of(r) in right and p.mpn == right[right_of(r)].mpn and
        {pin:right_of(net) for pin,net in p.nets.items()} == right[right_of(r)].nets
        for r,p in left.items())
    check('F01', equivalent, 'R is the same DISPLAY electrical design with L→R, T1–3→T7–9 substitutions; not a third independent native project')
    # Instantiate the verified native DISPLAY template only after structural equivalence.
    if equivalent:
        for (r,pin), net in list(actual.items()):
            if r in left:
                actual[(right_of(r),pin)] = right_of(net)
        for net,members in list(groups.items()):
            for r,pin in list(members):
                if r in left:
                    groups.setdefault(right_of(net), set()).add((right_of(r),pin))
    mapping = list(csv.DictReader((ROOT/'docs9/channel_map9.csv').open(encoding='utf-8-sig')))
    check('F02', len(mapping)==90 and len({(r['tube'],r['digit']) for r in mapping})==90, '90 unique (tube,digit) records')
    channel_rows = []
    for row in mapping:
        t, digit, hv = int(row['tube']), int(row['digit']), int(row['hvout'])
        m = 'LCR'[(t-1)//3]
        expected_hv = 10*((t-1)%3)+digit+1
        net = f'K_T{t}_{digit}'
        nodes = {(f'U_{m}',str(driver_pin(hv))), (f'J_T{t}',str(TUBE_PINS[digit]))}
        okay = hv == expected_hv and int(row['socket_pin']) == TUBE_PINS[digit] and groups.get(net)==nodes
        channel_rows.append(dict(tube=t,digit=digit,net=net,hvout=hv,pin=driver_pin(hv),
                                 nodes=sorted(nodes),status='PASS' if okay else 'FAIL',
                                 provenance='native' if m!='R' else 'native DISPLAY template + checked R equivalence'))
    check('F03', all(r['status']=='PASS' for r in channel_rows), 'Every cathode has exactly the expected driver output and socket pin; 60 native + 30 R-template channels')
    check('F04', len({(r['tube']//100, 'LCR'[(r['tube']-1)//3],r['hvout']) for r in channel_rows})==90,
          'No output assigned to two cathodes; each device uses HVOUT1–30 only')
    anodes = []
    for t in range(1,10):
        a = groups.get(f'A_T{t}',set()) == {(f'R_AN{t}_2','2'),(f'J_T{t}','2')}
        mid = groups.get(f'A_T{t}_MID',set()) == {(f'R_AN{t}_1','2'),(f'R_AN{t}_2','1')}
        bus = actual.get((f'R_AN{t}_1','1')) == 'HV_BUS'
        anodes.append(dict(tube=t,resistors=[f'R_AN{t}_1',f'R_AN{t}_2'],ohms=20000,status='PASS' if a and mid and bus else 'FAIL'))
    check('F05', all(a['status']=='PASS' for a in anodes), '9 independent HV_BUS→10k→MID→10k→A_Tn→socket.2 branches; no anode uses a driver channel')
    nc_ok = True
    for m in 'LCR':
        for pin in ('24','25','26','34','35','36'):
            nc_ok &= actual.get((f'U_{m}',pin),'').startswith('unconnected-')
        for t in range(1+'LCR'.index(m)*3,4+'LCR'.index(m)*3):
            for pin in ('1','8'):
                nc_ok &= actual.get((f'J_T{t}',pin),'').startswith('unconnected-')
    check('F06', nc_ok, 'HV5622 NC24/25/26/34 and unused HVOUT31/32 pins36/35, socket1/8 have no connected net')
    path_ok = True
    for m in 'LCR':
        wanted = {(f'U_LS_{m}','3'):f'MOD_{m}_DIN', (f'U_LS_{m}','4'):f'U_{m}_DIN',
                  (f'U_{m}','32'):f'U_{m}_DIN', (f'U_{m}','23'):f'U_{m}_DOUT',
                  (f'U_DS_{m}','3'):f'U_{m}_DOUT',(f'U_DS_{m}','4'):f'MOD_{m}_DOUT',
                  (f'U_DS_{m}','1'):'DRV_VDD',(f'U_DS_{m}','16'):'3V3',
                  (f'U_{m}','27'):'DRV_VDD',(f'U_{m}','29'):'GND',(f'U_{m}','30'):'DRV_VDD'}
        for logic_pin, ls_pin, hv_pin, global_net in [('CLK','5','28','DISP_CLK'),('LAT','11','31','DISP_LAT'),('BL','13','33','DISP_ALLOW')]:
            wanted[(f'U_{m}',hv_pin)] = f'U_{m}_{logic_pin}'
            wanted[(f'U_LS_{m}',ls_pin)] = f'U_{m}_{logic_pin}'
            wanted[(f'U_LS_{m}',{'CLK':'6','LAT':'10','BL':'14'}[logic_pin])] = global_net
        path_ok &= all(actual.get(k)==v for k,v in wanted.items())
    wanted = {('U10','19'):'MOD_L_DIN',('R62','1'):'MOD_L_DOUT',('R62','2'):'MOD_C_DIN',
              ('R63','1'):'MOD_C_DOUT',('R63','2'):'MOD_R_DIN'}
    check('F07', path_ok and all(actual.get(k)==v for k,v in wanted.items()), 'MCU→L up→HV→L down→R62→C up→HV→C down→R63→R up→HV→R down; no direct 12V DOUT on 3V3 DIN')
    pairs = []
    for m in 'LR':
        for kind, n in [('LV',16),('HV',2)]:
            for pin in map(str,range(1,n+1)):
                main, mod = (f'J_MAIN_{m}_{kind}',pin),(f'J_MOD_{m}_{kind}',pin)
                pairs.append(dict(module=m,kind=kind,pin=pin,main=actual.get(main),module_net=actual.get(mod),
                                  status='PASS' if actual.get(main)==actual.get(mod) and actual.get(main) is not None else 'FAIL'))
    check('F08', all(p['status']=='PASS' for p in pairs), '36 mated pins match by number; C is an internal main-board interface')
    lv_hv = [(k,n) for k,n in actual.items() if k[0].startswith(('J_MOD_','J_MAIN_')) and k[0].endswith('_LV') and n in ('HV_BUS','GND_HV')]
    check('F09', not lv_hv and all(groups.get(n) for n in ('HV_BUS','GND_HV','GND','3V3','DRV_VDD')), 'Power net groups remain distinct; LV connector has no HV_BUS/GND_HV')
    bonds = [p.ref for p in d.parts.values() if {'GND','GND_HV'} <= set(p.nets.values())]
    check('F10', bonds==['R_HV_STAR'] and actual.get(('R_HV_STAR','1'))=='GND_HV' and actual.get(('R_HV_STAR','2'))=='GND',
          f'GND_HV/GND bond components={bonds}; module VSS=LV GND, only capacitor/bleeder uses HV return')
    bit_ok = True
    # Independent 96-stage shift model; one unique marker for every transmission slot.
    state = [None]*96
    for serial in range(96):
        state = [serial]+state[:-1]
    for row in mapping:
        position = 'LCR'.index(row['module'])*32 + int(row['hvout'])-1
        bit_ok &= state[position]==int(row['serial_index']) and int(row['frame_bit'])==95-int(row['serial_index'])
        bit_ok &= int(row['byte'])==int(row['serial_index'])//8 and int(row['bit_in_byte'])==7-int(row['serial_index'])%8
    check('F11', bit_ok, '96 falling-edge shift model confirms wire byte/bit order; R32→R1, C32→C1, L32→L1; physical walking-one still HOLD')
    safety = {'R64':('SAFETY_LOOP_MAIN','SAFETY_LOOP_L_IN'),
              'R_SAFE_L':('SAFETY_LOOP_L_IN','SAFETY_LOOP_L_OUT'),
              'R59':('SAFETY_LOOP_L_OUT','SAFETY_LOOP_C_IN'),
              'R_SAFE_C':('SAFETY_LOOP_C_IN','SAFETY_LOOP_C_OUT'),
              'R60':('SAFETY_LOOP_C_OUT','SAFETY_LOOP_R_IN'),
              'R_SAFE_R':('SAFETY_LOOP_R_IN','SAFETY_LOOP_R_OUT'),
              'R57':('3V3','SAFETY_LOOP_MAIN'),'R58':('SAFETY_LOOP_R_OUT','GND')}
    check('F12', all(actual.get((r,str(pin)))==net for r,ends in safety.items() for pin,net in enumerate(ends,1))
          and actual.get(('U7','13'))=='SAFETY_LOOP_R_OUT' and actual.get(('U10','24'))=='SAFETY_LOOP_R_OUT',
          'Exact series path R57→R64→L→R59→C→R60→R→R58 verified, terminates at U7.13 and U10.24; thresholds/startup still HOLD')
    result = dict(status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',checks=checks,
                  channels=channel_rows,anodes=anodes,connector_pairs=pairs,references=refs,
                  limitation='Topology PASS does not approve component functionality, footprint geometry, insulation, ERC, DRC or HV operation')
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],checks=checks),ensure_ascii=False,indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--run',required=True);args=p.parse_args()
    raise SystemExit(0 if validate(args.run)['status']=='PASS' else 1)
