# NXT-M3 R14.3 · 晶体管热与击穿后保护

```text
Q1_THERMAL_DECISION = HOLD
FAULT_CONTAINMENT_DECISION = HOLD
PROTECTION_ARCHITECTURE = 阳极双电阻 + 基极反向阻断/下拉 + J6硬件锁存/U11断供 + 595消隐 + 双泄放；增强项为U18独立门极禁止与状态相关诊断
Q1_INSULATION_DECISION = HOLD
EVT_RELEASE = HOLD
MANUFACTURING_RELEASE = HOLD
```

2026-11-22。基线 `nxt/nxt-m3-insulation-r14-2`，`db3d7cc3420c255fe2cb0e270b602cce5384dd2f`。交付分支 `nxt/nxt-m3-thermal-protection-r14-3`。原 R13、R14 和 R14.2 目录保持原提交内容。冻结升压电路和 R40、U11 DNP 状态继续有效，工程只执行软件验证。 [复现](REPRODUCE.md)

## Q1 在什么条件下会过热

R14 的 478.4 mW 是 **外部 RCE** 耗散，同一时刻 Q1 代理的端口耗散约 **19 nW**。R14.3 用独立 B/C 电流测量源追踪 Q1。正常饱和工况约 1 mW 以内。195 V 连续供能、有 110 V 管降的半导通代理最多约 **89 mW**，低于 85°C 的 182 mW 静态热筛查。没有高 VCE 热态 SOA 证据，辉光管压降和热阻也须实测。若管压降消失且基极持续处在中间电平，代理 Q1 约 **474 mW**、**104 V / 4.57 mA**，比 25°C 静态限值还高约 35%。195 V、100 kΩ C–B 代理漏电加零管降时，Q1 自偏置在 25°C 约 **294 mW**、85°C 约 **275 mW**，热态超筛查。C47 直接接触基极还可将能量送入 B–E。 [功率归属与模型](MMBTA42_REAL_DISSIPATION.md) · [稳态温度与 SOA](TRANSISTOR_THERMAL_SOA.csv)

在 474 mW 工况，断供前每 1 ms 约加 0.474 mJ。如果基极仍有中间电平，0 ms 断供代理也有 **25.38 mJ** 进入 Q1。1 ms 后同时取消可控基极驱动时，断供后 Q1 约 **0.00017 mJ**，此时储能主要改走放电链。独立 B–E 注入或 C–B 自偏置仍可绕过消隐。要批准最大作用时间，须同时有起始结温、瞬态热阻、VCE–IC 轨迹对应的单次/重复脉冲 SOA 及二次击穿边界。85°C 单脉冲热筛查从当前功耗导出 `ZθJA(t) ≤ 137 K/W`，制造商证据未知，维持禁止高压。 [切断与消隐波形](evidence/scan_metrics.csv)

## 故障如何传播

| 主要路径 | 结论 |
| --- | --- |
| 有阳极限流的 C–E 短路 | 被选阴极失控，管能否点亮取决于点火。阳极链为 19.8 kΩ 时，195 V 零管降电流上界 9.85 mA，R302/R303 每颗最坏约 0.96 W。Q1 可几乎无结耗散，/OE 不能断开短路。 |
| 有阳极限流的 C–B 短路或漏电 | B–E 尚通时主要回地，并可能自偏置加热 Q1。B–E 也失效开路时，分流经 R100/R200、595 的输出管或钳位进入 3V3 并影响稳压和 MCU。二极管保护对这条路径的稳态回灌有效，仍须检验位移电流、热泄漏和短开路故障。 |
| 跨过阳极的接触或电痕 | C47 的 ESR、走线和故障通道限制脉冲。直接落到 Q1.B 或 595 输出侧的路径不同。以假设 10 Ω 到地，代理约 19 A。以 100 Ω 直达 595 侧，尽管理想断供，0–40 ms 仍有约 56.5 mJ 在该外部桥路耗散。模型超出器件线性和损坏边界后的数值仅表示过应力。 |
| U11 或 STOP | J6 到清锁存、/OE 在低压软件夹具内满足重新 ARM 约束。U11 卡通时电源仍在，U18 IN− 可单独停止门极驱动，D3 直通路径仍可把 5 V 侧耦入母线。健康双泄放 / 单路开路约 1.072 / 2.144 s 到 60 V。 |

空气导电接触、PCB 反复电痕和半导体内部击穿分别列在故障矩阵里。接触阻值为仿真假设。峰值未包含实物电感、不同铜距与材料的失效演进。 [模式、路径与传播](BREAKDOWN_FAULT_MATRIX.csv) · [能量与误差](evidence/energy_audit.json)

## 保护实现与验证结果

- 最小候选为原有限流与双泄放、基极串联 ES1G-13-F 阻断、4.7 kΩ 下拉、共享 1 kΩ 轨道负载、补齐 J6 联锁与消隐。独立三路 KiCad 样片还实现了增强候选的 U18 IN− 接口。它是可编辑的 LV 夹具项目。 [选型与成本](PROTECTION_ARCHITECTURE_DECISION.md) · [原生候选](candidate/R14_3-protection-coupon.kicad_pro)
- **ngspice 47** 完成 **509 个电气工况及 11 个 STOP 工况**。保存全部原生 RAW、可独立执行网表、参数和求解日志。电气源–耗散–储能审计，步长复算，旧功率归属断言，以及 64 条检测重放均通过。总电流阈值存在明确的漏检，增强传感暂作诊断。 [电气扫频](evidence/scan_metrics.csv) · [STOP 时序](evidence/interlock_metrics.csv) · [检测计数](evidence/detector_summary.json)
- **候选 KiCad 10.0.8** 为 ERC 0，原生 DRC **18 项间距违规、0 项未连接**，原理图—PCB 一致性 0 项。47 组针脚分配和 30 组同网铜路径均通过。晶导 C–B、C–E 铜距 1.1102 mm，SMA 对边 1.5000 mm，严于二者的 2.00 mm 规则仍生效。18 项中 9 项同封装焊盘对，另 9 项是 Q 附近焊盘、出线组合，由同一局部几何触发。 [候选原生审计](evidence/candidate/audit.json) · [完整 DRC](evidence/candidate/DRC.json)
- **冻结板与 R13 回归** 为 ERC 0、253 项净距违规、337 项未连接、一致性 0，Q1 铜 6/6、J6 联锁 36/49，与 R14.2 一致。R13 7 项单元测试、封存只读预检通过。Live Workers 调用 0，未触发付费流程。 [冻结板审计](evidence/regression/frozen_board_audit.json) · [Harness 预检](evidence/regression/harness_doctor.json)

下一步最小实物验证是在 0–5 V 夹具上测 J6 开断和复位顺序、U11 模拟卡通下的 U18 停振、/OE 消隐、残压联锁以及开/关机的逻辑轨回灌。继续取得晶导高 VCE 热态 SOA 和板级热量测依据。 [低压验证计划](LOW_VOLTAGE_VALIDATION_PLAN.md)
