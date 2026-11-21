* Current-mode controller proxy, no manufacturer qualification.
* R79 determines the screening clock at 100 kHz. COMP scaling and timing are assumptions.
VCLK CLK 0 PULSE(0 1 2u 10n 10n 95n 10u)
B_ENABLED ENABLE 0 V={0.5+0.5*tanh((v(UVLO)-1.5)*100)}
B_SS 0 SS I={10u*v(ENABLE)}
R_SS SS 0 1G
S_RESET_SS SS 0 DISABLE 0 SS_SW
B_DISABLE DISABLE 0 V={1-v(ENABLE)}
.model SS_SW SW(Ron=100 Roff=1G Vt=.5 Vh=.02)
B_GM 0 COMP I={max(-200u,min(200u,0.002*(min(v(SS),1)-v(FB))))}
D_C_HI COMP CLAMP_HI CLAMP_D
D_C_LO CLAMP_LO COMP CLAMP_D
VCLH CLAMP_HI 0 2.2
VCLL CLAMP_LO 0 1.53
.model CLAMP_D D(Is=1n N=1)
B_DUTY PHASE 0 V={time-floor((time-2u)/10u)*10u-2u}
V_ONE ONE 0 1
S_SET ONE LATCH CLK 0 PWM_SET
.model PWM_SET SW(Ron=1 Roff=1G Vt=.5 Vh=.05)
C_LATCH LATCH 0 100p
R_LATCH LATCH 0 100Meg
B_RESET RESET 0 V={max(v(DISABLE),max(v(PHASE)>9.25u,(v(PHASE)>200n)*(v(CS)+v(PHASE)*1600>min(.1,max(0,(v(COMP)-1.14)*.082)))))}
S_LRST LATCH 0 RESET 0 PWM_RESET
.model PWM_RESET SW(Ron=.12 Roff=1G Vt=.5 Vh=.05)
B_PWM PWM 0 V={v(VHV)*(0.5+0.5*tanh((v(LATCH)-.5)*50))}
R_RTLOAD RT 0 1G
R_READY READY 0 1G
R_VCC VHV VCC 1

