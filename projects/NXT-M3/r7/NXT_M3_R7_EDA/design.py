"""R7 P1 native schematic source data. Pad numbers are physical package numbers."""
from pathlib import Path

P = 'power_in'
O = 'power_out'
I = 'input'
B = 'bidirectional'
D = 'output'
OC = 'open_collector'
X = 'no_connect'
S = 'passive'
G = 'GND'
A = 'AUX12'
V = 'V3V3'
F = 'VIN_FUSED'
M = 'VIN_PROTECTED'
H = 'HV170'
parts = []
types = {}
group = 'INPUT'

def device(ref, kind, mpn, footprint, pin_rows, url='', status='CANDIDATE', value=None):
    mapped = {str(number): (name, electrical) for number, name, electrical, net in pin_rows}
    if kind in types and types[kind] != mapped:
        raise ValueError(kind)
    types[kind] = mapped
    parts.append(dict(ref=ref, kind=kind, mpn=mpn, value=value or mpn, footprint=footprint,
                      source=url, status=status, group=group, note='',
                      pins={str(number): net for number, name, electrical, net in pin_rows}))

def passive(ref, value, a, b, footprint, mpn='TBD', status='CANDIDATE'):
    kind = ref.rstrip('0123456789')
    device(ref, kind, mpn, footprint, [(1,'1', S,a),(2,'2', S,b)], status=status, value=value)

def r(ref, value, a, b=G, package='0805_2012Metric', mpn='TBD'):
    passive(ref, value, a, b, 'Resistor_SMD:R_'+package, mpn)

def c(ref, value, a, b=G, package='0805_2012Metric', mpn='TBD'):
    passive(ref, value, a, b, 'Capacitor_SMD:C_'+package, mpn)

def connector(ref, nets, footprint, value, mpn='TBD', status='CANDIDATE'):
    device(ref, 'Conn'+str(len(nets)), mpn, footprint,
           [(i,str(i), S,net) for i,net in enumerate(nets,1)], status=status, value=value)

def flag(ref, net):
    device(ref, 'FLAG', 'Power source declaration', '', [(1,'PWR',O,net)])

TI = 'https://www.ti.com/lit/ds/symlink/'
ADI = 'https://www.analog.com/media/en/technical-documentation/data-sheets/LT3757-3757A.pdf'
MICROCHIP = 'https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/20005854A.pdf'
ST = 'https://www.st.com/resource/en/datasheet/'
SO8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
SOT6 = 'Package_TO_SOT_SMD:SOT-23-6'
PIN2 = 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
PIN3 = 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'
TERM2 = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
TERM3 = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal'

connector('J1',['VIN_RAW',G],TERM2,'12V DC IN','1715721')
passive('F1','1A fuse candidate','VIN_RAW',F,'Fuse:Fuse_1206_3216Metric','0467001.NR')
passive('D1','17V bidirectional TVS',F,G,'Diode_SMD:D_SMB','SMBJ17CA-E3/52')
flag('#FLG01', F)
flag('#FLG02', G)
flag('#FLG03', 'FUSE_RTN')
unused = {1,2,3,4,5,6,7,11,16,18,21}
functions = {
    8:('IN',P,F),9:('IN',P,F),10:('UVLO',I,'IN_UV'),12:('OVP',I,'IN_OV'),
    13:('MODE',I,'FUSE_MODE'),14:('SHDN',I,'FUSE_EN'),15:('RTN',P,'FUSE_RTN'),
    17:('GND',P,G),18:('IMON',D,None),19:('ILIM',S,'ILIM'),20:('dVdT',S,'RAMP'),
    22:('FLT',OC,'EFUSE_FLT_N'),23:('OUT',O,M),24:('OUT_PARALLEL',S,M),25:('EP_RTN',P,'FUSE_RTN')
}
device('U1','TPS26600','TPS26600RHFR',
       'Package_DFN_QFN:Texas_RHF0024A_VQFN-24-1EP_4x5mm_P0.5mm_EP2.65x3.65mm',
       [(n,*functions.get(n,('NC',X,None))) for n in range(1,26)],TI+'tps2660.pdf')
passive('R1','68k',F,'IN_UV','Resistor_SMD:R_0805_2012Metric')
r('R2','10k','IN_UV')
r('R3','118k',F,'IN_OV')
r('R4','10k','IN_OV')
r('R5','20k 1%','ILIM')
r('R6','47k','FUSE_EN')
r('R7','10k',V,'EFUSE_FLT_N')
c('C1','1u 50V',F)
c('C2','10n','RAMP')
c('C3','1u 50V',M)
r('R8','402k 1% latch mode','FUSE_MODE','FUSE_RTN')
r('R9','10k','RUN_QN','FUSE_EN')

