* sw probe
.temp 27
Vsw NVSW 0 PWL(0 0 0.04u 0 0.06u 1 1.32u 1 1.34u 0 3.32u 0 3.34u 1 4.62u 1 4.64u 0 10u 0)
Vbus NVBP 0 24
Ssw NVDP 0 NVSW 0 SWM
.model SWM SW(VT=0.5 RON=1m ROFF=100meg)
R1 NVBP NVDP 10
IV NVDP 0 0
.options reltol=1e-4
.tran 5n 10u 0 uic

.control
run
wrdata out.dat v(NVDP) v(NVSW) i(IV)
.endc
.end
