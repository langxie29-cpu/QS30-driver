from r4lib import *
import runner,re,numpy as np
def frozen(case):
 r=next(r for r in json.loads((R3/'evidence/execution_ledger.json').read_text(encoding='utf8'))['records']if r['case']==case)
 return(R3/r['path']/'circuit.cir').read_text(encoding='ascii')
BASEMODELS={n:MODELS/n for n in ['controller.sub','st.lib','diode.lib','ss14.lib']}
SIC=HERE/'.local/ST_SiC_official/ST_SILICON_CARBIDE_SCHOTTKY_V13.LIB'
UCC=ORIGINAL/'sources/sprint06/UCC27511_unencrypted/unpacked/UCC27511_TRANS.LIB'
def measure(p,case,result):
 r=dict(case=case,execution=result,classification='INCONCLUSIVE',scope='Finite diagnostic only; all safety/manufacturing HOLD retained')
 log=(p/'circuit.log').read_bytes()if(p/'circuit.log').exists()else b''
 text=log.decode('utf-16-le'if log.startswith(b'L\0')else'utf8',errors='replace')
 if result['rc']not in(0,None):
  r['classification']='MODEL_FAIL'if any(s in text.lower()for s in ['syntax','unknown','undefined','table'])else'SOLVER_FAIL'
 elif result['rc']is None:r['classification']='EXECUTION_FAIL'
 elif result['endpoint_s']is not None:
  c=native(p/'circuit.raw');t=c['time'];r['IL_peak_A']=float(np.max(c['i(lpower)']))if'i(lpower)'in c else None
  if case.startswith('sic'):
   w=(t>=1.02e-6)&(t<=1.10e-6);r.update(SENSE_peak_V=float(np.max(c['v(sense)'])),shunt_abs_peak_A=float(np.max(abs(c['i(rsrc)']))),Dreverse_peak_A=float(max(0,-np.min(c['i(drec)'][w]))),Dreverse_voltage_peak_V=float(np.max(c['v(hv)']-c['v(drain)'])),Dnegative_port_charge_C=float(np.trapezoid(np.maximum(-c['i(drec)'][w],0),t[w])),VGS_min_V=float(np.min(c['v(gate)']-c['v(src)'])),VGS_max_V=float(np.max(c['v(gate)']-c['v(src)'])))
   r['qualification']='Typical model mechanism comparison; factorySiC model has noBV/avalanche; no hardware/SOA PASS'
  elif case.startswith('energy'):
   r['classification']='ELECTRICAL_FAIL'if r['IL_peak_A']>3.1 else'INCONCLUSIVE';r['I_input_peak_A']=float(np.max(-c['i(vinput)']));r['scope']='Stiffsource, NEVER shut off. Intentional charged low-voltage capacitor diagnostic; noCOUT discharge, no controller or eFuse guarantee, linearL cold only'
  elif case.startswith('cap'):
   r.update(final_window=stats(c,.10,.12),peak_V=float(np.max(c['v(hv)'])),SENSE_peak_V=float(np.max(c['v(sense)'])),min_SENSE_V=float(np.min(c['v(sense)'])))
   w=r['final_window'];ok=164.9<=w['mean']<=175.1 and w['pp']<=1 and r['peak_V']<=180 and r['SENSE_peak_V']<=.3
   r['output_only_status']='LIMITED_PASS'if ok else'ELECTRICAL_FAIL';r['scope']='Only capacitor assembly changed in R3 favorable parametricfront/internal7.2drive. Actualnew12Vbuffer/front/bleed assembly NOT qualified'
  elif case.startswith('ucc'):
   r.update(VGS_min_V=float(np.min(c['v(gate)']-c['v(src)'])),VGS_max_V=float(np.max(c['v(gate)']-c['v(src)'])))
   r['scope']='Ideal12V and7.2V are LOCAL TEST STIMULI ONLY, not realrail/fullsystem PASS'
  del c
 dump(HERE/'evidence/measurements'/(p.name+'.json'),r);return r
