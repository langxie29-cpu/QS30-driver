# 电气和保护资格

|项目|R7 判定|证据|
|---|---|---|
|原 R6 12 V、等效典型管负载、原注册 8 ms 尾窗|LIMITED_PASS|[原样复跑](evidence/runs/exact/)，完整正常代理窗口|
|10.8 V 冷启动和 2 W 点、12 V 匹配负载、13.2 V 无管与低负载、高温、恢复|INCONCLUSIVE|[注册与实跑](SIMULATION_RESULTS.csv)，欠缺跨角点的统一有效尾窗和恢复证据|
|VGS、VDS、二极管、电容、L1|LIMITED_PASS|[原样应力](evidence/runs/exact/)，典型普通窗约 173 V MOSFET、176 V 二极管反向，全程 −0.31 至 11.99 V VGS，稳态电容 RMS 59.4 mA。布局和温度仍开|
|0.6 A eFuse 正常窗口|HOLD|[R6 预充峰](evidence/runs/exact/waveform_metrics.json) 与 [dV/dt 敏感度](evidence/runs/precharge_ramp/)。未获得真实器件的 IOUT、IMON 或热限制时序|
|独立 OVP 拾取与门极抑制|LIMITED_PASS|[已 ARM 比较器与驱动单元](evidence/runs/protection_armed/)，3.3 V 固定预偏置下从 184.4 V 过门槛至开漏跌破 1.65 V 约 18.8 µs，输入以 100 V/ms 注入。先测得栅极约 11.99 V，再测得关断。锁存和开断用代理|
|输入开断及 PWM 停止后的被动前向通路|HOLD|隔离单元在 PWM 停止时得到 11.14 V 被动馈通，开断后约 0.12 mV，真实 U1 停供要求保持待验证。 [隔离单元](evidence/runs/isolation/)|
|AUX 偏置下降与掉电|HOLD|10 V AUX 强制 PWM 时 U6 将 EN 拉至约 6.4 mV，栅驱仍能输出约 10 V。整链必须验证 LT 禁止 PWM 延迟、U5 UVLO、HV5622 失电消隐，及未授权重启。 [单元](evidence/runs/protection_armed/)|
|手动 ARM、POR 和残压硬许可|HOLD|R6 仅时钟及 OVP 置位，不能在 OVP 释放至 60 V 之间阻挡新 ARM。须对保持按钮、重复边沿、跌落与恢复独立测试|
|双泄放及单路开路|LIMITED_PASS|5.5µF 初始 195 V，隔离模型双路/单路至 60 V 为 1.611/3.229 s。按 +1% R 上限，预算 1.630/3.261 s。 [时序与能量](FAULT_ENERGY_BUDGET.csv)|
|整机故障切断、SOA、耐压及实物验证|HOLD|[保护时序表](PROTECTION_TIMING_BUDGET.csv) · [制造阻塞](MANUFACTURING_BLOCKERS.md)|

195 V、5.5µF 初始储能 104.57 mJ。下游电感和低压电容能量单列。eFuse 短失效时持续供能还由外部电源、F1 时间电流和 TVS/热路径决定。60 V 只是本轮泄放量化指标，批准条件还包括外壳、绝缘及实际残压。
