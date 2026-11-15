"""Bounded 12/24V open-loop DCM research, not a controller or hardware signoff."""
from pathlib import Path
import hashlib, json, math, shutil
import numpy as np
import sprint03_hv as h

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'sim/sprint04/open_loop_v1'
F = 78000
L = 220e-6
VO = 170.0
IO = .027 + VO / 50000 + VO / 1522100 + VO / 1519100 + VO / 1514300

def operating_point(vin):
    dccm = 1 - vin / VO
    boundary = vin * dccm * (1-dccm) / (2*L*F)
    if IO < boundary:
        duty = math.sqrt(2*L*F*IO*(VO-vin)) / vin
        mode = 'DCM'
        ipk = vin*duty/(L*F)
    else:
        # Same limited room-temperature conduction screen as Sprint03.
        # Includes 1V diode and .3/.55/.15 ohm winding/MOS/shunt assumptions.
        a=VO+1; b=vin+IO*.7; c=IO*1.0
        q=(b+math.sqrt(b*b-4*a*c))/(2*a)
        duty=1-q; mode='CCM'
        avg=IO/q
        ipk=avg+(vin-avg*1.0)*duty/(2*L*F)
    return dict(vin_V=vin, io_A=IO, mode_screen=mode, duty=duty,
                ideal_CCM_duty=dccm, ideal_boundary_A=boundary, ideal_or_screen_peak_A=ipk,
                turnoff_window_s=(1-duty)/F,
                status='Research assumptions; not approved worst-case design')

def deck(p, c10=False, step=50e-9, vendor=True):
    # Hot-start at target voltage, no current-feedback, no automatic regulation.
    text=f'''Sprint04 fixed-PWM hot-start diagnostic - NOT ACTUAL CIRCUIT
.model NSW SW(RON=.55 ROFF=1e10 VT=3 VH=.1)
.model UF D(IS=10n N=1.5 RS=.5 CJO=15p TT=75n BV=1000 IBV=5u)
.model BODY D(IS=1n N=1.5 RS=.1 CJO=1p TT=100n BV=400)
VIN vin 0 {p['vin_V']}
RL vin lin .3
L20 lin sw 220u IC={0 if p['mode_screen']=='DCM' else IO/(1-p['duty'])}
VSWI sw mos 0
S20 mos src gate src NSW
RSENSE src 0 .15
DBODY src mos BODY
COSS mos src 150p
{'X20' if vendor else 'D20'} sw da {'UF4007' if vendor else 'UF'}
VDPROBE da hv 0
RESR hv cap .5
COUT cap 0 20.3u IC=170
RBLEED hv 0 50k
RFB hv 0 1.5221meg
ROVP hv 0 1.5191meg
RADC hv 0 1.5143meg
BTUBE hv 0 I=27m*min(max(v(hv)/150,0),1)
VPWM gate src PULSE(0 10 0 30n 30n {p['duty']/F-30e-9} {1/F})
'''
    if c10:
        text+='C10 sw hv 10n\n'
    if vendor:
        text+=(ROOT/'sim/sprint03/diagnostics_v1/diotec_compat.lib').read_text()
    return text+h.control(.003,step,'v(hv) v(cap) v(sw) v(src) v(gate) i(l20) i(vdprobe) v(mos) i(vswi)')

if __name__=='__main__':
    DEST.mkdir(parents=True,exist_ok=False)
    for source in [Path(__file__), ROOT/'design9/sprint03_hv.py', ROOT/'sim/sprint03/diagnostics_v1/diotec_compat.lib']:
        shutil.copyfile(source,DEST/source.name)
    assumptions=dict(target_V=VO,full_load_A=IO,inductor_H=L,frequency_Hz=F,
        input_envelope='22.8/24/25.2V exploratory +/-5%; not adapter guarantee; inductor-terminal voltage',
        conditions='3ms precharged open-loop; no UC3843, no OVP, no startup or closed-loop signoff',
        c10='Absent in baseline research only; actual formal C10 retained. Separate present comparison.',
        diode='Diotec research supplier hypothesis; inherited compatibility copy removes metadata only',
        acceptance='Execution requires rc0, native 3ms endpoint, wave output, no parsed errors. Engineering stays INCONCLUSIVE.',
        analytic_reference='https://www.ti.com/lit/an/slva061/slva061.pdf')
    h.dump(DEST/'assumptions.json',assumptions)
    cases=[('input12',12,False,50e-9,True),('input24_low',22.8,False,50e-9,True),
           ('input24',24,False,50e-9,True),('input24_high',25.2,False,50e-9,True),
           ('input24_c10',24,True,50e-9,True),('input24_step25ns',24,False,25e-9,True),
           ('input24_generic',24,False,50e-9,False)]
    results=[]
    for name,vin,c10,step,vendor in cases:
        p=operating_point(vin);p.update(c10_present=c10,max_step_s=step,vendor_diode=vendor)
        r=h.run(DEST,name,'Fixed PWM hot-start energy/mode screening; not autonomous regulation',deck(p,c10,step,vendor),.003,'power',p)
        if r['execution']=='PASS':
            t,v=h.loadwave(DEST/name/'waves.txt'); late=t>.0025
            current=v('i(l20)'); low=np.abs(current)<.01
            r['mode_diagnostic']=dict(late_time_fraction_abs_IL_below_10mA=float(np.trapezoid(low[late].astype(float),t[late])/(t[late][-1]-t[late][0])),
                IL_late_min_A=float(current[late].min()),IL_late_max_A=float(current[late].max()),
                VGS_min_V=float((v('v(gate)')-v('v(src)')).min()),VGS_max_V=float((v('v(gate)')-v('v(src)')).max()))
            h.dump(DEST/name/'command.json',r)
        results.append(r)
    h.dump(DEST/'results.json',dict(assumptions=assumptions,results=results,
        system='FAIL/HOLD',HV_G0='BLOCKED',HV_G1='BLOCKED',HV_G2='FAIL'))
    print('Completed',sum(r['execution']=='PASS' for r in results),'/',len(results))
