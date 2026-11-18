"""Independent principal interval calculations. UNKNOWN is not replaced by a convenient time."""
from r4lib import *
import math,itertools,csv
def limits(vref,rt,rb,vtol=.01,rtol=.01):
 return(vref*(1-vtol)*(1+rt*(1-rtol)/(rb*(1+rtol))),vref*(1+vtol)*(1+rt*(1+rtol)/(rb*(1-rtol))))
def main():
 capmax=2*10e-6*1.10+.3e-6*1.05;bleed=3*49.9e3;hv=195.;ln=math.log(195/60)
 temp=[]
 # Analytic NTC model from specified R25/B tolerance. Not actual thermal lag or full table fit.
 for r25,b,v5,rt,vth in itertools.product([9500,10500],[3977*.9925,3977*1.0075],[4.85,5.15],[12000*.99,12000*1.01],[.396,.404]):
  # Highwindow divider90.9k+10k alsoloadsNTC in parallel.
  rparallel=rt*vth/(v5-vth);rntc=1/(1/rparallel-1/100900)
  temp.append(1/(1/298.15+math.log(rntc/r25)/b)-273.15)
 v5nom=1.193*(1+319e3/100e3)
 summary=dict(utc=utc(),OVP_trip_V=limits(.4,400e3,860),residual_trip_V=limits(.4,660e3,4700),branch_off_trip_V=limits(.4,30100,10000),bias12_supervisor_trip_V=limits(.405,261000,10000),raw24_supervisor_trip_V=limits(.405,475000,10000),bias12_nominal_V=1.2*(1+453e3/49900),bias5_nominal_V=v5nom,feedback_nominal_1p91k_V=1.6*(1+200000/1910),feedback_conservative_1p568_1p632_0p1pct_V=[1.568*(1+200000*.999/(1910*1.001)),1.632*(1+200000*1.001/(1910*.999))],new_cap_voltage_at105C_V=450*(1-.0133*20),cap_ESR_70C10k_typ_ohm_each=.0109,cap_ESL_typ_H_each=24e-9,cap_RMS_70C10k_A_each=8,cap_max_initial_plus_optional_module_F=capmax,bleed_nominal_string_ohm=bleed,bleed_single_string_open_195_to60_s=bleed*1.01*capmax*ln,bleed_1pct_and100ppm_100C_single_open_s=bleed*(1.01+.0075)*capmax*ln,bleed_total_power_170_W=170**2/(bleed/2),bleed_total_power_195_W=195**2/(bleed/2),bleed_resistor_one_short_max_W=(195/(2*49900*.99))**2*(49900*.99),bleed_CRCW2512_linear_derated_power_at100C_W=1*(155-100)/(155-70),bleed_CRCW2512_max_working_V=500,temperature_trip_model_C=[min(temp),max(temp)],temperature_scope='ElectricalNTC R25/B window only; cable/thermalhotspotlag and sensoradhesion UNKNOWN,100Cengineeringlimitunchanged',LM5069_stable_Ilim_A=[.0485/(.05*1.01),.0615/(.05*.99)],LM5069_breaker_threshold_A=[.080/(.05*1.01),.130/(.05*.99)],LM5069_timer_component_s=[3.76*9e-9/120e-6,4.16*11e-9/51e-6],LM5069_total_cutoff_max_s='UNKNOWN (12us TIMER->GATE typical;1.2us breaker unloaded/VIN48condition; actualpassFET absent)',R12p4_cold_passive_Vmax_over_Rmin_A=26.4/(12.4*.99),R12p4_continuous_short_power_W=26.4**2/(12.4*.99),R12p4_max_deliverable_power_at21p6_V_W=21.6**2/(4*12.4*1.01),R33_max_deliverable_power_at21p6_V_W=21.6**2/(4*33*1.05),normal_inductor_copper_from_R3_RMS25C_W=.407808**2*.159,source_constant_fault_energy_upper_bound_J='UNBOUNDED without source/time/thermal qualification',scope='Independent interval arithmetic; any assumedtolerance marked, no actualL(I,T), parasitic/fastcut ormanufacturingPASS')
 dump(HERE/'evidence/independent_calculations.json',summary)
 rows=[]
 def energy(zone,components,cap,volt,energyJ,path,classification,gap):rows.append(dict(zone=zone,components=components,maximum_C_F=cap,maximum_V_V=volt,stored_energy_J=energyJ,fault_release_path=path,classification=classification,remaining_gap=gap))
 cin=2*2.2e-6*1.1
 energy('U100前/辅助输入','CAIN1+CAIN2 via DA1',cin,26.4,.5*cin*26.4**2,'rawinput/biasconverter fault; not directlyL unlessadditionalfailure','INCONCLUSIVE','C tolerance/DCbias andsourceinrush/F100 I2t coordination; rawinputsourcecontinuousenergy unbounded')
 cb=47e-6*1.2+.1e-6*1.1
 energy('U100至U101','C100+C111',cb,26.4,.5*cb*26.4**2,'V24P->R111->Q101->L20->D20/outputshort orQ20short','INCONCLUSIVE','Q101notselected/loadedoffmaxunknown; +20%C100assumption; allactualstorageincludingprobesmustenumerate')
 energy('U101后全部LV储能','No fittedbulk atL_FEED; Q101Coss/PCB/probe/TVS', 'UNKNOWN','26.4 envelope','UNKNOWN','L_FEEDcap->L20->fault bypasses U101sense/pass control','INCONCLUSIVE','No zeroC assumption. Need maximumremainingC/Eossinclmeasurementfixture + actualhotL')
 for value in [1e-6,47e-6]:energy('R3反例',str(value)+'F afterU101',value,26.4,.5*value*26.4**2,'Aftercutstorage directtoL even if upstreamswitchoff','ELECTRICAL_FAIL','R3observed3.578762/14.171475A,25C10pctLdrop screening; not damagecurrent')
 energy('Boost电感','L20 normal peak1.65A at165u sensitivity','N/A','N/A',.5*165e-6*1.65**2,'L->D20->HV afterPWMoff; saturationfaultenergynotlinear','INCONCLUSIVE','L(I,T)unknown; energycalculationonlywithinlinearassumption')
 energy('高压输出','2xB32774D4106K000 + optional300nmodule',capmax,195,.5*capmax*195**2,'COUT->externalorinternalshort/return, doesNOT traverselowvoltageeFuse','INCONCLUSIVE','ESR/ESL minimum andshortloopL unknown, no guaranteedpeak; touchprotectedinterface andpulsepathstillHOLD')
 energy('12V控制与门驱','CAOUTx2/CALDOIN/CDRV/CVIN etc','Enumerated in nativeBOM','12.6 planning envelope','UNKNOWN','Controller/gatedriver supply, reverse/partialpower paths; distinctfromL_FEED','INCONCLUSIVE','ExacteffectiveC andallrailfaultsnotqualified; notcountedaszeroorallowedL_FEEDbulk')
 energy('持续输入','External24Vsource','N/A',26.4,'NO FINITE BOUND','Q101stuckon orno effectivecut continuesfeedingfault','INCONCLUSIVE','Do not substituteTYP triptime orfuse nominal1A for finiteenergyguarantee')
 energy('故障开关与返回','Q101/Q20/D20/COUT returncopper','UNKNOWN','UNKNOWN','UNKNOWN','Different faultloops mustbeexaminedseparately','INCONCLUSIVE','No infiniteSOA/zeroESL/ideal0delaycredit; noPCBextraction yet')
 with(HERE/'FAULT_ENERGY_BUDGET.csv').open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps({k:summary[k]for k in ['OVP_trip_V','new_cap_voltage_at105C_V','bleed_single_string_open_195_to60_s','temperature_trip_model_C','feedback_nominal_1p91k_V','LM5069_timer_component_s']}))
if __name__=='__main__':main()
