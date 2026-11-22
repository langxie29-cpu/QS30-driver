# 电气审查清单
- 范围：R14.5实板连通/净距、R14.3故障隔离/STOP/锁存、interlock仿真、能量审计。
- 已证明：30/30阴极与Q1–Q30 180对端点铜连；外部HV净距违规24→5；J6 39/49；整板仍84未连接。保护/整板G5/G6阻断，P01/EVT/制造HOLD，HV_POWER_ON禁止。
- STOP/锁存：冻结路径J6 NC→R509/R510/C64→Q35→FAULT_N→U9→U8；interlock为仿真，stuck_u11约1.90µs停止，contact_bridged无停止时间且输出仍高，stuck_u11_and_mos_short门极仍3.3V；U25约1s未实测。
- 170/195V：能量审计仅给170V 52.45mJ、195V 69.02mJ、60V 6.53mJ与509例最大残差58.8µJ，均为代理/仿真，不是最终boost或实板母线。
- 残压检测：8/10mA漏16/16，6mA命中1误报3；综合命中9误报6；阈值仅仿真，1ms为首板诊断试验。
- 关键未知：实际boost波形/母线瞬态、硬件STOP/锁存动作、残压传感器、器件脉冲/热/绝缘、J6桥接与/OE硬短路限制。
- 证据：R14_5_FINAL_REPORT.md、FAULT_CONTAINMENT_OPTIONS.md、interlock_metrics.csv、energy_audit.json。
