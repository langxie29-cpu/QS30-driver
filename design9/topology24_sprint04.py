"""Sprint04 analytical mode-aware screening; no circuit or SPICE changes."""
from pathlib import Path
import json, math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs9/electrical_sprint04/topology24_calculations.json'
VOUT, L, FS = 170., 220e-6, 78e3
# Four 200k bleeders and all three HV dividers, including ADC R54/R55.
G = 4/200e3 + 1/(1.5e6+22.1e3) + 1/(1.5e6+19.1e3) + 1/(1.5e6+14.3e3)

def case(vin, tube_ma):
    io = 9*tube_ma/1000 + VOUT*G
    dccm = 1-vin/VOUT
    ibound = vin**2*dccm/(2*L*FS*VOUT)
    lcrit = vin**2*dccm/(2*FS*VOUT*io)
    if io < ibound:
        mode = 'DCM'
        duty = math.sqrt(2*L*FS*io*(VOUT-vin))/vin
        d2 = vin*duty/(VOUT-vin)
        ipk = vin*duty/(L*FS)
        iavg = ipk*(duty+d2)/2
        irms = ipk*math.sqrt((duty+d2)/3)
        idle = 1-duty-d2
        assert idle > 0
        assert math.isclose(ipk*d2/2, io, rel_tol=1e-12)
    else:
        mode, duty, d2, idle = 'CCM', dccm, 1-dccm, 0.
        iavg = io/(1-duty)
        delta = vin*duty/(L*FS)
        ipk = iavg + delta/2
        irms = math.sqrt(iavg*iavg + delta*delta/12)
        assert iavg-delta/2 >= -1e-12
    assert math.isclose(vin*iavg, VOUT*io, rel_tol=1e-12)
    return dict(vin_inductor_V=vin,tube_each_mA=tube_ma,output_A=io,output_W=VOUT*io,
                ideal_CCM_reference_D=dccm,CCM_reference_off_us=(1-dccm)/FS*1e6,
                boundary_output_A=ibound,critical_L_uH=lcrit*1e6,ideal_mode=mode,
                ideal_operating_D=duty,ideal_diode_fraction=d2,idle_fraction=idle,
                gate_off_us=(1-duty)/FS*1e6,diode_conduction_us=d2/FS*1e6,
                inductor_peak_A=ipk,inductor_average_A=iavg,inductor_rms_A=irms)

def main():
    data = dict(status='ANALYTICAL_SCREEN_ONLY_NOT_HARDWARE_PASS',
        assumptions=dict(vout_V=VOUT,L_H=L,frequency_Hz=FS,
            input_nodes='Inductor terminal; adapter/path drop not included',
            input_ranges='12V and 24V +/-5% and +/-10% research cases, not frozen supply specs',
            losses='Ideal semiconductor/linear L; no saturation/parasitics/C10/thermal'),
        extra_hv_conductance_S=G,
        cases=[case(v,i) for v in (10.8,11.4,12,12.6,13.2,21.6,22.8,24,25.2,26.4) for i in (0,1.5,2.25,3)],
        two_stage_CCM_references=[dict(vin_V=v,D1=1-v/48,D2=1-48/VOUT) for v in (11.4,12,12.6)],
        buck24to3V3=dict(D_nominal=3.3/24,ton_ns_at_500kHz=(3.3/24)/500e3*1e9,
            ton_ns_at26V4_630kHz=(3.3/26.4)/630e3*1e9,
            caution='Ideal duty/on-time only; TPS54202 typical tmin 110ns is not a full corner guarantee'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(OUT)
    for c in data['cases']:
        if c['tube_each_mA']==3:
            print(c)

if __name__=='__main__':main()
