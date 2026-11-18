# R7 电源收敛、成本与原生工程审查

**Reference Design** 为 12 V P1 LT3757A。**Recommended Design** 也是 R7 的 12 V P1 研发候选，制造保持 HOLD。**Lowest-Cost Candidate** 暂缺完整可比 BOM 与到手数据；P2 的 UCC28C43DR 是已见最低裸控制器价，TPS40210DGQR 是外围复杂度较低的下一优先控制器研究候选。 [资格矩阵](QUALIFICATION_MATRIX.json) · [封装与供货](COMPONENT_SUBSTITUTION_MATRIX.csv)

|问题|R7 答复|证据|
|---|---|---|
|1. 12→170 V LT3757A 是否真正收敛？|冻结 R6 代理范围通过，12 V 末 8 ms 均值 170.056 V，纹波 0.282 Vpp。实际整机角点、恢复和保护尚未闭合。|[原样复跑](evidence/runs/exact/) · [资格](ELECTRICAL_QUALIFICATION.md)|
|2. 超时根因和处置？|原运行直接由墙钟超时终止。多处分段时间步升级造成实际数值负担；换 Gear、Alternate 与缩小保存均未消除。原样改进梯形已取得尾窗，复杂模型瓶颈与原环境差异仍开放。|[诊断](SIMULATION_DIAGNOSTICS.md)|
|3. 0.6 A 与电感是否冲突？|0.786 A 是开关脉冲。原样全程 1.10 A 与 1.33 A 源流峰同时出现在 PWM 前的被动预充。真实保留电容、斜率和限流带宽决定 IOUT，不能直接等同。|[峰值定位](evidence/runs/exact/waveform_metrics.json) · [预充敏感度](evidence/runs/precharge_ramp/)|
|4. TMR 可替换？|现图两侧负端均接系统地，非隔离调压可研究。需保证 HV5622 10.8–13.2 V 及 U6 许可上下限，TPS552872RYQR 保持 HOLD。|[供应](SUPPLY_RISK_REVIEW.md) · [器件矩阵](COMPONENT_SUBSTITUTION_MATRIX.csv)|
|5. UCC27511 必要？|P1 保留。提供足够 VGS 和独立故障抑制。现有 FET 的 RDS(on) 按 10 V 规定，LT3757A 7.2 V 直驱替换被拒绝。|[取舍](DESIGN_TRADEOFFS.md)|
|6. 更便宜的控制器？|TPS40210DGQR 与 UCC28C43DR 均低价，尚未证明完整低线、热、空载和故障等效。|[拓扑对照](ALTERNATIVE_POWER_ARCHITECTURES.md) · [各次运行](SIMULATION_RESULTS.csv)|
|7. 磁件、MOS、SiC 与电容？|可查 MSS1260-154KLD、STP6NK60Z、STPSC2H065B-TR、STTH1R06U、Rubycon 450PX4.7MEFC10X12.5。待热态、动态和供货审查，无功率器件导入。|[器件矩阵](COMPONENT_SUBSTITUTION_MATRIX.csv)|
|8. HV5622PG-G 最经济？|仍是已审三位静态驱动参考。PJ 三只公告子集差 $1.47，缺货与 PLCC 改版成本未闭合。PG 的绝对最低全成本未证明。|[价格](SUPPLEMENTAL_PRICE_EVIDENCE.csv) · [供应](SUPPLY_RISK_REVIEW.md)|
|9. 单板、三板实际降多少？|全套均 UNKNOWN。LCSC P2 TPS40210 的控制器一片价差 $3.3312、三片 $9.9936，UCC28C43DR 为 $4.2677/$12.8031。均未计外围、制造、税运。R7 原生无已确认降本。|[数量档](LCSC_PRICE_EVIDENCE.csv) · [1/3/5/10 核算](BEFORE_AFTER_COST.csv)|
|10. 批准与拒绝？|批准四只既有分压落实准确 MPN，保留原电值。拒绝直接使用保护后 VIN 作 HV5622 稳压轨及现 P1 直驱，其他替换 HOLD。|[审批矩阵](COST_OPTIMIZATION_CANDIDATES.csv)|
|11. 降本风险和验证成本？|P2 增加补偿、限流、硬关断与启动验证。调偏置则新增跨压、轻载/掉电、EMI。较小磁件、硅二极管和电解各需新增热、寄生与寿命审查。真实 NRE 未报价。|[取舍](DESIGN_TRADEOFFS.md)|
|12. 12 V 还是 24 V？|研发保留 12 V。24 V 均流约减半，名义 CCM 占空降低，尚需额外输入保护、AUX、配电测试与报价。|[计算](POWER_AND_LOAD_BUDGET.csv)|
|13. 原理图与仿真一致？|关键功率、分压、ADC、泄放和管支路设计值相符。eFuse、TMR、管动态、U7/POR 和板寄生按范围逐项标明，整机并未由同一真实器件模型覆盖。|[映射](BASELINE_RECONSTRUCTION.md) · [真实网表](evidence/native.xml)|
|14. 首次 PCB 尚缺哪些资格？|主要是可重复全角点，U1、失电与独立关断，残压硬许可，管座机械/绝缘几何、布局、DRC、供货、目标 MCU 实物与独立放行。|[阻塞](MANUFACTURING_BLOCKERS.md)|
|15. 下一轮最值得做什么？|先验证前级实际 dV/dt、被动预充和 IOUT，并建立 AUX/OVP 故障实际切断与残压 ARM 的窗口。随后用统一负载完成正常角点。|[下一轮](NEXT_ENGINEERING_DECISIONS.md)|

R6 按历史资产口径单板 ¥276.82–481.82、三板 ¥830.46–1,445.46 为规划区间。R7 以同一批页面重建 1、3、5、10 块下单口径和逐料小计。R7 三板已见材料子集 US$114.5812，R6 为 US$109.8772。两者覆盖的 MPN 数不同，差额不是完整成本变化。R7 新锁定的四颗分压新增可见料项，当前 69 个拟装实例仍缺准确 MPN。完整到手成本、15% 和 25% 目标保持未知。采购、付款、制造、实物高压、危险故障注入及 main 合并保持 HOLD。 [逐行](evidence/order_lines.csv)

原生 LTspice 共 30 次，5 次返回零、16 次超时、9 次非零退出。Flash 共 5 次、4,789 tokens，费用 UNKNOWN。低压 C 回归在 RV32 实际执行通过，STM32C011 通过目标语法检查。完整大波形留在执行机，远端含全部运行网表、日志、摘要和合适大小的原始波形。

[原生工程](NXT_M3_R7_EDA/NXT-M3.kicad_pro) · [复现](REPRODUCE.md) · [运行收据](evidence/resources.json) · [R1](R1_DECISION.md) · [R2](R2_DECISION.md) · [R3](R3_DECISION.md) · [R4](R4_DECISION.md) · [R5](R5_DECISION.md)
