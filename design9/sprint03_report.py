"""Derive Sprint03 calculations, matrices and integrity manifest from raw evidence."""
import csv, json, math, subprocess
from pathlib import Path
import sprint03_hv as h
R=h.ROOT; B=h.BASE; D=R/'docs9/electrical_sprint03'
def main():
    D.mkdir(exist_ok=True)
    assert not (D/'calculations.json').exists(),'Use a new report version instead of overwriting'
    V=2.5*(1+1500/22.1);io=.027+V/50000+V/1522100+V/1519100
    table=[]
    for vi in [10.9,11.4,12,12.6]:
        q=((vi+io*.7)+math.sqrt((vi+io*.7)**2-4*(V+1)*io))/(2*(V+1));d=1-q;I=io/q
        di=(vi-I*(.3+.7))*d/(220e-6*78000);rms=math.sqrt(I*I+di*di/12)
        table.append(dict(vin_at_inductor_V=vi,ideal_D=1-vi/V,lossy_D=d,off_time_s=q/78000,Iavg_A=I,deltaI_A=di,Ipeak_A=I+di/2,Irms_A=rms,MOS_Irms_A=rms*math.sqrt(d),diode_Irms_A=rms*math.sqrt(q),DCR_loss_W=rms*rms*.3,MOS_conduction_W=rms*rms*.55*d,shunt_loss_W=rms*rms*.15*d,diode_conduction_W=io,RHP_zero_resistive_Hz=(V/io)*q*q/(2*math.pi*220e-6),capacitive_ripple_V=io*d/(20.3e-6*78000),CCM_boundary_Iout_A=vi*d*q/(2*220e-6*78000)))
    calc=dict(target_V=V,tube_currents_A=[.0135,.02025,.027],bleed_A=V/50000,divider_A=V/1522100+V/1519100,total_max_output_A=io,total_max_output_W=V*io,feedback_reference_only_extremes_V=[2.42*(1+1500*.99/(22.1*1.01)),2.58*(1+1500*1.01/(22.1*.99))],bias_effect_2uA_times_Rtop_V=3,C10_single_edge_energy_W=.5*10e-9*V*V*78000,stored_energy_J=.5*20.3e-6*V*V,cases=table,assumptions='HV input envelope exploratory; L220u DCR.3 Ron.55 source shunt.15 diode1V,78kHz; DC/ripple approximation excludes commutation, input gating, wiring, thermal and saturation. No efficiency fitted.')
    h.dump(D/'calculations.json',calc)
    runs=json.loads((B/'qualification_v1/results.json').read_text())['results']+json.loads((B/'diagnostics_v1/results.json').read_text())
    with (D/'SIMULATION_MATRIX.csv').open('w',encoding='utf8',newline='') as f:
        fields=['id','purpose','execution','engineering','exit_code','duration_s'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r.get(k,'') for k in fields} for r in runs)
    def row(ref,param,value,status,model,source,ds,impact):return dict(ref=ref,parameter=param,value_unit=value,status=status,model_implementation=model,source=source,datasheet=ds,blocking_impact=impact)
    ti='https://www.ti.com/lit/ds/symlink/uc3843a.pdf';vi='https://www.vishay.com/docs/91054/irf740.pdf';uf='https://diotec.com/en/product/UF4007.html'
    source='netlist9/QS30-9_REV.A_netlist.csv; Sprint03 native_hv_pins.csv (ref/pin locator); bom9/BOM9_A.csv (refs locator)'
    rows=[
      row('J1','Input nominal','12 V','CONFIRMED','VIN fixture; .05/.5 ohm historical hypotheses','bom9/BOM9_A.csv:J1; docs9/G0_ARCHITECTURE.md:EXT12','UNKNOWN adapter','Actual adapter min/max/current/transients unknown'),
      row('J1','Input envelope/current','11.4–12.6 V exploratory; rated current UNKNOWN','ASSUMED','Research VIN at inductor terminal','docs9/OVP_SIMULATION_INPUTS.md:boundary values','UNKNOWN','Front diode/Q4/cable loss means not identical to adapter voltage'),
      row('U20','Order code/package','UC3843AN; DIP-8; manufacturer UNKNOWN','CONFIRMED','Inherited generic functional model; NOT vendor AN model',source,ti,'Order code exists for TI A-family, actual manufacturer/procurement not frozen; PRELIM_8P is not approved DIP geometry'),
      row('U20','A-series timing/PWM conditional on TI','IDIS 7.6–8.8 mA over UC384xA range; 8.3 nominal; DMAX92/96/100 % at specified table conditions','ASSUMED','Only IDIS sensitivity .0076/.0083/.0088; nominal oscillator thresholds inherited','Sprint03 source/TI_UC3843A.txt:5.5 pp6–7',ti,'Does not create a joint timing/temperature/drive corner guarantee'),
      row('L20','L/current designation','220 uH / >=5 A design label; 12x12','CONFIRMED','Linear 220u; no saturation',source,'UNKNOWN actual magnetics','MPN, Irms, Isat definition/tolerance/temp missing'),
      row('L20','DCR','0.3 ohm','ASSUMED','RL=.3', 'sim/sprint03/qualification_v1/power_0.935/circuit.cir','UNKNOWN','Loss, gain, saturation and hot winding cannot qualify'),
      row('Q20','MOS family/rating','IRF740; TO-220; 400 V /10 A designation','CONFIRMED','Switch Ron=.55; fixed150pF Coss; body diode generic',source,vi,'Manufacturer/suffix/Tj/SOA and nonlinear electrical model unknown'),
      row('Q20','Vishay comparator R/Qg','Rds max .55 ohm at Vgs10V Id6A; Qg max63 nC at Vds320V Id10A; Qgd32 nC','ASSUMED','Ron only; 1nF gate replaces actual charge; Qgd absent','sim/a9_3/sources/Vishay_IRF740.pdf.txt:pp1–2',vi,'Conditional family comparison; no gate-drive/stress qualification'),
      row('D20','Rectifier','UF4007; DO-41;1000 V/1 A label','CONFIRMED','Generic D or separate Diotec hypothesis',source,uf,'Actual supplier unconfirmed'),
      row('D20','Recovery','75 ns Diotec product nominal descriptor','ASSUMED','TT75n generic; official subckt electrical params retained in separate test','sim/sprint02/source/diotec_uf4007_spice.lib',uf,'TT is not a universal trr waveform guarantee; supplier-specific model unqualified'),
      row('C11,C12','Output capacitance','2x10 uF/250 V; SMD-8x12 label','CONFIRMED','20.3u lumped including module caps; ESR.5 hypothesis',source,'UNKNOWN actual capacitor','ESR/ESL, ripple-current, lifetime, tolerance, voltage and thermal data absent'),
      row('C10','Across diode capacitance','10 nF /630 V across SW_HV/HV_BUS','CONFIRMED','Retained in one controlled comparison; absent only in separate hypotheses',source,'UNKNOWN actual capacitor','Hard switching burden; not a qualified RC snubber'),
      row('R36,C13,Q20','Actual sense path','100 kohm SW-to-CS;470 pF GND;Q20.S=GND','CONFIRMED','Known-current forced SW12V experiment',source,ti,'No current transduction; cannot define OCP amperes'),
      row('RSENSE','Hypothetical shunt','0.15 ohm; power/tolerance UNKNOWN','ASSUMED','Independent Kelvin demonstration only','Sprint03 kelvin_*.cir', 'UNKNOWN','1V/.15=6.67A before slope/filter effects; not selected safe limit for >=5A label'),
      row('R34,R35','Feedback divider','1.5 Mohm (2x750k1% description) /22.1 kohm1% description','CONFIRMED','Same values; FB nominal2.5V',source,ti,'Physical MPN, bias/ref tolerances and temperature prevent output tolerance freeze'),
      row('R37,C14,C15','Actual compensation','10 kohm;100 nF branch to GND;22 uF COMP-to-GND','CONFIRMED','Original short screen retains it; Type-II is separate historical hypothesis',source,ti,'Not equivalent to historical 4.7u/1n FB-return Type-II'),
      row('R32,C9','Timing','10 kohm /2.2 nF;78 kHz design estimate','CONFIRMED','8.3mA functional baseline78.948kHz; unloaded','native_hv_pins.csv:R32/C9; docs9/POWER9.md',ti,'Actual timing tolerances, VCC and drive frequency corners unknown'),
      row('T1–T9','Load design basis','1.5/2.25/3 mA each;13.5/20.25/27 mA nine tubes','CONFIRMED','New screen 27mA at high voltage; legacy max((HV-125)/20k,0)','docs/source_scans/QS30-1_原厂说明书_p2_基本参数表.png; docs9/ELECTRICAL_CLOSURE_SPRINT01.md:3','Repository original manufacturer scan','Batch sustaining voltage, ignition/hysteresis and HV5622 drop unknown'),
      row('R33,R_MOD_*_BLEED','Bleed network','4x200 kohm =>50 kohm; .593 W at172.18V','CONFIRMED','50k aggregate','native_hv_pins.csv; docs9/OVP_SIMULATION_INPUTS.md:bleed','UNKNOWN resistor MPN','Main alone200k/20u; one open not redundant safety'),
      row('Input/load/acceptance','Freeze evidence','Approved ripple/start/overshoot/derating UNKNOWN','UNKNOWN','No Gate PASS assigned','docs9/GATES.md; docs9/HOLD_REGISTER.md; sim/sprint02/acceptance.json','N/A','Prior experimental thresholds not recorded user-approved system specification')]
    with (D/'COMPONENT_MODEL_MATRIX.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    h.dump(D/'results.json',dict(system='FAIL/HOLD',topology='UNKNOWN',HV_G0='BLOCKED',HV_G1='BLOCKED',HV_G2='FAIL',runs=len(runs),completed=sum(r['execution']=='PASS' for r in runs),timeouts=sum(r['exit_code']=='TIMEOUT' for r in runs),runtime_s=sum(r['duration_s'] for r in runs),further_closed_loop='BLOCKED at G0, not run'))
    baseline=json.loads((B/'baseline.json').read_text(encoding='utf8'));changed=[p for p,d in baseline['protected_sha256'].items() if not (R/p).exists() or h.sha(R/p)!=d]
    assert not changed,changed
    h.dump(D/'integrity.json',dict(protected_files_checked=len(baseline['protected_sha256']),prior_files_changed=changed,head_unchanged=h.git('rev-parse','HEAD').strip()==baseline['head'],branch=h.git('branch','--show-current').strip(),native_export='2 sch XML exports rc0;64 HV CSV/native pin comparisons',DRC_ERC='Not rerun; native engineering inputs unchanged; counts inherited, not Sprint03 measurements'))
    (D/'git-diff-stat.txt').write_text(h.git('diff','--stat'),encoding='utf8')
    (D/'git-status.txt').write_text(h.git('status','--short'),encoding='utf8')
    print(json.dumps(calc,ensure_ascii=True,indent=2));print('Prior-file integrity OK',len(baseline['protected_sha256']))
if __name__=='__main__':main()
