* F3b cross-check: level-1 NMOS switch, same duty/period
.temp 27
Vbus NVBP 0 24
Vsw NVSW 0 PWL(0 0 1.06u 0 1.08u 1 2.02u 1 2.04u 0 3.06u 0 3.08u 1 4.02u 1 4.04u 0 5.06u 0 5.08u 1 6.02u 1 6.04u 0 7.06u 0 7.08u 1 8.02u 1 8.04u 0 9.06u 0 9.08u 1 10.02u 1 10.04u 0 12u 0)
Msw NVDP NVSW 0 0 MSW
.model MSW NMOS(LEVEL=1 VTO=1 KP=20 W=1 L=1u)
Vds 0 NVDP 0
Rl NVBP NVL 0.038
L1 NVL NVDP 150u IC=0
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
