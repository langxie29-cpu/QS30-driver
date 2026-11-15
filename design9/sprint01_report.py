"""Reproduce Sprint01 classifications and verify surgical PCB changes."""
import collections,csv,gzip,hashlib,json,re,subprocess,tempfile
from pathlib import Path
from kiutils.board import Board
from reconcile9 import xml_nets
from kicad_gen import gen_pcb,parts_of,load
from build9 import build,erc
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs9/electrical_sprint01';OUT.mkdir(exist_ok=True)
def write(name,data):
    p=OUT/name
    if p.exists() and name!='manifest.json':
        assert json.loads(p.read_text(encoding='utf-8'))==json.loads(json.dumps(data)), p
        return
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def items(o):
    if isinstance(o,dict):
        if 'severity' in o and 'type' in o:yield o
        else:
            for v in o.values():yield from items(v)
    elif isinstance(o,list):
        for v in o:yield from items(v)
def main():
    hvnets={r['net'] for r in csv.DictReader((ROOT/'netlist9/QS30-9_REV.A_netlist.csv').open(encoding='utf-8-sig')) if r['net_class']=='HV'}
    mapping={'clearance':'Clearance','shorting_items':'Short circuit','unconnected_items':'Unconnected','lib_footprint_issues':'Pad / Footprint','net_conflict':'Schematic parity'}
    categories=['Clearance','Short circuit','Unconnected','Via / Track','Pad / Footprint','Courtyard','Silkscreen','Board outline','Schematic parity','Other']
    summaries={};index=[]
    for phase,run in [('before','sprint01_before'),('after','sprint01_verified')]:
        reports={};counts=collections.Counter();cats=collections.Counter({k:0 for k in categories});sevs=collections.Counter();hv=collections.Counter()
        for board in ['QS30-9_DISPLAY','QS30-9_MAIN']:
            data=json.loads((ROOT/'kicad/logs'/run/f'{board}.drc.json').read_text(encoding='utf-8'));reports[board]=data
            for n,item in enumerate(items(data),1):
                rule=item['type'];counts[rule]+=1;cats[mapping.get(rule,'Other')]+=1;sevs[item['severity']]+=1
                nets=set(re.findall(r'\[([^\]]+)\]',str(item))) & hvnets
                if nets:hv[rule]+=1
                index.append({'phase':phase,'board':board,'item':n,'type':rule,'severity':item['severity'],'category':mapping.get(rule,'Other'),'hv_nets':';'.join(sorted(nets)),'description':item['description'],'objects':json.dumps(item.get('items',[]),ensure_ascii=False)})
        write(f'drc-{phase}.json',{'note':'Board-keyed original native JSON, including all report arrays; native originals in kicad/logs/'+run,'boards':reports})
        summaries[phase]={'types':dict(counts),'categories':dict(cats),'severity':dict(sevs),'hv_tagged_items':dict(hv),'top_five_nonzero':counts.most_common(5)}
    write('erc-after.json',{'boards':{b:json.loads((ROOT/'kicad/logs/sprint01_verified'/f'{b}.erc.json').read_text(encoding='utf-8')) for b in reports}})
    write('drc-summary.json',summaries)
    with (OUT/'drc-items.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(index[0]));w.writeheader();w.writerows(index)
    checks={}
    for board,prefixes,w,h in [('QS30-9_DISPLAY',('MOD_L',),100,100),('QS30-9_MAIN',('MB_','MOD_C'),120,90)]:
        path=ROOT/'kicad/projects'/board/f'{board}.kicad_pcb'
        old=subprocess.check_output(['git','show','9682439:'+str(path.relative_to(ROOT)).replace('\\','/')])
        new=path.read_bytes();normal=new.decode().replace('\r\n','\n')
        after,_,_=xml_nets(ROOT/'kicad/logs/sprint01_verified'/f'{board}.xml');before,_,_=xml_nets(ROOT/'kicad/logs/sprint01_before'/f'{board}.xml')
        # Remove only exact known singleton NC assignments and definitions.
        for n in {n for n in after.values() if n.startswith('unconnected-')}:
            normal=re.sub(r'^  \(net \d+ "'+re.escape(n)+r'"\)\n','',normal,flags=re.M)
            normal=re.sub(r' \(net \d+ "'+re.escape(n)+r'"\)','',normal)
        generated,_,_=gen_pcb(board,parts_of(load(),prefixes),w,h)
        with tempfile.TemporaryDirectory() as td:
            tmp=Path(td)/'generated.kicad_pcb';tmp.write_text(generated,encoding='utf-8')
            a=Board.from_file(str(tmp),encoding='utf-8');b=Board.from_file(str(path),encoding='utf-8')
            def pads(board):return {(fp.properties.get('DesignRef',fp.properties.get('Reference')),p.number):(p.net.name if p.net else '',p.position.X,p.position.Y,p.size.X,p.size.Y) for fp in board.footprints for p in fp.pads}
            generated_matches=pads(a)==pads(b)
        checks[board]={'native_members_identical':before==after,'geometry_active_nets_identical_to_HEAD':normal==old.decode().replace('\r\n','\n'),'generator_pad_nets_geometry_match':generated_matches}
        assert all(checks[board].values()),checks[board]
    model=build();structural=erc(model,model.nets());checks['structural_erc']=structural
    write('checks.json',checks)
    # Preserve raw text byte-for-byte compressed; do not remove originals.
    folders=[ROOT/'sim/a9_2'/r for r in ['sprint01_actual','sprint01_measurements','sprint01_measurements_v2']]
    for folder in folders:
        for p in folder.rglob('waves.txt'):
            if Path(str(p)+'.gz').exists():continue
            with gzip.open(str(p)+'.gz','wb') as f:f.write(p.read_bytes())
    paths=[p for r in ['sprint01_actual','sprint01_measurements','sprint01_measurements_v2'] for p in (ROOT/'sim/a9_2'/r).rglob('*') if p.is_file() and p.name!='waves.txt']
    paths += [ROOT/'design9'/p for p in ['electrical_sprint01.py','sprint01_sim.py','sprint01_report.py','safety_sim9.py','reconcile9.py','kicad_gen.py']]
    write('manifest.json',{'branch':'nxt/reva9-electrical-sprint01','base_commit':'9682439fe35636ed2c2928bc50d30858133e4c8a','tool_versions':{'KiCad':'10.0.8','ngspice':'47','numpy':'2.5.4','matplotlib':'3.11.2'},'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
    print(json.dumps(summaries,indent=2));print(json.dumps(checks,ensure_ascii=True))
if __name__=='__main__':main()
