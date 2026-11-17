* reverse window -250 V .. 0 V
.include ss14_vishay.models
.model DSS14 D
.temp 125
VA NVAP 0 0
D1 NVAP NVKP DSS14
VK NVKP 0 0
.dc VA -250 0 0.5

.control
run
wrdata out.dat i(VA)
.endc
.end
