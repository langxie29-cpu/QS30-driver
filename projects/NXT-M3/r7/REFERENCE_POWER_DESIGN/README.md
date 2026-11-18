# P1 模型

[原理图](../NXT_M3_R7_EDA/NXT-M3.kicad_pro) · [关键网络映射](../BASELINE_RECONSTRUCTION.md) · [正反证](../SIMULATION_RESULTS.csv)

- p1_vendor_* 是完整连接的研究模型，TPS3700 与 UCC27511 采用 TI 方程，U7、eFuse 和供电为代理。输入电压和显示条件按文件名区分。
- protection.cir 保留首轮未有效 ARM 的反例。protection_armed.cir 用一个受控断开前的 ARM 代理复查比较和栅驱。该 deck 的供能为强制输入，不能代表整机 OVP 峰值。
- precharge_ramp.cir 仅用于被动预充通路结果，基于 TPS26600 模型之外的典型 dV/dt 与 0.6A 夹限。
- isolation.cir 与 R6 的隔离单元同一个模型，用于独立量化泄放与被动馈通。
