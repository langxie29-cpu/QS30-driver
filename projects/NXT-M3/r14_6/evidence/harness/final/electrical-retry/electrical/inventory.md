# R14.6 保护端点与模型边界审查

## 证据锚点
- KiCad 10.0.8 原生 after：ERC 0/0，clearance 79，unconnected 65，added_violations 0，prior_connections_lost 0；cathodes 30/30，cathode_endpoints 180/180。
- 保护计数：OVP/FB/SNUB before 14 → after 20；J6 before 39 → after 39。
- 保护连通：R81.1→C47.1、R83.2→R84.1、SNUB 两端、C35.1→U13.2 已接通；但 R61.2→R62.1、D3.1→C47.1、看门狗及部分 J6/许可/硬件消隐端点仍未接通，不能给 STOP、OVP、OCP、重新使能、泄放签字。
- 仿真：off_170、off_195、partial_195、stop_nominal、stop_one_bleeder、stop_u11_stuck、watchdog_proxy、ovp_proxy 均 exit 0，solver 为 ngspice-46 DLL，且 applied_to_final_hardware=false。
- 代理结果：OVP/FB 空载故障 trip 约 21.893 ms，25 ms 母线约 187.86 V；OCP 基础代理未报 trip，R4 重塑注入约 18.001 ms 报 trip，显示注入形态依赖。

## 限制
- 170/195 V 工况仅验证理想目标电压及 30 mA 限流模型；连续稳压、阴极浮置峰值、温升、器件 SOA 未验证。
- OVP/OCP 共因、前级启动掉电、控制器开路/短路、噪声与钳位未验证；泄放 bus_to_60_s 以仿真起点计量，阈值及单失效实板复测缺失。
- U11/R40 为 DNP，U18.5 原生接 GND；J6 桥接、持续喂狗故障、U8/U9 失效、共用偏置失供覆盖未证明。
- 缺少与最终 PCB、已确认装配配置及寄生参数一致的 LM5155 模型；重复峰值、D3 超快整流换流、MOSFET SOA、实际吸收效果未知。

## 下一门证据
- 恢复电源和保护端到端布线，闭合原理图/PCB，确认 DNP 配置和独立硬件保护路径。
- 使用与最终板一致的模型参数、供电约束和寄生参数完成 OVP/OCP/STOP/泄放/开关应力验证，并制定实板阈值、单失效、温升和 SOA 试验计划。
- POWER_SIMULATION、EVT_RELEASE、HV_POWER_ON 均为 HOLD；本审查不构成任何门批准。
