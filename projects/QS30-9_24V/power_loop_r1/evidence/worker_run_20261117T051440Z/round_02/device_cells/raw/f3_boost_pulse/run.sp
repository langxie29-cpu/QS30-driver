* F3b boost switch node: Vin 24 V, D=0.65, fsw 500 kHz, L 150u DCR 0.038
.temp 27
Vbus b 0 24
Vsw sw 0 PULSE(0 1 1u 20n 20n 1.3u 2u)
Ssw d 0 sw 0 SWM
.model SWM SW(VT=0.5 RON=1m ROFF=100meg)
L1 b d 150u Rser=0.038
D1 d o DUF
.model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)
Co o 0 47u
Rld o 0 3k
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.options itl4=500 maxord=2 gmin=1e-12
.tran 1e-08 0.0015 0.0001 uic

.control
run
wrdata out.dat i(L1) v(d) v(o) v(sw)
.endc
.end
