* A: UCC3803 reference-derived DCM fixture; actual TI controller, proxy switch/rectifier.
.include uccx813-3.lib
LPOWER vin lx {LMAG} ic=0
R_DCR lx drain 45m
VQ drain sw 0
S_Q sw source gate source SWITCH_A
.model SWITCH_A SW(Ron=0.25 Roff=500Meg Vt=2.5 Vh=0.12)
C_OSS sw source 85p
C_GATE gate source 450p
D_BODY source sw D_BODY_A
.model D_BODY_A D(Is=10n Rs=0.1 BV=250 IBV=0.25m Cjo=35p Tt=35n)
D_HV drain hv D_RECT_A
.model D_RECT_A D(Is=10n Rs=0.1 BV=400 IBV=1u Cjo=12p Tt=25n)
R_SENSE source 0 100m
R_GATE drv gate 10
R_CS source cs 1k
C_CS cs 0 1n
R_CT ref ct 60.4k
C_CT ct 0 {CT}
C_REF ref 0 100n
R_FB1 hv fb 645.12k
R_FB2 fb 0 7.68k
C_COMP comp fb 220p
X_CTL comp fb cs ct 0 drv vin ref UCC3803
