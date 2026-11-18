"""Delivery scope, physical-net invariants and generated-file hashes; no solver calls."""
from r4lib import *
import subprocess,ast,csv,re
def main():
 required=['ENGINEERING_REPORT.md','ARCHITECTURE_DECISION_RECORD.md','FRONTEND_ARCHITECTURE_COMPARISON.md','FAULT_ENERGY_BUDGET.csv','COMPONENT_SELECTION_DECISIONS.csv','COMPONENT_DERATING_MATRIX.csv','BOM_CHANGE_IMPACT.md','SAFETY_CIRCUIT_IMPLEMENTATION.md','EVT01/NXT-PWR-EVT01.kicad_pro','EVT01/NXT-PWR-EVT01.kicad_sch','EVT01_BOM_REVIEW.csv','EVT01_COST_SCENARIOS.md','QUALIFICATION_MATRIX.json','REPRODUCE.md','NEXT_ENGINEERING_DECISIONS.md']
 assert all((HERE/p).is_file()and(HERE/p).stat().st_size>0 for p in required)
 d=json.loads((HERE/'EVT01/design_source.json').read_text());parts={p['ref']:p for p in d['parts']};tests={}
 def check(name,ok):tests[name]=bool(ok);assert ok,name
 check('U100_RTN_EP_floating_reference',parts['U100']['pins']['15']==parts['U100']['pins']['25']=='RTN100'and parts['U100']['pins']['17']=='PGND')
 check('U100_MODE_open_IMON_unused',parts['U100']['pins']['13']is None and parts['U100']['pins']['18']is None)
 check('Real12V_to_VIN_and_driver_not_INTVCC',parts['U20']['pins']['10']==parts['U201']['pins']['1']=='V12'and parts['U20']['pins']['8']=='INTVCC')
 check('Q101_not_fitted_not_selected',parts['Q101']['status']=='HOLD_DNP_UNSELECTED'and parts['Q101']['mpn'].startswith('UNKNOWN'))
 check('R111_unselected',parts['R111']['value']=='HOLD_CURRENT_SETTING')
 check('No_fitted_capacitor_at_L_FEED',not any(p['kind']=='C'and'L_FEED'in p['pins'].values()for p in d['parts']))
 for net in ['HOLD_FULL_SAFETY_VALID','HOLD_RESIDUAL_VALID','HOLD_PRECHARGE_OK','HOLD_INPUT_CUT_VALID']:
  check(net+'_physical_pulldown',any(p['kind']=='R'and p['value']=='10k'and set(p['pins'].values())=={net,'GND_CTRL'}for p in d['parts']))
 check('D20_SiC_pin_assignment',parts['D20']['mpn']=='STPSC4H065D'and parts['D20']['pins']=={'1':'HV_BUS','2':'SW_HV'})
 check('U520_independent12V_supply',parts['U520']['pins']['5']=='V12'and parts['U520']['pins']['2']=='PGND')
 erc=json.loads((HERE/'EVT01/latest_review.json').read_text());check('Native_pin_connectivity_matches',erc['pin_comparison']['status']=='PASS')
 check('ERC_warnings_not_waived',erc['ERC']['severity_counts'].get('error',0)==0 and erc['ERC']['violations']>0)
 check('No_PCB_no_DRC',not list((HERE/'EVT01').glob('*.kicad_pcb'))and erc['DRC_performed']is False)
 q=json.loads((HERE/'QUALIFICATION_MATRIX.json').read_text());check('All_original_holds_unchanged',all(v=='UNCHANGED_HOLD'for v in q['holds'].values()))
 for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
 rel=HERE.relative_to(ROOT).as_posix();paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',rel],cwd=ROOT,text=True).splitlines();paths=sorted(set(paths));forbidden=[];secret=[]
 for name in paths:
  p=ROOT/name
  if p.suffix.lower()in['.raw','.lib','.sub','.pdf','.exe','.zip']:forbidden.append(name)
  if p.is_file()and re.search(rb'sk-[A-Za-z0-9]{24,}',p.read_bytes()):secret.append(name)
 check('No_vendor_models_PDF_executable_or_raw_in_git',not forbidden)
 check('No_detected_provider_key_pattern',not secret)
 dump(HERE/'evidence/delivery_audit.json',dict(utc=utc(),invariants=tests,required_files=required,python_AST='PASS',file_scope='R4only; excludes ignored .local/raw/vendor files',forbidden_files=forbidden,key_pattern_findings=secret,scope='Software and artifact consistency only; no physical safety qualification'))
 # Include the just-written audit; exclude the manifest itself to avoid self-reference.
 paths=sorted(set(paths+[str((HERE/'evidence/delivery_audit.json').relative_to(ROOT)).replace('\\','/')]))
 with(HERE/'evidence/DELIVERY_SHA256.csv').open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
  for name in paths:
   p=ROOT/name
   if p.name=='DELIVERY_SHA256.csv'or not p.is_file():continue
   w.writerow(dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
 print(json.dumps(dict(invariants=len(tests),source_files=len(paths),required_files=len(required),status='SOFTWARE_CONSISTENCY_PASS',electrical='HOLD')))
if __name__=='__main__':main()
