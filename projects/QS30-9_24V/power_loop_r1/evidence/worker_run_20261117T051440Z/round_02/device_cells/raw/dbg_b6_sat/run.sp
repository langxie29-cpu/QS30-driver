* F3b boost switch node 24 V -> D=0.60 @ 500 kHz, 6 periods
.temp 27
Vbus NVBP 0 24
Vsw NVSW 0 PWL(0 0 1.06u 0 1.08u 1 2.02u 1 2.04u 0 3.06u 0 3.08u 1 4.02u 1 4.04u 0 5.06u 0 5.08u 1 6.02u 1 6.04u 0 7.06u 0 7.08u 1 8.02u 1 8.04u 0 9.06u 0 9.08u 1 10.02u 1 10.04u 0 12u 0)
Ssw NVDP 0 NVSW 0 SWM
.model SWM SW(VT=0.5 RON=1e-3 ROFF=1e12)
Vds 0 NVDP 0
Bfl NSAT 0 V=Lslot*x/(1+(abs(i(L1))/x)**2)
L1 NVBP NSAT 1m IC=0
.param Lslot=150u x=9.7
D1 NVDP NVOP DUF
.model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)
Co NVOP 0 47u
Rld NVOP 0 3k
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.tran 5e-09 1.2e-05 0 uic

.control
run
wrdata out.dat i(L1) v(NVDP) v(NVOP) v(NVSW)
.endc
.end
