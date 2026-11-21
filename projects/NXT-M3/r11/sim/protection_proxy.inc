* Ideal ARMED latch, RC timing surrogate and U11 switch shutoff.
B_RAW TRAW 0 V={max(v(OVP)>1.25,v(CS_FILT)>v(OCP_REF))}
R_TRIP TRAW TRIP 1k
C_TRIP TRIP 0 2n
S_KILL HOLD 0 TRIP 0 S_KILL_SW
.model S_KILL_SW SW(Ron=30 Roff=1T Vt=.5 Vh=.025)
C_LATCH_A HOLD 0 1n IC=3.3
R_HOLD HOLD 0 1T
B_ARMED ARMED 0 V={v(ARM_REQUEST)*min(1,max(0,v(HOLD)/3.3))}
.meas tran trip_time WHEN v(TRIP)=.5 RISE=1
.meas tran armed_loss WHEN v(ARMED)=1.6 FALL=1
.meas tran hv_25ms FIND v(HV) AT=25m

