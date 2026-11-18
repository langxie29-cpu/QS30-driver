"""Rebuild power, stress, programmed thresholds and stored-energy reference data."""
from itertools import product
from pathlib import Path
import csv
import math

ROOT = Path(__file__).resolve().parent


def table(name, rows):
    with (ROOT/name).open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    vo = 170
    feedback, ovp, adc, bleed = (vo*vo/201900, vo*vo/461000, vo*vo/202490, vo*vo/249000)
    static = feedback+ovp+adc+bleed
    states = (("no_tube",0,125),("one_min",1,140),("three_typ",3,125),("three_max",3,110))
    rows = []
    for vin, (name,ntubes,sustain), eff, inductance, freq in product(
        (10.8,12,13.2,21.6,24,26.4), states, (.70,.80,.85), (135e-6,150e-6,165e-6), (90e3,100e3,110e3)
    ):
        tube_amp = (vo-sustain)/20000
        load = static+vo*tube_amp*ntubes
        peak = math.sqrt(2*load*(vo-vin)/(eff*inductance*freq*vo))
        duty = peak*inductance*freq/vin
        discharge = peak*inductance*freq/(vo-vin)
        rows.append(dict(Vin_V=vin,load=name, tubes=ntubes,tube_sustain_V=sustain,
                         tube_total_mA=round(ntubes*tube_amp*1000,4),tube_power_W=round(vo*tube_amp*ntubes,6),
                         feedback_W=round(feedback,6),OVP_W=round(ovp,6),ADC_W=round(adc,6),
                         dual_bleeder_W=round(bleed,6),HV_total_W=round(load,6),LV_input_budget_W=.45,
                         eta=eff,L_uH=round(inductance*1e6),frequency_kHz=freq/1000,
                         avg_module_input_A=round((load/eff+.45)/vin,5),
                         dcm_peak_A=round(peak,5),duty_on=round(duty,5),duty_diode=round(discharge,5),
                         mode_screen="DCM" if duty+discharge<=1 else "CCM_NEEDS_MODEL"))
    table("POWER_AND_LOAD_BUDGET.csv", rows)
    seq = [
        ("U1 UVLO rising",1.175*7.8,1.19*7.8,1.225*7.8,"V","TI thresholds at nominal divider; tolerance separate","LIMITED_PASS"),
        ("U1 OVP rising",1.17*12.8,1.19*12.8,1.225*12.8,"V","TI thresholds at nominal divider; input TVS dynamic clamp separate","LIMITED_PASS"),
        ("U1 dVdT ramp",4*23.75/10,4.7*24.6/10,5.5*25.5/10,"V/ms","10nF nominal; ramp/interactions still open","LIMITED_PASS"),
        ("U1 dVdT at 10.8 V",10.8/(5.5*25.5/10),10.8/(4.7*24.6/10),10.8/(4*23.75/10),"ms","Plus enable delay; C2 tolerance and foldback separate","LIMITED_PASS"),
        ("U1 programmed limit","UNKNOWN",.60,"UNKNOWN","A","20k, nominal formula. 0.54/0.66A diagnostic sweep only","HOLD"),
        ("OVP output bus pick-up",.396*(1+460*.999/1.001),184.4,.404*(1+460*1.001/.999),"V","1% threshold, all divider 0.1%, before leakage/delay","LIMITED_PASS"),
        ("U6 AUX falling release","UNKNOWN",(.4-.0055)*27.5,"UNKNOWN","V","Hysteresis typical - confirm loaded AUX and all corners","HOLD"),
        ("U6 input to fault output ","UNKNOWN","MEASURED_IN_CELL","UNKNOWN","us","Actual vendor macro, one ramp; threshold and slope dependent","LIMITED_PASS"),
        ("U7 compare to hard shutdown","UNKNOWN","UNKNOWN","UNKNOWN","us","Supply, clear/setup/hold; simulation proxy","HOLD"),
        ("U1 power interruption","UNKNOWN","UNKNOWN","UNKNOWN","us","Measure OUT current fall upstream of C3 with Kelvin sense; FLT not cut current","HOLD"),
        ("AUX loss shift/blank after fault","UNKNOWN","UNKNOWN","UNKNOWN","us","U6 A commands LT only. U5 continues to respond to forced PWM above its UVLO","HOLD"),
        ("POR / residual ARM","UNKNOWN","UNKNOWN","UNKNOWN","ms","U8, U7 and button qualification. No residual hardware permit exists","HOLD"),
    ]
    table("PROTECTION_TIMING_BUDGET.csv",[dict(path=a,min=b,typ=c,max=d,unit=e,scope=f,status=g)
                                          for a,b,c,d,e,f,g in seq])
    energy = []
    for c_uf, v in product((4.5,5,5.5),(170,184.4,195)):
        for n in (1,2):
            r = 498000*1.01/n
            energy.append(dict(case=f"output_{n}_working_bleeder",total_C_uF=c_uf,V_initial=v,
                               stored_J=round(.5*c_uf*1e-6*v*v,8), max_continuing_source_W="UNKNOWN",
                               t_to_60V_s=round(r*c_uf*1e-6*math.log(v/60),6),
                               t_to_30V_s=round(r*c_uf*1e-6*math.log(v/30),6),
                               scope="Independent discharge with supply disconnected; ignore other parallel paths"))
    for case,c,v,e,scope in (
        ("protected_C3_upper_screen",1.2,13.2,.5*1.2e-6*13.2**2,"1uF assumed +20%; MLCC DC bias and tolerance pending"),
        ("AUX_all_caps_upper_screen",6,13.2,.5*6e-6*13.2**2,"4.7uF and 3x100nF with +20%; coupling to HV unproven"),
        ("L1_energy_at_replay_peak",0,0,.5*165e-6*1.09954**2,"165uH and recorded R6 passive-inrush current; linear upper sensitivity"),
        ("source_during_100us_with_0p6A",0,13.2,13.2*.6*100e-6,"Illustrative 0.6A clip, not a guaranteed transient cap"),
        ("U1_failed_short_passive_path",0,13.2,"UNBOUNDED_OVER_TIME","External source limits and F1/TVS SOA unknown"),
    ):
        energy.append(dict(case=case,total_C_uF=c,V_initial=v,stored_J=e,max_continuing_source_W="UNKNOWN",
                           t_to_60V_s="NOT_APPLICABLE",t_to_30V_s="NOT_APPLICABLE",scope=scope))
    table("FAULT_ENERGY_BUDGET.csv",energy)


if __name__=="__main__":
    main()
