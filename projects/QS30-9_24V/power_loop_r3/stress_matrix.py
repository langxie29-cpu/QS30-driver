from analyze import *
import csv,json
def main():
 ms=json.loads((HERE/'evidence/final_metrics_index.json').read_text());by={m['case']:m for m in ms};n=by['front24_fast'];cell=by['cell5ps'];f=by['front26p4_short47u'];f1=by['front26p4_short1u'];rows=[]
 def row(ref,mpn,scenario,qty,value,unit,basis,limit,status,gap):rows.append([ref,mpn,scenario,qty,value,unit,basis,limit,status,gap])
 # Maxima from each finite scenario are never labelled device-global upper bounds.
 for m in ms:
  if not m['case'].startswith('front') or 'i(lpower)' not in m:continue
  name=m['case'];scope='25C parameter-front native study '+name
  row('L20','MSS1583-154KED',name,'IL_peak',m['i(lpower)']['max'],'A',scope,'25C10pctLdrop3.1A;hot unknown',m['classification'] if 'short' in name else 'INCONCLUSIVE','L(I,T)/coreloss missing;150u linear invalid beyond source drop domain')
  row('D20','US1G-E3/61T',name,'forward_peak',m['i(drec)']['max'],'A',scope,'1A average and30A8.3ms single halfsine not ns repetitive rating','INCONCLUSIVE','recovery/surge waveform/thermal')
  row('D20','US1G-E3/61T',name,'reverse_peak',-m['i(drec)']['min'],'A',scope,'no fullwaveform Qrr maximum in datasheet','INCONCLUSIVE','temperature/test-condition mismatch')
  row('D20','US1G-E3/61T',name,'reverse_voltage',-m['diode_anode_minus_cathode_V']['min'],'V',scope,'VRRM400V','INCONCLUSIVE','actual PCB parasitics and repetitive breakdown')
  row('U101','TPS26601RHFR',name,'pass_peak_power',m['frontend_power_W']['max'],'W',scope,'no guaranteed max trip/thermal pulse boundary','INCONCLUSIVE','BPASS instantaneous regulation favorable;not vendor behavior')
  row('U101','TPS26601RHFR',name,'pass_integral',m['frontend_signed_energy_J'],'J',scope,'must compare actual pulse SOA/thermal trajectory','INCONCLUSIVE','no lifetime/thermal qualification from finite study')
  row('COUT','2xECQE2106JF + module emulator',name,'current_peak_abs',max(abs(m['i(cout)']['min']),abs(m['i(cout)']['max'])),'A',scope,'ripple and pulse current bound not established','INCONCLUSIVE','short discharge largely in fault switch/return;not MOS drain current')
  row('COUT','2xECQE2106JF + module emulator',name,'voltage_peak',m['v(hv)']['max'],'V',scope,'250V85C,187.5V105C','INCONCLUSIVE','actualcapacitor temperature/ESR/lifetime')
  row('Q20','STP9NK50Z',name,'external_VDS_range',f'{m["MOS_VDS_external_V"]["min"]:.9g}..{m["MOS_VDS_external_V"]["max"]:.9g}','V',scope,'500V plus reversebodydiode/pulse conditions','INCONCLUSIVE','positive/negative instantaneous stress not same as intrinsic')
  row('Q20','STP9NK50Z',name,'external_drain_peak_abs',max(abs(m['MOS_external_drain_current_A']['min']),abs(m['MOS_external_drain_current_A']['max'])),'A',scope,'IDM28.8A SOAlimited;not standalonerating','INCONCLUSIVE','actualSOA/thermal and packageparasitics')
  row('RSRC','value-only;WSL2512R0620FEA candidate',name,'I2R_peak',m['shunt_power_W']['max'],'W',scope,'candidate1W70C not pulse permission','INCONCLUSIVE','Kelvin/TCR/pulse/repetition')
 # Normal versus local stress and fault use different supplies and initial energies.
 for m,label in [(n,'joint0to120ms_7p2V_LDO'),(cell,'local89p17V_1p4A_12Vdrive_singleedge')]:
  for key,qty,unit in [('MOS_VDS_external_V','externalVDS','V'),('MOS_VGS_external_V','externalVGS','V'),('MOS_external_drain_current_A','externalDrainCurrent','A'),('MOS_external_source_current_A','externalSourceCurrent','A'),('MOS_external_gate_current_A','externalGateCurrent','A')]:
   v=m[key];row('Q20','STP9NK50Z',label,qty+'_minmax',f'{v["min"]:.9g}..{v["max"]:.9g}',unit,m['path'],'500V VDS;VGS+/-30V;IDM28.8A SOAlimited','INCONCLUSIVE','pulseV/Icoincidence,Tj,negativeVDS/bodydiode and actual parasitics')
  row('Q20','STP9NK50Z',label,'signed_external_terminal_mean',m['MOS_terminal_power_W']['mean'],'W',m['path'],'signed terminal power includes stored energy','INCONCLUSIVE','not intrinsic thermal dissipation;not repetitiveEAS')
  row('RSRC','value-only;WSL2512R0620FEA candidate',label,'I2R_peak',m['shunt_power_W']['max'],'W',m['path'],'candidate1W70C DC not arbitrary pulse guarantee','INCONCLUSIVE','exactoriginalMPN absent,pulse/TCR/inductance')
  row('RSRC','value-only;WSL2512R0620FEA candidate',label,'I2R_time_mean',m['shunt_power_W']['mean'],'W',m['path'],'1W candidate only','INCONCLUSIVE','finite waveform mean not junction or pulse qualification')
  row('XNEG/RNEG','originalSS14_model/2ohm',label,'RNEG_peak_current',max(abs(m['i(rneg)']['min']),abs(m['i(rneg)']['max'])),'A',m['path'],'SS14exactMPN repeated pulse and resistor pulse missing','INCONCLUSIVE','gate clamp shares source/sense return transient')
 row('D20','US1G-E3/61T','local5ps','negative_terminal_charge',cell['diode_negative_terminal_charge_C']*1e9,'nC','fixed1.02..1.10us includes displacement','trr50ns IF.5A IR1A Irr.25A does not bound thisQ','INCONCLUSIVE','not pure minoritycarrier Qrr or max datasheet recovery charge')
 for key in ['MOS_intrinsic_VDS_V','MOS_intrinsic_VGS_V']:
  v=cell[key];row('Q20','STP9NK50Z','local5ps',key,f'{v["min"]:.9g}..{v["max"]:.9g}','V','explicit saved internal nodes','500V/+/-30V with transient/SOA conditions','INCONCLUSIVE','isolated sample extrema differ with10ps;unvalidated internal excursions')
 row('Q20','STP9NK50Z','repetitiveavalanche','energy_budget','UNKNOWN','J/cycle','EAS190mJ is single25C pulse;IAR7.2A TJlimited','cannot apply singleEAS repetitively','INCONCLUSIVE','separate avalanche branch/current/Tj not established')
 row('Q20','STP9NK50Z','hotfullpower','junction_temperature','UNKNOWN','degC','25Conlymodel','TJmax150C;Tc100CID4.5A;SOA curvesTc25C','INCONCLUSIVE','actual thermal path and7.2V RDSon maximum absent')
 row('L20','MSS1583-154KED','joint0to120ms','copper25C_est',n['inductor_copper25_est_W'],'W','timeRMS^2*.16','Irms1.55/2.2A are20/40C rise atspecifiedtest','INCONCLUSIVE','coreloss/hotcurrent/ambienttemperature andmounting missing')
 row('L20','MSS1583-154KED','joint0to120ms','copper100C_est',n['inductor_copper100_est_W'],'W','Cu alpha.00393 only','maxpart125C not an allowedambient','INCONCLUSIVE','DCR scaling not thermal solution')
 row('RF/CF','22ohm/4.7nF candidates','tolerance','tau_range','97.2477..109.6557','ns','1pctR5pctC candidate','no hardRC step-delay maximum','INCONCLUSIVE','add blanking/comparator/driver,noise,actualC')
 row('COUT','ECQE2106JF','hotfault','ratedvoltage105C',187.5,'V','250V85C derate1.25pct/C','195Vdesignatedfault','ELECTRICAL_FAIL','105Ccap operation incompatible195Vrating;cap temperature must be constrained or component changed')
 row('U100/F100','TPS26601RHFR /0451001.MRL','overload_fault','I2t_and_tripmax','UNKNOWN','A2s/s','existingU10012k,F1001A,newU1018k','upstream coordination required','INCONCLUSIVE','upstreamnotmodeled, sourcecurrentlimit/fusecurve missing')
 row('OVP/latch','notimplementedfully','FBopen_fault','HV_peak_and_delay','UNKNOWN','V/s','not executed','HV<=195V designatedfault','INCONCLUSIVE','independent physical chain missing')
 row('CSNUB/RSNUB','100pF/330ohm value-only','recovery','pulsevoltage_energy','UNKNOWN','V/J','observedD20reverse near400V;nodeSN notsaved','need exactHVcap/resistor pulse ratings','INCONCLUSIVE','BOM intentionally blocks100Vcap in snubber')
 row('Controller','LT3757AEMSE#PBF candidate','biasfault','LDOjunction_and_permit','UNKNOWN','W/degC','internalnativeLDO and bias clamp study','VIN40V;INTVCC<=VIN+.3V,20V;GATE<=INTVCC+.3V','INCONCLUSIVE','rail fault transient/thermal tolerance/independentpermit')
 headers=['reference','MPN_or_candidate','scenario','quantity','maximum_provable_or_measured_value','unit','evidence_and_scope','rating_or_criterion','classification','remaining_gap']
 with (HERE/'COMPONENT_STRESS_MATRIX.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(headers);w.writerows(rows)
 print('Stress rows',len(rows))
if __name__=='__main__':main()
