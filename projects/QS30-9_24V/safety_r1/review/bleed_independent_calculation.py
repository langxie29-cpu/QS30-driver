"""Independent analytical bounds for proposed two permanent bleed strings."""
import json,math,pathlib
r=181800.;c=21.315e-6;v=195.
data={
 'scope':'Ideal RC and initial resistor tolerance only; TCR, ageing, shared ground and component ratings unqualified',
 'single_string_t_to_60_s':r*1.01*c*math.log(v/60),
 'stored_energy_195V_J':.5*c*v*v,
 'normal_two_strings_power_170V_W':2*170**2/r,
 'increment_vs_one_200k_170V_W':2*170**2/r-170**2/200000,
 'intact_string_power_195V_Rmin_W':v*v/(r*.99),
 'short_fault_remaining_resistor_power_195V_Rmin_W':v*v/(90900*.99),
 'short_fault_total_main_power_W':v*v/(r*.99)+v*v/(90900*.99),
 'single_resistor_max_V_after_other_short':195,
 'manufacturing':'HOLD'}
assert data['single_string_t_to_60_s']<5
pathlib.Path(__file__).with_suffix('.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
print(json.dumps(data,indent=2))
