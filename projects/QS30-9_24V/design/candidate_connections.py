"""Emit review-only pin table. Intentionally has no native schematic/BOM exporter.
These are unapproved candidates; never import them into the legacy generator.
"""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 rows=[]
 def pins(ref,mpn,mapping,layer,note=''):
  for pin,(signal,net) in mapping.items():
   rows.append(dict(ref=ref,mpn=mpn,pin=pin,pin_name=signal,net=net,layer=layer,route_note=note,review_status='UNREVIEWED_CANDIDATE_NOT_NATIVE'))
 def passive(ref,mpn,a,b,layer,note=''):
  pins(ref,mpn,{'1':('1',a),'2':('2',b)},layer,note)
 for ref,vin,out,rtn,lim,shdn in [('U100','VIN_RAW','24P','RTN100','ILIM100','SHDN100'),('U101','24P','HV_IN24','RTN101','ILIM101','HV_PERMIT_UNRESOLVED')]:
  m={'8':('IN',vin),'9':('IN',vin),'10':('UVLO',ref+'_UV'),'12':('OVP',ref+'_OV'),'13':('MODE',ref+'_NC_MODE'),'14':('SHDN',shdn),'15':('RTN',rtn),'17':('GND','GND'),'18':('IMON',ref+'_NC_IMON'),'19':('ILIM',lim),'20':('dVdT',ref+'_DVDT'),'22':('FLT',ref+'_FLT'),'23':('OUT',out),'24':('OUT',out),'EP':('PAD',rtn)}
  for p in list(range(1,8))+[11,16,21]: m[str(p)]=('NC',ref+'_NC_'+str(p))
  pins(ref,'TPS26601RHFR',m,'L0','RTN is not interchangeable with system GND; hardware permit driver not implemented')
  for suffix,value,a,b in [('UVT','160k' if ref=='U100' else '150k',vin,ref+'_UV'),('UVB','10k',ref+'_UV',rtn),('OVT','240k',vin,ref+'_OV'),('OVB','10k',ref+'_OV',rtn),('ILIM','12k' if ref=='U100' else '20k',lim,rtn)]:
   passive('R_'+ref+'_'+suffix,'VALUE_ONLY_MPN_PENDING:'+value,a,b,'L0')
  passive('C_'+ref+'_DVDT','VALUE_ONLY_MPN_PENDING:47n',ref+'_DVDT',rtn,'L0')
 passive('R_U101_OFF','VALUE_ONLY_MPN_PENDING:10k','HV_PERMIT_UNRESOLVED','RTN101','L0','Default OFF; no direct MCU bypass')
 passive('F100','0451001.MRL','J24_POS','VIN_RAW','L0')
 passive('D100','SMBJ33CA-E3/52','VIN_RAW','GND','L0','Bidirectional, pin names not polarity')
 passive('C100','EEUFR1J470','24P','GND','L0','Polarized bulk goes after reverse protection')
 passive('C101','GRM188R72A104KA35D','VIN_RAW','GND','L0')
 for ref,out,ind in [('U110','AUX12','MSS1260-104MLD'),('U120','EXT5','MSS1260-333MLD')]:
  pins(ref,'LMR51610XDBVR',{'1':('CB',ref+'_CB'),'2':('GND','GND'),'3':('FB',ref+'_FB'),'4':('EN','24P'),'5':('VIN','24P'),'6':('SW',ref+'_SW')},'L1' if ref=='U110' else 'L2')
  passive('L_'+ref,ind,ref+'_SW',out,'L1/L2')
  passive('CB_'+ref,'VALUE_ONLY_MPN_PENDING:100n',ref+'_CB',ref+'_SW','L1/L2')
  passive('R_'+ref+'_FBT','VALUE_ONLY_MPN_PENDING:'+('140k' if ref=='U110' else '52.3k'),out,ref+'_FB','L1/L2')
  passive('R_'+ref+'_FBB','VALUE_ONLY_MPN_PENDING:10k',ref+'_FB','GND','L1/L2')
 pins('U111','TPS22810DBVR',{'1':('VIN','AUX12'),'2':('GND','GND'),'3':('EN','DRV_PERMIT_UNRESOLVED'),'4':('CT','DRV_CT'),'5':('QOD','DRV_QOD'),'6':('VOUT','DRV12')},'L1')
 passive('R_U111_OFF','VALUE_ONLY_MPN_PENDING:10k','DRV_PERMIT_UNRESOLVED','GND','L1')
 passive('C_U111_CT','VALUE_ONLY_MPN_PENDING:10n','DRV_CT','GND','L1')
 passive('R_U111_QOD','VALUE_ONLY_MPN_PENDING:1k','DRV_QOD','DRV12','L1')
 pins('U121','TPS2116DRLR',{'1':('GND','GND'),'2':('VOUT','5V_SYS'),'3':('VIN1','EXT5'),'4':('PR1','MUX_PR1'),'5':('MODE','EXT5'),'6':('VIN2','USB_VBUS'),'7':('VOUT','5V_SYS'),'8':('ST','MUX_ST')},'L2')
 passive('R_MUX_TOP','VALUE_ONLY_MPN_PENDING:316k','EXT5','MUX_PR1','L2')
 passive('R_MUX_BOT','VALUE_ONLY_MPN_PENDING:100k','MUX_PR1','GND','L2')
 pins('U122','TPS62162DSGR',{'1':('PGND','GND'),'2':('VIN','5V_SYS'),'3':('EN','5V_SYS'),'4':('AGND','GND'),'5':('FB','GND'),'6':('VOS','3V3'),'7':('SW','3V3_SW'),'8':('PG','P3V3_PG'),'EP':('PAD','GND')},'L2')
 passive('L122','MSS1260-222NLD','3V3_SW','3V3','L2')
 pins('U20','UCC28C43DR',{'1':('COMP','COMP_UNQUALIFIED'),'2':('FB','FB_HV'),'3':('CS','CS_FILTER'),'4':('RTCT','RT_CT'),'5':('GND','GND_HV'),'6':('OUT','GATE_DRIVE'),'7':('VDD','AUX12'),'8':('VREF','VREF_PWM')},'L3','Pin5/CT/CS return use dedicated Kelvin traces to R230 pad2; not SW or digital return')
 pins('Q20','STP9NK50Z',{'1':('G','HV_GATE'),'2':('D','SW_HV'),'3':('S','CS_SHUNT'),'TAB':('D','SW_HV')},'L3')
 pins('D20','US1G-E3/61T',{'A':('A','SW_HV'),'K':('K','HV_BUS')},'L3','Logical A/K; physical pad numbering requires footprint review')
 for ref,mpn,a,b,note in [
  ('L20','MSS1260-154KLD','HV_IN24','SW_HV','150uH'),
  ('R230','RL2512FK-070R82L','CS_SHUNT','GND_HV','Power pads with independent Kelvin pickup at each pad'),
  ('R36','RC0603FR-07100RL','CS_SHUNT','CS_FILTER','Kelvin positive, never SW'),
  ('CCS','GRM1885C1H221JA01D','CS_FILTER','GND_HV','Kelvin negative'),
  ('RT','RC0603FR-0715K4L','VREF_PWM','RT_CT','15.4k'),
  ('C9','GRM1885C1H102JA01D','RT_CT','GND_HV','1n C0G'),
  ('R34A','TNPW12061M00BEEA','HV_BUS','FB_HV_MID','1M 0.1%'),
  ('R34B','TNPW12061M00BEEA','FB_HV_MID','FB_HV','1M 0.1%'),
  ('R35A','TNPW060329K4BEEA','FB_HV','FB_HV_LOW','29.4k 0.1%'),
  ('R35B','TNPW0603453RBEEA','FB_HV_LOW','GND_HV','453ohm 0.1%'),
  ('RG','VALUE_ONLY_MPN_PENDING:22ohm','GATE_DRIVE','HV_GATE','gate source return geometry pending'),
  ('RGS','VALUE_ONLY_MPN_PENDING:10k','HV_GATE','CS_SHUNT','default discharge'),
  ('C11','ECQE2106JF','HV_BUS','GND_HV','10u/250V'),('C12','ECQE2106JF','HV_BUS','GND_HV','10u/250V')]: passive(ref,mpn,a,b,'L3',note)
 # Decoupling, protection, compensation and enable-driver completeness intentionally not asserted.
 dest=ROOT/'netlist/candidate_power_pins.csv';dest.parent.mkdir(exist_ok=True)
 with dest.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 meta={'schema_version':1,'status':'UNREVIEWED_CANDIDATE','approved_for_native_generation':False,'rows':len(rows),'scope':'Power core pin candidates only; not complete assembly netlist','missing':['decoupling and passive MPN completion','hardware PG and permit drivers','OVP/OC latch/reset','COMP/soft-start/ramp','USB current protocol/ESD paths','module/MCU full netlist'],'native_export_policy':'Refuse native output until reviewed connection set and all required approvals/qualification evidence exist'}
 (ROOT/'netlist/candidate_power_pins.meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
 print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
