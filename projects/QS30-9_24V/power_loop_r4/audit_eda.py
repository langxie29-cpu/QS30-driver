"""Real KiCad load/export/ERC and independent XML-versus-source pin comparison."""
from r4lib import *
import subprocess,os,shutil,uuid,xml.etree.ElementTree as ET,collections
def main():
 project=HERE/'EVT01';stamp=utc().replace(':','').replace('-','')[:15]+'_'+uuid.uuid4().hex[:6];out=HERE/'evidence/eda_runs'/stamp;out.mkdir(parents=True,exist_ok=False);snapshot=out/'snapshot';snapshot.mkdir()
 for p in project.iterdir():
  if p.is_file()and(p.suffix in ['.kicad_sch','.kicad_pro','.kicad_sym','.json','.csv']or p.name in ['sym-lib-table','fp-lib-table']):shutil.copy2(p,snapshot/p.name)
 env=dict(os.environ);env['KICAD10_FOOTPRINT_DIR']='C:/Program Files/KiCad/10.0/share/kicad/footprints';env['KICAD10_SYMBOL_DIR']='C:/Program Files/KiCad/10.0/share/kicad/symbols'
 sch=project/'NXT-PWR-EVT01.kicad_sch';commands=[('netlist',[str(KC),'sch','export','netlist','--format','kicadxml','-o',str(out/'native.net'),str(sch)]),('ERC',[str(KC),'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(out/'erc.json'),str(sch)]),('SVG',[str(KC),'sch','export','svg','-o',str(out/'svg'),str(sch)])]
 rows=[]
 for name,args in commands:
  r=subprocess.run(args,cwd=project,capture_output=True,env=env,timeout=180);(out/(name+'_stdout.bin')).write_bytes(r.stdout);(out/(name+'_stderr.bin')).write_bytes(r.stderr);rows.append(dict(name=name,argv=args,rc=r.returncode))
 comparison=None
 if(out/'native.net').exists():
  x=ET.parse(out/'native.net');observed={}
  for net in x.findall('.//nets/net'):
   for node in net.findall('node'):observed[(node.get('ref'),node.get('pin'))]=net.get('name')
  src=json.loads((project/'design_source.json').read_text(encoding='utf8'));expected={(p['ref'],k):v for p in src['parts']for k,v in p['pins'].items()if v is not None}
  differences=[dict(ref=k[0],pin=k[1],expected=v,actual=observed.get(k))for k,v in expected.items()if observed.get(k)!=v]
  unexpected=[dict(ref=k[0],pin=k[1],net=v)for k,v in observed.items()if k not in expected and not v.startswith('unconnected-')]
  comparison=dict(status='PASS'if not differences and not unexpected else'FAIL',expected_connected_pins=len(expected),exported_connected_pins=len(observed),differences=differences,unexpected=unexpected)
  dump(out/'pin_net_comparison.json',comparison)
 erc_summary={}
 if(out/'erc.json').exists():
  erc=json.loads((out/'erc.json').read_text(encoding='utf8'));violations=[v for s in erc.get('sheets',[])for v in s.get('violations',[])];erc_summary=dict(violations=len(violations),severity_counts=dict(collections.Counter(v.get('severity')for v in violations)),type_counts=dict(collections.Counter(v.get('type')for v in violations)))
 receipt=dict(utc=utc(),KiCad='10.0.8',commands=rows,pin_comparison=comparison,ERC=erc_summary,PCB_present=False,DRC_performed=False,manufacturing='HOLD',snapshot_sha256={p.name:sha(p)for p in snapshot.iterdir()})
 dump(out/'receipt.json',receipt);dump(HERE/'EVT01/latest_review.json',dict(run=str(out.relative_to(HERE)),**receipt));print(json.dumps(dict(run=str(out),commands=[dict(name=x['name'],rc=x['rc'])for x in rows],pin_comparison=comparison,ERC=erc_summary)))
if __name__=='__main__':main()
