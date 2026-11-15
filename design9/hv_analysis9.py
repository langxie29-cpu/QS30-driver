"""Independent numerical checks, no SPICE or presumed efficiency signoff."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'sim/a9_3/independent_calculations.json'

def oscillator(rt,ct,idis):
    # Integrate C*dV/dt=(5-V)/Rt and C*dV/dt=(5-V)/Rt-Id exactly.
    charge=rt*ct*math.log((5-1)/(5-2.7))
    discharge=rt*ct*math.log((2.7-5+idis*rt)/(1-5+idis*rt))
    return dict(rt_ohm=rt,ct_F=ct,idis_A=idis,charge_s=charge,deadtime_s=discharge,frequency_Hz=1/(charge+discharge),dmax=charge/(charge+discharge))

def corner(top,bot,vmin,vmax,offset=0):
    return dict(nominal_V=(1+top/bot)*(vmin+vmax)/2,
                low_V=(vmin-offset)*(1+top*.99/(bot*1.01)),
                high_V=(vmax+offset)*(1+top*1.01/(bot*.99)))

r={
 'status':'PROVISIONAL parameter assumptions; exact arithmetic is VERIFIED, hardware margins HOLD',
 'oscillator':[oscillator(rt,ct,idis) for rt,ct in [(10000,2.2e-9),(22000,1e-9)] for idis in [.0028,.006,.0083]],
 'oscillator_note':'2.8 and 8.3 mA are exploratory stress assumptions, NOT UC3843 guaranteed bounds. DN40 illustrates discharge-current variation; freeze manufacturer/suffix before deriving production bounds.',
 'feedback_1pct_UC_FB_2p42_to_2p58':corner(1.5e6,22100,2.42,2.58),
 'ovp_original_TL431C_and_5mV':corner(1.5e6,19100,2.44,2.55,.005),
 'ovp_candidate_TL431C_and_5mV':corner(1.5e6,19600,2.44,2.55,.005),
 'energy_J':{str(v):.5*20.3e-6*v*v for v in [172.1832579,198.44,220,230]},
 'c10_hard_charge_loss_W':.5*10e-9*172.1832579**2*78000,
 'c10_hard_charge_Q_C':10e-9*172.1832579,
 'c10_note':'Hard-charge loss estimate per cycle; actual energy recovery and stress require real commutation model/measurement.',
 'gate_drive_63nC_78kHz_A':63e-9*78000,
 'passive_discharge':dict(all_connected_to50_s=50e3*20.3e-6*math.log(172.1832579/50),main_only_to50_s=200e3*20e-6*math.log(172.1832579/50)),
 'operating_points':[]}
for vin in [11.4,12,12.6]:
    for load in [.02025,.027]:
        vo=172.1832579;d=1-vin/vo;delta=vin*d/(220e-6*78000)
        for eta in [.75,.85,.9]:
            po=vo*load+vo*vo/50000
            iavg=po/(vin*eta); rms=math.sqrt(iavg*iavg+delta*delta/12)
            fz=vo/(load+vo/50000)*(1-d)**2/(2*math.pi*220e-6)
            r['operating_points'].append(dict(vin_V=vin,tube_load_A=load,assumed_eta=eta,pout_including_bleed_W=po,duty_ideal=d,off_time_s=(1-d)/78000,inductor_delta_A=delta,inductor_mean_A=iavg,inductor_peak_A=iavg+delta/2,inductor_rms_A=rms,dcr_loss_at_p3ohm_W=rms*rms*.3,mos_conduction_at_p55ohm_W=rms*rms*d*.55,mos_overlap_50ns_W=.5*vo*(iavg+delta/2)*50e-9*78000,diode_forward_at1V_W=load+vo/50000,capacitive_ripple_V=(load+vo/50000)*d/(20.3e-6*78000),rhp_zero_CCM_resistive_equivalent_Hz=fz,conservative_crossover_ceiling_Hz=min(78000/10,fz/5),minimum_slope_V_per_s_at_Rs_p15= .15*((vo-vin)-vin)/(2*220e-6)))
r['topology_candidates']=dict(single_boost_12_170_D=1-12/170,two_stage_12_48_D=1-12/48,two_stage_48_170_D=1-48/170,flyback_Ns_Np_8_D=170/(170+12*8),flyback_ideal_switch_V=12+170/8,flyback_ideal_diode_V=170+12*8)
out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
print(out)
