* F2 pins: 2-terminal device (A K); forward sweep 0..1.2 V
.include us1g_diodesinc.models
.model DI_US1G D
.temp 27
VA NVAP 0 0
D1 NVAP NVKP DI_US1G
VK NVKP 0 0
.dc VA 0 1.2 0.005

.control
run
wrdata out.dat v(NVAP) i(VA)
.endc
.end
