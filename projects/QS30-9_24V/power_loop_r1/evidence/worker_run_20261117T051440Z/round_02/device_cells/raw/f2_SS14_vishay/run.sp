* F2 pins: 2-terminal device (A K); forward sweep 0..1.2 V
.include ss14_vishay.models
.model DSS14 D
.temp 27
VA NVAP 0 0
D1 NVAP NVKP DSS14
VK NVKP 0 0
.dc VA 0 1.2 0.005

.control
run
wrdata out.dat v(NVAP) i(VA)
.endc
.end
