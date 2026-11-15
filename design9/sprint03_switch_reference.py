"""Qualify switch-control reference; no compensator or physical value search."""
import json, shutil
import numpy as np
import sprint03_hv as h
dest=h.BASE/'switch_reference_v1';dest.mkdir(exist_ok=False);shutil.copyfile(__file__,dest/'driver.py')
results=[]
for corrected in [False,True]:
    deck=h.power(11.4,.935,False)
    deck=deck.replace('S20 sw src gate 0 NSW',f'VSWI sw mos 0\nS20 mos src gate {"src" if corrected else "0"} NSW').replace('DBODY src sw BODY','DBODY src mos BODY').replace('COSS sw src 150p','COSS mos src 150p')
    deck=deck.replace('i(vdprobe)\nquit','i(vdprobe) v(mos) i(vswi)\nquit')
    name='control_vgs' if corrected else 'control_ground'
    r=h.run(dest,name,'Instrument identical binary switch; compare gate-to-source against historical gate-to-ground control',deck,.003,'power',dict(control_reference='src' if corrected else 'GND'))
    if r['execution']=='PASS':
        t,v=h.loadwave(dest/name/'waves.txt');late=t>.0025
        r['stress_diagnostic']={}
        for key,z in [('VGS_V',v('v(gate)')-v('v(src)')),('VDS_V',v('v(mos)')-v('v(src)')),('MOS_current_A',v('i(vswi)'))]:
            r['stress_diagnostic'][key]=dict(min=float(z.min()),max=float(z.max()),late_rms=float(np.sqrt(np.trapezoid(z[late]**2,t[late])/(t[late][-1]-t[late][0]))))
        h.dump(dest/name/'stress_diagnostic.json',r['stress_diagnostic'])
    results.append(r)
h.dump(dest/'results.json',results)
