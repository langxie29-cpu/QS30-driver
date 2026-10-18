"""Trace every native ERC/DRC item, cluster roots, and audit safety edits.

Does not modify or filter the native reports. Outputs only new A9.2 review data.
"""
import collections
import csv
import json
from pathlib import Path
import re
from kiutils.schematic import Schematic
from reconcile9 import xml_nets

ROOT=Path(__file__).resolve().parents[1]
LOG=ROOT/'kicad/logs'
ROOTS={
 'power_pin_not_driven':('A92-ERC-SUPPLY','P1','供电源未声明；逐网追溯后声明边界，不证明电源工作'),
 'shorting_items':('A92-DRC-01','P0','不同网络占位焊盘重叠；PCB文件真实铜短接，真实封装几何未验证'),
 'clearance':('A92-DRC-01','P0','占位焊盘行距忽略高度；默认间距不是高压批准间距'),
 'copper_edge_clearance':('A92-DRC-02','P1','过高占位焊盘越过板边净空'),
 'solder_mask_bridge':('A92-DRC-01','P1','占位焊盘碰撞导致阻焊桥；未验证真实阻焊尺寸'),
 'unconnected_items':('A92-DRC-03','P1','未布线PCB；非原理图显式NC'),
 'net_conflict':('A92-DRC-04','P2','原理图显式NC自动命名，PCB对应pad无net；逐脚保留隔离'),
 'lib_footprint_issues':('A92-DRC-05','P1','占位封装库/安装孔库未配置；不能据此证明机械尺寸'),
 'footprint_link_issues':('A92-ERC-LIB-FP','P1','原理图引用占位QS30封装库未配置'),
 'lib_symbol_issues':('A92-ERC-LIB-SYM','P2','嵌入符号可加载，QS30外部符号库未配置')}


def items(obj):
    if isinstance(obj,dict):
        if 'severity' in obj and 'type' in obj: yield obj
        else:
            for value in obj.values():yield from items(value)
    elif isinstance(obj,list):
        for value in obj:yield from items(value)


def main():
    out=ROOT/'docs9/a9_2_evidence';out.mkdir(exist_ok=True)
    all_rows=[];clusters={};native_snapshots={};erc_errors=[]
    for run in ('a9_2_before','a9_2_final'):
        native_snapshots[run]={}
        for board in ('QS30-9_DISPLAY','QS30-9_MAIN'):
            nodes,_,refs=xml_nets(LOG/run/f'{board}.xml')
            native_snapshots[run][board]={r:{p:n for (rr,p),n in nodes.items() if rr==r}
                                                     for r in sorted(set(refs.values()))}
            for kind in ('erc','drc'):
                path=LOG/run/f'{board}.{kind}.json';data=json.loads(path.read_text(encoding='utf8'))
                parsed=list(items(data));count=collections.Counter()
                refcounts=collections.defaultdict(collections.Counter)
                for i,item in enumerate(parsed,1):
                    root,severity,reason=ROOTS[item['type']]
                    descriptions=' | '.join(v.get('description','') for v in item.get('items',[]))
                    # Native JSON item descriptions may be Chinese or English.
                    mentions={r for r in re.findall(r'\b[A-Za-z]+\d+\b',descriptions) if r in refs}
                    designrefs=sorted(refs.get(r,r) for r in mentions)
                    nets=sorted(set(re.findall(r'\[([^\]]+)\]',descriptions)))
                    count[item['type']]+=1
                    refcounts[item['type']].update(designrefs)
                    row=dict(id=f'A92-{run}-{board.split("_")[-1]}-{kind.upper()}-{i:04d}',
                             run=run,board=board,kind=kind,rule=item['type'],severity=item['severity'],
                             root=root,priority=severity,refs=';'.join(designrefs),nets=';'.join(nets),
                             evidence=str(path.relative_to(ROOT))+f' item {i}',
                             native_description=item['description'],items=descriptions,root_cause=reason)
                    all_rows.append(row)
                    if run=='a9_2_before' and kind=='erc' and item['severity']=='error':
                        ref=next(iter(mentions));pin=re.search(r'(?:Pin |引脚 |���� )(\d+)',descriptions)
                        if not pin:pin=re.search(r' (\d+) \[',descriptions)
                        design=refs[ref]
                        erc_errors.append(dict(id=f'A92-ERC-{len(erc_errors)+1:02d}',board=board,
                                               ref=ref,design_ref=design,pin=pin[1],net=nodes[(design,pin[1])],
                                               rule=item['type'],native_item=row['id']))
                clusters[f'{run}/{board}/{kind}']=dict(counts=dict(count),
                       components={k:dict(v.most_common()) for k,v in refcounts.items()},
                       inherited_ignored_checks=data.get('ignored_checks',[]))
    with (out/'all_native_items.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    (out/'clusters.json').write_text(json.dumps(clusters,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'erc_seven.json').write_text(json.dumps(erc_errors,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'native_connections.json').write_text(json.dumps(native_snapshots,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    nodes,_,_=xml_nets(LOG/'a9_2_final/QS30-9_MAIN.xml')
    checks=[]
    def check(cid,ok,description):checks.append(dict(id=cid,status='PASS' if ok else 'FAIL',evidence=description))
    check('A92-T01',nodes['U23','2']=='OVP_SNS' and nodes['U23','3']=='VREF_OVP','OVP IN- senses bus; IN+ references TL431; rising HV pulls SET low')
    check('A92-T02',not any(r=='R39' for r,p in nodes),'R39 hazardous direct logic/gate link absent from native XML')
    check('A92-T03',nodes['U20','8']=='VREF_UC' and nodes['U21','1']==nodes['U21','2']=='VREF_AUX_2V5','UC internal 5 V no longer shares 2.5 V TL431 shunt')
    check('A92-T04',nodes['D4','1']=='GND' and nodes['D4','2']=='3V3' and nodes['D4','3']=='HVF_NODE','BAT54S middle junction is pad 3, upper rail cathode pad 2')
    check('A92-T05',all(nodes[r,'1']==n and nodes[r,'2']=='GND' for r,n in [('R_Q5_BE','Q5_B'),('R_Q3_BE','Q3_B'),('R_HV_REQ_PD','HV_EN_REQ')]),'three explicit default-off 100k pull-downs')
    check('A92-T06',nodes['Q20','3']=='GND' and nodes['R36','1']=='SW_HV','UNRESOLVED: wrong CS topology retained and explicitly FAIL for protection')
    checks[-1]['status']='FAIL' if checks[-1]['status']=='PASS' else 'REVIEW'
    (out/'safety_topology_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    positions={}
    for board in ('QS30-9_DISPLAY','QS30-9_MAIN'):
        s=Schematic.from_file(str(ROOT/f'kicad/projects/{board}/{board}.kicad_sch'),encoding='utf8')
        positions[board]={}
        for symbol in s.schematicSymbols:
            props={p.key:p.value for p in symbol.properties}
            positions[board][props['DesignRef']]=dict(kicad_ref=props['Reference'],x_mm=symbol.position.X,y_mm=symbol.position.Y)
    (out/'schematic_coordinates.json').write_text(json.dumps(positions,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(items=len(all_rows),erc_errors=erc_errors,checks=checks),ensure_ascii=True))


if __name__=='__main__':main()