group = 'BIAS'
device('D2','DIODE','US1G-E3/61T','Diode_SMD:D_SMA',
       [(1,'K',S,'BIAS_IN'),(2,'A',S,F)],'https://www.vishay.com/docs/88794/us1a.pdf')
flag('#FLG04','BIAS_IN')
device('U2','TPS7A1601','TPS7A1601DGNR','Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm',
       [(1,'OUT',O,V),(2,'FB',I,'LDO_FB'),(3,'PG',OC,None),(4,'GND',P,G),
        (5,'EN',I,'BIAS_IN'),(6,'NC',X,None),(7,'DELAY',S,None),(8,'IN',P,'BIAS_IN'),
        (9,'EP',P,G)],TI+'tps7a1601.pdf')
r('R10','178k 1%',V,'LDO_FB')
r('R11','100k 1%','LDO_FB')
c('C4','1u 50V','BIAS_IN')
c('C5','4.7u 16V',V)
device('U3','TMR1212','TMR 1-1212','NXT_M3:TRACO_TMR1_SIP6_SINGLE',[
    (1,'-Vin',P,G),(2,'+Vin',P,M),(4,'+Vout',O,A),(6,'-Vout',S,G)],
    'https://datasheet.lcsc.com/datasheet/pdf/c27041be2e95a09c7b457df29162e8ec.pdf')
c('C6','4.7u 25V',A)

group = 'BOOST'
connector('J4',['BOOST_ARM_SRC','BOOST_EN'],PIN2,'BOOST ARM - LINK DNP',status='HOLD_DNP')
device('U4','LT3757A','LT3757AEMSE#PBF','Package_SO:MSOP-10-1EP_3x3mm_P0.5mm_EP1.68x1.88mm',
       [(1,'VC',S,'VC'),(2,'FBX',I,'FBX'),(3,'SS',S,'SS'),(4,'RT',S,'RT'),
        (5,'SYNC',I,G),(6,'SENSE',I,'SENSE'),(7,'GATE',D,'PWM_RAW'),
        (8,'INTVCC',O,'INTVCC'),(9,'SHDN_UVLO',I,'BOOST_EN'),(10,'VIN',P,M),
        (11,'EP_GND',P,G)],ADI)
device('U5','UCC27511','UCC27511DBVR',SOT6,
       [(1,'VDD',P,A),(2,'OUTH',D,'DRV_ON'),(3,'OUTL',D,'DRV_OFF'),
        (4,'GND',P,G),(5,'IN-',I,'FAULT_Q'),(6,'IN+',I,'PWM_RAW')],TI+'ucc27511.pdf')
device('Q1','NFET_TO220','STP9NK50Z','Package_TO_SOT_THT:TO-220-3_Vertical',
       [(1,'G',I,'GATE'),(2,'D',S,'SW_HV'),(3,'S',S,'FET_SOURCE')],ST+'stp9nk50z.pdf')
device('D20','DIODE','STPSC4H065D','Package_TO_SOT_THT:TO-220-2_Vertical',
       [(1,'K',S,H),(2,'A',S,'SW_HV')],ST+'stpsc4h065.pdf')
device('D21','DIODE','SS14-E3/61T','Diode_SMD:D_SMA',
       [(1,'K',S,'NEG_GATE'),(2,'A',S,'FET_SOURCE')],'https://www.vishay.com/docs/88746/ss12.pdf')
passive('L1','150uH +/-10%',M,'SW_HV','Inductor_SMD:L_Coilcraft_MSS1583-XXX','MSS1583-154KED')
passive('C20','5uF 450V film',H,G,'Capacitor_THT:C_Rect_L31.5mm_W11.0mm_P27.50mm_MKS4','B32774D4505K000')
r('R20','0.13R 1%','FET_SOURCE',G,'2512_6332Metric','WSL2512R1300FEA')
r('R21','22R','FET_SOURCE','SENSE')
c('C21','4.7n','SENSE')
r('R22','22R','DRV_ON','GATE')
r('R23','10R','DRV_OFF','GATE')
r('R24','10k','GATE','FET_SOURCE')
r('R25','2R','NEG_GATE','GATE')
r('R26','330R pulse','SW_HV','SNUB','1206_3216Metric')
device('C22','C','C1206C101JCGACTU','Capacitor_SMD:C_1206_3216Metric',
       [(1,'1',S,'SNUB'),(2,'2',S,H)],
       'https://search.kemet.com/component-documentation/download/specsheet/C1206C101JCGACTU',
       value='100p C0G 500V',status='HOLD_PULSE')
