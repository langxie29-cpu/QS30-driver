from r3lib import *
from runner import run
import re,argparse
TEMPLATE=(R2/'evidence/principal/filter22R_4p7n_threads1_200ms/circuit.cir').read_text()
OBS='.save V(vin) V(in) V(hv) V(en) V(intvcc) V(out) V(gate) V(src) V(sense) V(drain) V(ss) V(vc) I(LPOWER) I(DREC) I(RSRC) I(RNEG) I(RG) I(RSNUB) I(COUT) I(XQ:LD) I(XQ:LS) I(XQ:LG) V(XQ:13) V(XQ:9) V(XQ:5) V(XQ:7) V(XQ:6) V(XQ:12)'
def front(vin=24,kind='fast',bulk='1u',stop=.12):
 s=TEMPLATE.replace(s0:='QS30 exploratory cold start, genuine controller, initial COUT=0','QS30 R3 dissipative frontend PARAMETER STUDY, real LT3757A LDO, COUT0')
 supply=f'PWL(0 0 1u {vin})' if kind!='normal' else f'PWL(0 0 5m {vin})'
 if kind=='restart':supply=f'PWL(0 0 1u {vin} 60m {vin} 60.001m 0 65m 0 65.001m {vin})'
 s=s.replace('VINPUT vin 0 PWL(0 0 1m 24)',f'VINPUT vin 0 {supply}')
 s=s.replace('RINPUT vin in .1',f'''* Favorable INSTANTANEOUS current regulation. Not TI vendor behavior or timing bound.
* Cdvdt is a real charged state; pass current only moves energy VIN -> switched branch.
VPERMIT permit 0 PWL(0 0 1u 0 1.001u 1)
BVALID valid 0 V=if(V(vin)>19,if(V(permit)>.5,1,0),0)
BDVDT 0 dvdt I=if(V(valid)>.5,if(V(dvdt)<1.2,5.5u,0),-V(dvdt)/14)
CDVDT dvdt 0 42.3n IC=0
BPASS vin in I=if(V(valid)>.5,max(0,min(1.591,min(V(vin,in)/.25,10*(25.5*V(dvdt)-V(in))))),0)
CIN in 0 {bulk} Rser=.05 IC=0
RINBLEED in 0 100k
* Required output negative clamp candidate, coarse diode only; exact MPN pulse qualification HOLD.
DCLAMP 0 in DCL
.model DCL D(Is=1u Rs=.05 N=1.1 Cjo=100p Bv=60)
''')
 s=s.replace('VAUX aux 0 PWL(0 0 1m 12)\nRAUX aux intvcc .1\n','')
 s=s.replace('XU vc fb ss rt 0 sense out intvcc en intvcc 0 LT3757A','XU vc fb ss rt 0 sense out intvcc en in 0 LT3757A')
 # Original hardware UVLO divider; independent safe permit needs implementation.
 if kind=='disabled':s=s.replace('REN1 in en 200k\nREN2 en 0 12.8k','VEN en 0 0')
 if kind=='permit_loss':s=s.replace('PWL(0 0 1u 0 1.001u 1)','PWL(0 0 1u 0 1.001u 1 60m 1 60.001m 0)')
 if kind=='bias_loss':s=s.replace('CSS ss 0 100n IC=0','CSS ss 0 100n IC=0\nVBIASFAIL bf 0 PWL(0 0 60m 0 60.001m 1)\nSBIAS intvcc 0 bf 0 BIAS\n.model BIAS SW(Ron=.1 Roff=1G Vt=.5)')
 if kind=='short':
  s=s.replace('REN1 in en 200k\nREN2 en 0 12.8k','VEN en 0 0')
  s=s.replace('RLOAD hv 0 5200','RLOAD hv 0 5200\nVFAULT f 0 PWL(0 0 12m 0 12.001m 1)\nSFAULT hv 0 f 0 FAULT\n.model FAULT SW(Ron=.01 Roff=1G Vt=.5)')
 s=re.sub(r'(?m)^\.tran .*$',f'.tran 200n {stop} 0 200n uic',s)
 s=re.sub(r'(?m)^\.save .*$',OBS+' V(dvdt) V(permit) I(BPASS) I(CIN) I(DCLAMP)',s)
 return s
