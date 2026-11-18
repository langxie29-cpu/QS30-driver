"""Summarize observed resource usage from frozen execution receipts."""
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
flash=[json.loads(p.read_text(encoding='utf-8')) for p in E.glob('flash_r*.json')]
runs=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'LTSPICE_MODEL'/'runs').glob('*/result.json')]
with (ROOT/'SIMULATION_RESULTS.csv').open(encoding='utf-8',newline='') as src:
    classes=Counter(row['classification'] for row in csv.DictReader(src))
groups = {
  1: ('Architecture and basis','BASELINE.md POWER_CORNERS.csv SYSTEM_ARCHITECTURE.md POWER_REQUIREMENTS.md POWER_TOPOLOGY_COMPARISON.md'),
  2: ('Design and protections','BOOST_DESIGN.md SAFETY_ARCHITECTURE.md FAULT_ENERGY_BUDGET.csv COMPONENT_SELECTION.csv PRELIMINARY_BOM.csv'),
  3: ('Native LTspice','LTSPICE_MODEL SIMULATION_MATRIX.csv SIMULATION_RESULTS.csv PARAMETER_ITERATIONS.csv WAVEFORM_ANALYSIS.md'),
  4: ('Native EDA and C prototype','NXT_M3_EDA FIRMWARE_PROTOTYPE PIN_MAPPING.csv FOOTPRINT_REVIEW.csv ERC_REPORT.md COMMUNICATION_PROTOCOL.md MODULAR_INTERFACE_SPEC.md'),
  5: ('Costs and qualifications','COST_COMPARISON.csv FINAL_ENGINEERING_REPORT.md QUALIFICATION_MATRIX.json LEGACY_REUSE_MATRIX.csv MANUFACTURING_BLOCKERS.md HARDWARE_VALIDATION_PLAN.md')
}
rounds=[]
for key,(purpose,scope) in groups.items():
    receipts = [f for f in flash if f['round']==key]
    path = E/f'flash_r{key}_1.json'
    utc = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec='seconds')
    rounds.append(dict(round=key, purpose=purpose, tracked_files=scope.split(),
                       decision=f'R{key}_DECISION_RECORD.md', first_flash_receipt_utc=utc,
                       called=sum(bool(f.get('called')) for f in receipts),
                       flash_seconds=sum(f['seconds'] for f in receipts),
                       flash_states=Counter(f['status'] for f in receipts),
                       flash_finish=Counter(f.get('finish','UNKNOWN') for f in receipts),
                       flash_tokens=sum((f.get('usage') or {}).get('total_tokens',0) for f in receipts),
                       LTspice_calls=len(runs) if key==3 else 0,
                       LTspice_wall_seconds_total=round(sum(r['seconds'] for r in runs),3) if key==3 else 0,
                       LTspice_classes=classes if key==3 else {},
                       model_sources=['ADI bundled LT3757A','ST factory STP9NK50Z/SiC','Vishay SS14',
                                      'explicit behavioral/placeholders restricted per experiment'] if key==3 else [],
                       independent_reviews=[f'flash_r{key}_{f["session"]}.json' for f in receipts],
                       charging='UNKNOWN', quotes='PRICE_EVIDENCE.csv' if key==5 else
                               'PRELIMINARY_BOM.csv' if key==2 else 'N/A'))
total = dict(flash_calls=sum(r['called'] for r in rounds),
             flash_tokens=sum(r['flash_tokens'] for r in rounds),
             LTspice_calls=len(runs), classes=classes, child_codex_calls=0, currency_cost='UNKNOWN')
(E/'resources.json').write_text(json.dumps(dict(rounds=rounds,total=total,
    timing_scope='Actual recorded tool wall times, summed and may overlap; total round wall time not instrumented separately'),
    indent=2)+'\n',encoding='utf-8')
print(json.dumps(total))