r('R27','100k 0.1%',H,'FB_MID','1206_3216Metric','TNPW1206100KBEEA')
r('R28','100k 0.1%','FB_MID','FBX','1206_3216Metric','TNPW1206100KBEEA')
r('R29','1.90k 0.1%','FBX')
r('R30','140k','RT')
r('R31','68k',M,'BOOST_ARM_SRC')
r('R32','12k','BOOST_EN')
c('C23','4.7u 16V','INTVCC')
c('C24','100n','SS')
r('R33','22k','VC','COMP')
c('C25','6.8n','COMP')
c('C26','100p','VC')
c('C27','100n 25V',A)

group = 'SAFETY'
device('U6','TPS3700','TPS3700DDCR',SOT6,
       [(1,'OUTA',OC,'BOOST_EN'),(2,'GND',P,G),(3,'INA+',I,'AUX_OK_SENSE'),(4,'INB-',I,'OVP_SENSE'),
        (5,'VDD',P,V),(6,'OUTB',OC,'OVP_PRE_N')],TI+'tps3700.pdf')
device('U7','LVC1G74','SN74LVC1G74DCUR','Package_SO:VSSOP-8_2.3x2mm_P0.5mm',
       [(1,'CLK',I,'ARM_CLK'),(2,'D',I,G),(3,'QN',D,'RUN_QN'),(4,'GND',P,G),
        (5,'Q',D,'FAULT_Q'),(6,'CLR_N',I,V),(7,'PRE_N',I,'OVP_PRE_N'),(8,'VCC',P,V)],TI+'sn74lvc1g74.pdf')
device('U8','TPS3808','TPS3808G33DBVR',SOT6,
       [(1,'RESET_N',OC,'OVP_PRE_N'),(2,'GND',P,G),(3,'MR_N',I,V),(4,'CT',S,None),
        (5,'SENSE',I,V),(6,'VDD',P,V)],TI+'tps3808.pdf')
device('Q2','2N7002','2N7002P,215',SOT23,
       [(1,'G',I,'FAULT_Q'),(2,'S',S,G),(3,'D',S,'BOOST_EN')])
connector('J5',[V,'ARM_CLK'],PIN2,'INTERNAL MOMENTARY ARM','TBD')
r('R40','10k','ARM_CLK')
r('R41','10k',V,'OVP_PRE_N')
r('R42','230k 0.1%',H,'OVP_MID','1206_3216Metric')
r('R43','230k 0.1%','OVP_MID','OVP_SENSE','1206_3216Metric')
r('R44','1k 0.1%','OVP_SENSE')
for index, midpoint in ((45,'BLEED_A'),(47,'BLEED_B')):
    r('R'+str(index),'249k 1%',H,midpoint,'1206_3216Metric','CRCW1206249KFKEA')
    r('R'+str(index+1),'249k 1%',midpoint,G,'1206_3216Metric','CRCW1206249KFKEA')
r('R49','100k 0.1%',H,'ADC_MID','1206_3216Metric','TNPW1206100KBEEA')
r('R50','100k 0.1%','ADC_MID','ADC_PRE','1206_3216Metric','TNPW1206100KBEEA')
r('R51','2.49k 0.1%','ADC_PRE')
r('R52','10k','ADC_PRE','HV_ADC')
r('R70','265k 0.1%',A,'AUX_OK_SENSE')
r('R71','10k 0.1%','AUX_OK_SENSE')
c('C40','10n','HV_ADC')
c('C41','100n',V)
c('C42','100n',V)
c('C43','100n',V)

group = 'MCU'
mcu_pins = [
 ('PB7','SER_RX',I),('PC14','FAULT_Q',I),('PC15','EFUSE_FLT_N',I),('VDD',V,P),('VSS',G,P),
 ('PF2_NRST','NRST',B),('PA0','HV_ADC',I),('PA1','BL3',D),('PA2','LE3',D),('PA3','CLK3',D),
 ('PA4','DATA3',D),('PA5','ADDR0',I),('PA6','ADDR1',I),('PA7','LED_N',D),('PB0','BUS_DE',D),
 ('PA9_PA11',None,B),('PA10_PA12',None,B),('PA13','SWDIO',B),('PA14','SWCLK',I),('PB6','SER_TX',D)]
device('U9','STM32C011F4','STM32C011F4P6','Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',
       [(index,name,kind,net) for index,(name,net,kind) in enumerate(mcu_pins,1)],ST+'stm32c011f4.pdf')
c('C50','100n',V)
c('C51','1u 10V',V)
for idx,net in enumerate(('BL3','LE3','CLK3','DATA3','BUS_DE'),53):
    r('R'+str(idx),'100k',net)