def cell(step='10p',pcb=False):
 s=(R2/'evidence/principal/minimum_all_currents5ps/circuit.cir').read_text()
 s=s.replace('QS30 exploratory cold start, genuine controller, initial COUT=0','QS30 R3 localized stress cell IC89.17V IL1.4A, NOT STARTUP')
 s=s.replace('RF src sense 10','RF src sense 22').replace('CF sense 0 1n','CF sense 0 4.7n')
 s=re.sub(r'(?m)^\.tran .*$',f'.tran {step} 1.1u 0 {step} uic',s)
 s=s.replace('numdgt=15','numdgt=15 threads=1')
 if pcb:s=s.replace('VQD drain qd 0','LPCB_D drain qdp 5n Rser=.01\nVQD qdp qd 0').replace('VQS qs src 0','VQS qs qsp 0\nLPCB_S qsp src 5n Rser=.01')
 s=s.replace('.save V(*) I(*)',OBS+' I(VQD) I(VQG) I(VQS) V(qd) V(qs) V(qg) V(q:13) V(q:9) V(q:5) V(q:7) V(q:6) V(q:12) I(L:q:LD) I(L:q:LS) I(L:q:LG) I(M:q:MOS) I(D:q:DBS) I(D:q:DBD)')
 return s
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('group',choices=['nominal','corners','events','stress','fault','probe','probe_instance','internal']);v=a.parse_args()
 jobs=[]
 if v.group=='nominal':jobs=[('front24_fast',front(),.12,700)]
 if v.group=='corners':jobs=[('front21p6_fast',front(21.6,stop=.08),.08,550),('front26p4_fast',front(26.4,stop=.08),.08,550),('front24_normal',front(kind='normal',stop=.08),.08,550)]
 if v.group=='events':jobs=[('front24_restart',front(kind='restart'),.12,700),('front26p4_disabled',front(26.4,'disabled',stop=.025),.025,120),('front24_permit_loss',front(kind='permit_loss'),.12,700),('front24_bias_loss',front(kind='bias_loss'),.12,700)]
 if v.group=='stress':jobs=[('cell10ps',cell('10p'),1.1e-6,90),('cell5ps',cell('5p'),1.1e-6,90),('cell_pcb5n',cell('5p',True),1.1e-6,90)]
 if v.group=='fault':jobs=[('front26p4_short1u',front(26.4,'short','1u',.025),.025,150),('front26p4_short47u',front(26.4,'short','47u',.025),.025,150)]
 if v.group=='probe':
  # One bounded compatibility probe only; no decryption, no conversion and no vendor-model edits.
  lib=ROOT/'projects/QS30-9_24V/sources/sprint06/TPS26601_pspice/unpacked/TPS26601_TRANS.LIB'
  deck=f'TPS26601 compatibility probe only\n.include "{lib.as_posix()}"\nV1 in 0 24\nR1 in 0 1k\n.tran 1u 10u\n.save V(in)\n.end\n'
  jobs=[('tps_encrypted_probe',deck,10e-6,30)]
 if v.group=='probe_instance':
  lib=ROOT/'projects/QS30-9_24V/sources/sprint06/TPS26601_pspice/unpacked/TPS26601_TRANS.LIB'
  deck=f'''TPS26601 actual instantiated compatibility probe
.include "{lib.as_posix()}"
V1 in 0 24
VSH sh 0 2
RIL ilim 0 8k
RMODE mode 0 402k
CDV dvdt 0 47n
COUT out 0 1u
RLOAD out 0 1k
XEF flt 0 sh mode ilim nc0 nc1 dvdt imon 0 0 0 out out in in 0 TPS26601_TRANS
.options threads=1
.tran 1u 10u
.save V(in) V(out)
.end
'''
  jobs=[('tps_instantiated_probe',deck,10e-6,30)]
 if v.group=='internal':
  deck=cell('5p').replace('I(M:q:MOS) I(D:q:DBS) I(D:q:DBD)','Id(M:q:OS) Ig(M:q:OS) Is(M:q:OS) I(L:q:D) I(L:q:S) I(L:q:G) I(D:q:BS) I(D:q:BD) I(R:q:D) I(R:q:G) I(R:q:S) V(q:4) V(q:8)')
  jobs=[('cell_internal5ps',deck,1.1e-6,90)]
 for name,deck,stop,budget in jobs:
  run(name,deck,stop,budget,'P0 frontend energy-path study' if name.startswith('front') else 'P0 localized stress or bounded compatibility study','Not vendor frontend timing/thermal qualification. Genuine control and power models retained; behavioral protection delay favorable/unbounded in hardware. All safety holds retained.')
