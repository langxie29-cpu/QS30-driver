"""Codex's independent analytical checks; no simulated waveform generation."""
from pathlib import Path
import json, math, hashlib
HERE=Path(__file__).resolve().parent

def calculate():
    v=170.; r=90900.; n=2; branches=2; c=21.315e-6
    total_r=r*n/branches
    total_p=v*v/total_r
    unit_p=(v/n)**2/r
    return {
        'method':'Direct circuit equations, independent of Flash scripts; not SPICE qualification',
        'bleeders':{'R_each_ohm':r,'series_count':n,'parallel_branches':branches,
            'P_total_170V_W':total_p,'P_each_resistor_170V_W':unit_p,
            'check_sum_W':unit_p*n*branches,'delta_from_single_200k_W':total_p-v*v/200000,
            'HV_budget_after_delta_W':5.71642+total_p-v*v/200000,
            'mixed_voltage_budget_warning':'The preceding legacy5.88985W floor mixes175.1V source budget and170V delta; use corrected upper-voltage budget below.',
            'delta_at175p1V_W':175.1**2*(1/90900-1/200000),
            'HV_budget175p1V_corrected_W':5.716423382277459+175.1**2*(1/90900-1/200000),
            'P_survivor_one_short_195V_Rminus1pct_W':195**2/(r*.99),
            'one_string_open_discharge_195to60_s':r*n*1.01*c*math.log(195/60)},
        'control':{'CCM_ideal_duty_21p6V':1-21.6/v,'CCM_ideal_duty_26p4V':1-26.4/v,
            'warning':'CCM duty is NOT DCM duty. Startup can traverse CCM; UCC28C43 requires slope compensation review.',
            'LT_feedback_nominal_V':1.6*(1+200000/(1820+80.6)),
            'LT_nominal_current_limit_110mV_over62mohm_A':.110/.062,
            'stored_C_energy_170V_J':.5*c*v*v,
            'minimum_net_charge_power_for_1s_W':.5*c*v*v,
            'warning2':'Nominal current threshold is not worst-case peak; blanking/delay, hot L, tolerance and model uncertainty remain open.'},
        'acceptance':{'vin_V':[21.6,26.4],'vout_mean_V':[164.9,175.1], 'ripple_Vpp_max':1,
            'normal_peak_V_max':180,'cold_start_s_max':1,'recovery_s_max':.1,'specified_fault_peak_V_max':195},
        'milestones':{'M1':'PENDING_NATIVE_REFERENCE_AND_DEVICE_REVIEW','M2':'NOT_PROVEN','M3':'NOT_PROVEN'},
        'manufacturing':'HOLD'
    }

if __name__=='__main__':
    out=HERE/'evidence/independent'
    out.mkdir(parents=True,exist_ok=True)
    result=calculate()
    assert abs(result['bleeders']['P_total_170V_W']-result['bleeders']['check_sum_W'])<1e-12
    (out/'calculations.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
