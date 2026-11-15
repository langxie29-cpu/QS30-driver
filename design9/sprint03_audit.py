"""Read-only inputs; write only Sprint03 namespace. Run once before experiments."""
from pathlib import Path
import csv, hashlib, json, subprocess, urllib.request, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'sim/sprint03'; B.mkdir(exist_ok=True); S=B/'source'; S.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT).decode('utf8',errors='replace')
assert not (B/'baseline.json').exists(),'Refuse to overwrite baseline'
paths=git('ls-files','--cached','--others','--exclude-standard','-z').split('\0')
protected={p:sha(ROOT/p) for p in paths if p and (ROOT/p).is_file() and not p.startswith(('sim/sprint03/','docs9/electrical_sprint03/','design9/sprint03_'))}
dump(B/'baseline.json',dict(head=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),status=git('status','--short'),protected_sha256=protected,ancestor_AGENTS='None on workspace ancestry or inside repository',note='Inherited dirty files preserved; no commits'))
(B/'inherited-worktree.patch').write_text(git('diff','--binary'),encoding='utf8')
for p in ['sim/sprint02/source/uc3843_functional.lib','sim/sprint02/source/references.json']:(S/Path(p).name).write_bytes((ROOT/p).read_bytes())
docs=['README.md',*map(str,(ROOT/'docs9').glob('*.md')),'sim/README.md','sim/a9_2/MODEL_LIMITS.md','open_issues9.md','HOLD_REGISTER9.md']
dump(B/'document_inventory.json',[dict(path=str(Path(p)),bytes=len((ROOT/p).read_bytes()),sha256=sha(ROOT/p)) for p in docs if (ROOT/p).exists()])
downloads=[]
for name,url in [('TI_UC3843A.pdf','https://www.ti.com/lit/ds/symlink/uc3843a.pdf'),('TI_UC3843AN.html','https://www.ti.com/product/UC3843A/part-details/UC3843AN')]:
    try:
        with urllib.request.urlopen(url,timeout=25) as r:data=r.read()
        (S/name).write_bytes(data);downloads.append(dict(url=url,file=name,sha256=sha(S/name),status='OK'))
    except Exception as e:downloads.append(dict(url=url,status='FAILED',error=str(e)))
dump(S/'downloads.json',downloads)
exe='C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'; cmds=[]
for board in ['QS30-9_MAIN','QS30-9_DISPLAY']:
    out=B/(board+'.xml'); inp=ROOT/f'kicad/projects/{board}/{board}.kicad_sch'
    argv=[exe,'sch','export','netlist','--format','kicadxml','-o',str(out),str(inp)]
    p=subprocess.run(argv,capture_output=True);cmds.append(dict(argv=argv,rc=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace'),source_sha256=sha(inp)))
    assert p.returncode==0
dump(B/'native_export.json',cmds)
tree=ET.parse(B/'QS30-9_MAIN.xml'); mapping={}
for c in tree.findall('./components/comp'):
    mapping[c.attrib['ref']]=next(f.text for f in c.findall('./fields/field') if f.attrib.get('name')=='DesignRef')
nodes={}
for n in tree.findall('./nets/net'):
    for p in n.findall('node'):nodes[(mapping[p.attrib['ref']],p.attrib['pin'])]=n.attrib['name']
rows=list(csv.DictReader((ROOT/'netlist9/QS30-9_REV.A_netlist.csv').open(encoding='utf-8-sig')))
selected=[r for r in rows if r['sheet']=='MB_HV' or r['ref'].startswith('R_MOD_')]
for r in selected:
    if (r['ref'],r['pin']) in nodes:assert nodes[(r['ref'],r['pin'])]==r['net'],r
with (B/'native_hv_pins.csv').open('w',newline='',encoding='utf8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(selected)
dump(B/'native_topology.json',dict(pins_compared=len([r for r in selected if (r['ref'],r['pin']) in nodes]),csv_native_match=True,topology='Uncoupled single-inductor nonisolated boost',controller_mpn=[r['mpn'] for r in rows if r['ref']=='U20'][0],series_shunt_present=False,cs_pickoff='SW_HV through R36=100k; C13=470p to GND',ground='Q20.S=GND; R_HV_STAR connects GND_HV',native_components=[dict(designref=mapping[c.attrib['ref']],value=c.findtext('value'),footprint=c.findtext('footprint')) for c in tree.findall('./components/comp') if mapping[c.attrib['ref']] in ['U20','L20','Q20','D20','C10']]))
print('Frozen',len(protected),'files; exported and compared native HV pins',flush=True)
