"""Independent small-signal order-of-magnitude calculation, not a loop PASS."""
import json,math,hashlib
from local_probe import HERE
if __name__=='__main__':
 p=HERE/'evidence/candidate_diagnostic/nominal_24V_gear_resource600/circuit.cir'
 s=p.read_text();assert 'RLOAD hv 0 5200' in s and 'COUT hv 0 20.3u' in s
 r=1/(1/5200+1/90900+1/201900.6);c=20.3e-6
 rc_pole=1/(2*math.pi*r*c);power_pole=1/(math.pi*r*c);zero=1/(2*math.pi*22000*6.8e-9)
 ref=1/(2*math.pi*12*94e-6)
 j=dict(classification='INCONCLUSIVE',scope='Analytical order-of-magnitude only; no additional model calls or SPICE runs',
  source_net_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),Rload_effective_ohm=r,Cout_F=c,RC_time_constant_s=r*c,
  passive_RC_pole_Hz=rc_pole,constant_power_control_approx_pole_Hz=power_pole,compensator_R22k_C6p8n_zero_Hz=zero,
  compensator_zero_over_approx_plant_pole=zero/power_pole,
  vendor_reference_RC_pole_Hz=ref,reference_to_candidate_RC_pole_ratio=ref/rc_pole,
  derivation='For C*dV/dt=Pcommand/V - V/R and P0=V0^2/R, d(deltaV)/dt=deltaP/(C*V0)-2*deltaV/(R*C), so fp=1/(pi*R*C). This is a constant-power approximation, not the exact finite-Vin, current-mode, DCM/CCM plant.',
  decision='Do not infer compensation adequacy from the24V demo: the load/C pole scale changes greatly while the copied RC zero stays near1kHz. Actual operating-point frequency-response and settling must be evaluated after current-cell stress is understood. No component change approved by this calculation alone.',
  limitations=['Actual duty/current-control/slope compensation and conduction-mode transitions not modeled by this formula',
   'Cannot separate the observed output oscillation cause from SENSE/diode/model artifacts',
   'No gain margin/phase margin or final compensation values claimed'])
 out=HERE/'evidence/independent/compensation_screen.json';out.write_text(json.dumps(j,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(j,indent=2))
