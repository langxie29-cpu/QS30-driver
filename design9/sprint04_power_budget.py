"""Read-only arithmetic study; writes only new Sprint04 power-budget results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs9/electrical_sprint04/power_budget_results.json'

def calculate():
    rows = []
    for v in (170.0, 2.5 * (1 + 1500 / 22.1)):
        bleed = v*v/50000
        dividers = {name: v*v/r for name,r in (
            ('feedback',1522100), ('OVP',1519100), ('ADC',1514300))}
        for i in (.0015,.00225,.003):
            branches = 9*v*i
            resistors = 9*i*i*20000
            total = branches+bleed+sum(dividers.values())
            rows.append(dict(bus_V=v,per_tube_A=i,branch_power_W=branches,
                anode_resistors_W=resistors,tube_plus_driver_W=branches-resistors,
                tube_plus_driver_voltage_V=v-i*20000,
                bleeders_W=bleed,dividers_W=dividers,total_known_HV_W=total,
                HV_input_current_A={str(vin):[total/(vin*.9),total/(vin*.75)] for vin in (12,24)}))
    maxhv = rows[2]['total_known_HV_W']
    return dict(status='RESEARCH_ONLY_NOT_SYSTEM_PASS',rows=rows,
        low_voltage_example=dict(rail3V3_A=.8,rail3V3_W=2.64,
            HV5622_12V_A_3chips_datasheet_high_clock=.045,
            HV5622_12V_W=.54,LV_example_total_W=3.18,
            system_power_W_before_other_aux=[maxhv/.9+3.18/.9,maxhv/.75+3.18/.8],
            system_current_A_before_other_aux={str(vin):[(maxhv/.9+3.18/.9)/vin,(maxhv/.75+3.18/.8)/vin] for vin in (12,24)}),
        assumptions=['HV efficiency .75-.90 is sensitivity only, not measured',
            'LV combined efficiency .80-.90 is sensitivity only, not measured',
            '.8A on 3V3 inherited allocation, not measured demand',
            '15mA/chip HV5622 at 8MHz CLK/4MHz DATA; not actual clock consumption',
            'known HV total omits off-state leakage, abnormal states, tolerances and transients',
            'normal operation: one cathode per tube, nine branches; not 90 simultaneous independent loads',
            'no tube sustaining voltage or driver low-current drop assumed'])

if __name__ == '__main__':
    if OUT.exists():
        raise SystemExit('Refusing to overwrite prior results')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(calculate(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(OUT)
