"""Principal-authored local switching diagnostic, NOT a startup fixture."""
import re
import lab
def build(p,step,method):
 lab.full(p,stop=10e-6,step=step,method=method)
 s=(p/'circuit.cir').read_text()
 s=s.replace('VINPUT vin 0 PWL(0 0 1m 24)','VINPUT vin 0 24')
 s=s.replace('LPOWER in drain 150u Rser=.16','LPOWER in drain 150u Rser=.16 IC=1.4')
 s=s.replace('XQ drain gate src STP9NK50Z','VQD drain qd 0\nVQG gate qg 0\nVQS qs src 0\nXQ qd qg qs STP9NK50Z')
 s=s.replace('COUT hv 0 20.3u Rser=.1 IC=0','COUT hv 0 20.3u Rser=.1 IC=89.17')
 s=re.sub(r'(?m)^XU .*$', 'VDRIVE out 0 PWL(0 0 1u 0 1.02u 12 5u 12 5.02u 0)',s)
 s=re.sub(r'(?m)^\.save .*$', '.save V(hv) V(drain) V(src) V(gate) V(out) V(sense) I(VQD) I(VQG) I(VQS) I(LPOWER) I(DREC) I(RSRC) I(RF) I(RNEG) I(RGS) I(RSNUB) I(CSNUB)',s)
 (p/'circuit.cir').write_text(s,encoding='ascii')
if __name__=='__main__':
 for label,step,method in [('gear_1ns',1e-9,'gear'),('gear_0p5ns',5e-10,'gear'),('trap_1ns',1e-9,'trap')]:
  p=lab.HERE/'evidence/principal/minimum_cell'/label
  build(p,step,method)
  print(label,lab.execute(p,'Does original diode/MOS/clamp network produce high shunt current with a finite gate edge, without controller? InitialHV89.17V/IL1.4A is local-state isolation only. No cold-start or current-limit qualification.', 'maxstep/method one variable relativeGear1ns',30),flush=True)
