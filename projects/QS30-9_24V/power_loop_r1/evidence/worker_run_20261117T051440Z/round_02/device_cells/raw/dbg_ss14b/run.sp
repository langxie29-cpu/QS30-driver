* reverse window -250 V .. 0 V
.include ss14_vishay.models
.temp 27
VA NVAP 0 0
X1 NVAP NVKP SS14
VK NVKP 0 0
.dc VA -250 0 0.5

.control
run
wrdata out.dat i(VA)
.endc
.end
