"""Update S05 index/status and verify evidence, keeping legacy/baseline files read-only."""
from pathlib import Path
import csv,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def writecsv(p,rows):
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 p=ROOT/'config/project.json';c=json.loads(p.read_text(encoding='utf8'))
 c.update(revision='S05-REVIEW',lifecycle='DESIGN_BASELINE_AND_CANDIDATES_ONLY_07_NOT_QUALIFIED',manufacturing='HOLD',active_design_baseline='config/sprint05.json',sprint05_report='docs/SPRINT05_REPORT.md')
 for rail in c['rails']:
  if rail['name']=='VIN24':rail.update(status='DESIGN_REQUIREMENT_BASELINED',continuous_range_V=[21.6,26.4],transient_limits_V={'positive_design_test_V':40,'duration_ms':1,'source_ohm':1,'qualification':'NOT_ADAPTER_GUARANTEE'},adapter_mpn='GST40A24-P1J')
  elif rail['name']=='HV_BUS':rail.update(status='DESIGN_REQUIREMENT_BASELINED_NOT_VALIDATED',mean_limits_V=[164.9,175.1])
  elif rail['name']=='5V_SYS':rail.update(status='TWO_STAGE_AND_USB_MUX_CANDIDATE')
 c['unresolved']=['adapter hotplug/transient qualification','remaining passive exact MPN and primary specifications/footprints','actual tube and LV loads and thermal behavior','PG/hardware permit/default-off and loss-of-power circuit','USB pre-enumeration boot and 5V fault OVP','hot magnetic saturation and real switching models','CT loading/ramp/CCM startup/soft start/compensation','OVP/OC latch and safe reset','COUT discharge and single fault/touch criterion','reviewed native schematic and ERC/PCB not produced']
 dump(p,c)
 rows=readcsv(ROOT/'docs/TASKS.csv')
 states={'24V-01':'DONE_BASELINE','24V-02':'DONE_BUDGET','24V-03':'CANDIDATE_REVIEW','24V-04':'CANDIDATE_REVIEW','24V-05':'CANDIDATE_REVIEW','24V-06':'CANDIDATE_REVIEW','24V-07':'QUALIFICATION_NOT_PASSED','24V-08':'NOT_ENTERED','24V-11':'PREPARED_ISOLATED_DATA_ONLY'}
 for row in rows:
  if row['id'] in states:row['status']=states[row['id']]
  row['s05_evidence']='docs/SPRINT05_REPORT.md' if row['id'] in states else ''
 writecsv(ROOT/'docs/TASKS.csv',rows)
 # Export the human-reviewed source matrix without implying BOM release.
 text=(ROOT/'docs/S05_CIRCUIT_CANDIDATES.md').read_text(encoding='utf8')
 block=text.split('|位号/用途|',1)[1].split('## 2.',1)[0]
 matrix=[]
 for line in block.splitlines():
  if not line.startswith('|') or line.startswith('|---'):continue
  cells=line.strip('|').split('|')
  if len(cells)!=4:raise AssertionError('Malformed source matrix row')
  matrix.append(dict(role=cells[0],exact_candidate_mpn_package=cells[1].replace('**',''),primary_source_and_review=cells[2],remaining_qualification=cells[3],status='CANDIDATE_NOT_RELEASED'))
 writecsv(ROOT/'docs/sprint05/MPN_SOURCE_MATRIX.csv',matrix)
 oldrefs={x['ref'] for x in readcsv(ROOT/'baseline_snapshot/legacy12_netlist.csv')}
 pins=readcsv(ROOT/'netlist/candidate_power_pins.csv');new={}
 for x in pins:
  if x['ref'] not in oldrefs:new.setdefault(x['ref'],dict(ref=x['ref'],candidate_mpn=x['mpn'],layer=x['layer'],status='NEW_UNREVIEWED_CANDIDATE',note=x['route_note']))
 writecsv(ROOT/'docs/sprint05/NEW_CANDIDATE_DEVICES.csv',list(new.values()))
 checks={};base=json.loads((ROOT/'baseline_snapshot/baseline.json').read_text(encoding='utf8'))
 for rel,expected in base['protected_sha256'].items():
  p=REPO/rel;actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
  checks[rel]={'same':actual==expected,'expected':expected,'actual':actual}
 coverage=json.loads((ROOT/'docs/sprint05/coverage.json').read_text(encoding='utf8'))
 cs=json.loads((ROOT/'sim/cs_v1/results.json').read_text(encoding='utf8'))
 calc=json.loads((ROOT/'docs/sprint05/calculations.json').read_text(encoding='utf8'))
 rails={x['rail']:x for x in readcsv(ROOT/'docs/sprint05/POWER_RAILS.csv')}
 assert coverage['all_refs_covered'] and coverage['migration_rows']==211
 assert cs['passive_filter_pass'] and cs['24V_07']=='NOT_PASSED'
 assert abs(float(rails['VIN24']['power_W'])-calc['adapter_W_alloc'])<1e-9
 assert calc['CS']['ideal_limit_min_A']>calc['DCM_screen']['max_Ipk_A']
 assert c['manufacturing']=='HOLD'
 meta=json.loads((ROOT/'netlist/candidate_power_pins.meta.json').read_text(encoding='utf8'))
 assert meta['approved_for_native_generation'] is False
 assert len(pins)==len({(x['ref'],x['pin']) for x in pins})
 # Explicit topology checks on candidate data, not an electrical ERC.
 nets={(x['ref'],x['pin']):x['net'] for x in pins}
 assert nets['C100','1']=='24P' and nets['C101','1']=='VIN_RAW'
 assert nets['U20','7']=='AUX12' and nets['U20','3']=='CS_FILTER'
 assert nets['R36','1']=='CS_SHUNT' and nets['R36','2']=='CS_FILTER'
 assert nets['Q20','3']=='CS_SHUNT' and nets['R230','2']=='GND_HV'
 assert nets['U101','14']=='HV_PERMIT_UNRESOLVED'
 assert not any(x['ref']=='C10' for x in pins)
 local_links=[]
 for md in [ROOT/'README.md',*sorted((ROOT/'docs').glob('S05*.md')),ROOT/'docs/SPRINT05_REPORT.md']:
  for link in re.findall(r'\]\(([^)]+)\)',md.read_text(encoding='utf8')):
   if '://' not in link:
    target=(md.parent/link.split('#')[0]).resolve()
    if not target.exists():local_links.append({'file':str(md),'missing':link})
 assert not local_links,local_links
 verify={'date':'2026-11-14','timezone':'Asia/Shanghai','status':'EVIDENCE_AND_DATA_CHECK_ONLY_NOT_ELECTRICAL_PASS','legacy_protected_count':len(checks),'legacy_protected_unchanged':all(x['same'] for x in checks.values()),'legacy_checks':checks,'coverage':coverage,'candidate_pin_rows':len(pins),'source_matrix_rows':len(matrix),'new_candidate_refs':len(new),'passive_CS_cases':len(cs['cases']),'passive_CS_pass':cs['passive_filter_pass'],'topology_data_assertions':'PASS_SCOPE_LIMITED','local_doc_links':'PASS','24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','native_schematic_ERC_DRC':'NOT_RUN_NO_NATIVE_24V_DESIGN','manufacturing':'HOLD','physical_HV_powerup':False}
 dump(ROOT/'docs/sprint05/final_verification.json',verify)
 manifest={}
 for p in sorted(ROOT.rglob('*')):
  if p.is_file() and p.name!='manifest_s05.json' and '__pycache__' not in p.parts:
   manifest[str(p.relative_to(ROOT)).replace('\\','/')]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 dump(ROOT/'docs/sprint05/manifest_s05.json',manifest)
 print(json.dumps({k:v for k,v in verify.items() if k!='legacy_checks'},ensure_ascii=False,indent=2))
 if not verify['legacy_protected_unchanged']: raise RuntimeError('Legacy protected hash mismatch; inspect evidence, do not restore automatically')
if __name__=='__main__':main()