r('R58','10k',V,'ADDR0')
r('R59','10k',V,'ADDR1')
r('R60','1k',V,'LED_A')
device('D50','LED','LTST-C190KGKT','LED_SMD:LED_0603_1608Metric',[(1,'K',S,'LED_N'),(2,'A',S,'LED_A')])
connector('J6',['ADDR0',G,'ADDR1',G], 'Connector_PinHeader_2.54mm:PinHeader_2x02_P2.54mm_Vertical','ADDR STRAPS - optional shunts')
connector('J7',[V,'SWDIO',G,'SWCLK','NRST'],
          'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical','SWD, Vref only')

group = 'BUS'
device('U10','THVD1410','THVD1410DR',SO8,
       [(1,'R',D,'SER_RX'),(2,'RE_N',I,'BUS_DE'),(3,'DE',I,'BUS_DE'),(4,'D',I,'SER_TX'),
        (5,'GND',P,G),(6,'A',B,'BUS_A'),(7,'B',B,'BUS_B'),(8,'VCC',P,V)],TI+'thvd1450.pdf')
connector('J2',['BUS_A','BUS_B',G],TERM3,'RS485 A/B/GND','1715734')
connector('J3',['BUS_A','BUS_B',G],TERM3,'RS485 A/B/GND','1715734')
connector('J8',['BUS_A','BUS_TERM'],PIN2,'END TERMINATION LINK DNP',status='HOLD_DNP')
r('R65','120R 1%', 'BUS_TERM','BUS_B')
c('C52','100n',V)
device('D51','SM712','SM712-02HTG',SOT23,
       [(1,'IO1',S,'BUS_A'),(2,'IO2',S,'BUS_B'),(3,'GND',S,G)],
       'https://www.littelfuse.com/products/tvs-diode-arrays/automotive/sm712')

group = 'DRIVE'
cd = [('VCC',P,V),('ENA',I,V),('A',I,'DATA3'),('E',D,'DATA12'),('F',D,'CLK12'),
      ('B',I,'CLK3'),('ENB',I,V),('VSS',P,G),('ENC',I,V),('C',I,'LE3'),('G',D,'LE12'),
      ('NC',X,None),('H',D,'BL12'),('D',I,'BL3'),('END',I,V),('VDD',P,A)]
device('U11','CD40109B','CD40109BPWR','Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
       [(i,*row) for i,row in enumerate(cd,1)],TI+'cd40109b.pdf')
hv_func = {
    23:('DOUT',D,None),24:('NC',X,None),25:('NC',X,None),26:('NC',X,None),
    27:('POL',I,A),28:('CLK',I,'CLK12'),29:('VSS',P,G),30:('VDD',P,A),
    31:('LE',I,'LE12'),32:('DIN',I,'DATA12'),33:('BL',I,'BL12'),34:('NC',X,None)
}
for pin,channel in [*((pin,23-pin) for pin in range(1,23)),
                    *((pin,67-pin) for pin in range(35,45))]:
    hv_func[pin] = (f'HVOUT{channel}',OC,f'K{(channel-1)//10+1}_{(channel-1)%10}' if channel <= 30 else None)
device('U12','HV5622PG','HV5622PG-G','Package_QFP:Microchip_PQFP-44_10x10mm_P0.8mm',
       [(i,*hv_func[i]) for i in range(1,45)],MICROCHIP)
for idx,net in enumerate(('DATA12','CLK12','LE12','BL12'),66):
    r('R'+str(idx),'100k',net)
c('C53','100n',V)
c('C54','100n 25V',A)
c('C55','100n 25V',A)

group = 'TUBES'
for tube in range(1,4):
    anode = f'ANODE{tube}'
    p = [(1,'IC1',X,None),(2,'ANODE',S,anode)]
    for pin, digit in ((3,0),(4,9),(5,8),(6,7),(7,6),(9,5),(10,4),(11,3),(12,2),(13,1)):
        p.append((pin,f'K{digit}',S,f'K{tube}_{digit}'))
    p.append((8,'IC8',X,None))
    device(f'V{tube}','QS30_1','J13-1A socket', '', sorted(p),status='HOLD_SOCKET',
           value='QS30-1 / J13-1A')
    for pos, first, second in ((70,H,f'ANODE_MID{tube}'),(71,f'ANODE_MID{tube}',anode)):
        device(f'R{pos+tube*2}', 'R', 'MFR02SF1002A10',
               'Resistor_THT:R_Axial_DIN0414_L11.9mm_D4.5mm_P15.24mm_Horizontal',
               [(1,'1',S,first),(2,'2',S,second)],
               'https://item.szlcsc.com/59791.html', status='HOLD_ANODE_THERMAL',
               value='10k 1% 2W')
for idx in range(1,5):
    device(f'H{idx}','HOLE','Mounting hole', 'MountingHole:MountingHole_3.2mm_M3', [],
           status='HOLD_MECHANICAL')