def main():
 results=[]
 # Only proposed rectifier changes. Original source model byte-for-byte.
 for label,step in [('sic_1ns','1n'),('sic_0p5ns','0.5n')]:
  d=frozen('cell5ps').replace('QS30 R3 localized stress cell IC89.17V IL1.4A, NOT STARTUP','QS30 R4 SiC local cell IC89.17V IL1.4A, NOT STARTUP')
  d=d.replace('.include diode.lib','.include diode.lib\n.include sic.lib').replace('DREC drain hv US1G','DREC drain hv STPSC4H065D')
  d=re.sub(r'(?m)^\.tran .*$',f'.tran {step} 1.1u 0 {step} uic',d)
  p,r=runner.run(label,d,dict(BASEMODELS,**{'sic.lib':SIC}),1.1e-6,120,'SiC eliminates stored minority-carrier recovery but retains junction displacement','Original factoryrectifier model only; half-step case changesmaxstep',[[1.02e-6,1.10e-6]],'Local precharged cell, not systemstartup/SOA. NoBV infactorySiC model; no avalanche qualification');results.append(measure(p,label,r))
 # One finite original driver macro compatibility/function test, no edits on failure.
 d=frozen('cell5ps').replace('.include diode.lib','.include diode.lib\n.include ucc.lib')
 d=d.replace('RG out gate 22','RGU outh gate 22\nRGD outl gate 22\nXDRV logic 0 0 vdd outh outl UCC27511_TRANS\nVBIAS vdd 0 12')
 d=re.sub(r'(?m)^VDRIVE .*$', 'VLOGIC logic 0 PWL(0 0 1u 0 1.02u 7.2 3u 7.2 3.02u 0)',d)
 d=re.sub(r'(?m)^\.tran .*$','.tran 1n 4u 0 1n uic',d).replace('I(RG)','I(RGU) I(RGD)')
 p,r=runner.run('ucc_driver_local',d,dict(BASEMODELS,**{'ucc.lib':UCC}),4e-6,120,'Original UCC27511 accepts7.2Vlogic and drives gate from12V local stimulus','Added unmodified driver macro; no complete realrail claim',[[2e-6,2.9e-6]],'Ideal12V localstimulusONLY; nofullsystemPASS; do notedit vendor model onparserfailure');results.append(measure(p,'ucc_driver_local',r))
 # Conservative source remains on forever; no convenient protective delay or ideal cut.
 for location in ['after','before']:
  post='47u'if location=='after'else'1n';pre='1n'if location=='after'else'47u'
  d=f'''QS30 R4 isolated low-voltage stored-energy cell NOT COLDSTART OR SYSTEM QUALIFICATION
.include diode.lib
VINPUT supply 0 26.4
RINPUT supply bulk .1
CBULK bulk 0 {pre} Rser=.05 IC=26.4
RLIMIT bulk in 12.4
CPOST in 0 {post} Rser=.05 IC=26.4
LPOWER in sw 135u Rser=.16 IC=0
DREC sw fault US1G
RFAULT fault 0 .01
.temp 25
.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear plotwinsize=0 numdgt=15 threads=1
.tran 10n 200u 0 10n uic
.save V(*) I(*)
.end
'''
  label='energy47_'+location+'_R'
  p,r=runner.run(label,d,{'diode.lib':MODELS/'diode.lib'},200e-6,120,'Storage behind a resistor bypasses its input current bound; moving it before the resistor changes this','47uF position only; complementary1nF explicit residual, both capacitorIC26.4V',[[0,200e-6]],'Lowvoltagechargedcell, noCOUT. Stiffinput NEVERcuts;12.4ohmresearchonly, notproductioncomponent. LinearL not hot bound');results.append(measure(p,label,r))
 # Single assembly change: new capacitor, retain R3 bleed and all other circuitry.
 d=frozen('front24_fast').replace('COUT hv 0 20.3u Rser=.1 IC=0','C11 hv 0 10u Rser=.0109 Lser=24n IC=0\nC12 hv 0 10u Rser=.0109 Lser=24n IC=0\nCMOD hv 0 300n Rser=.1 IC=0').replace('I(COUT)','I(C11) I(C12) I(CMOD)')
 p,r=runner.run('cap_only_baseline_120ms',d,BASEMODELS,.12,600,'New450VfilmtypicalRLC changes ripple and startup, not frontend credibility','Outputcapacitor assembly only; ORIGINAL R3 bleed unchanged',[[.10,.12]],'COUT0,genuineLT3757A internallybiased7.2. R3favorableparamfront andMOSdriveunqualified. Not fullR4 proposedhardware; C ESR/ESLtyp70C10k, no max guarantee');results.append(measure(p,'cap_only_baseline_120ms',r))
 dump(HERE/'evidence/measurement_index.json',results)
 print(json.dumps([dict(case=r['case'],classification=r['classification'],output_only_status=r.get('output_only_status'))for r in results]),flush=True)
if __name__=='__main__':main()
