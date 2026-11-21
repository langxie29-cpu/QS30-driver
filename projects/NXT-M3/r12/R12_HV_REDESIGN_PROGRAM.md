# NXT-M3 R12 — 5 V → 170 V power architecture / cost-down engineering program

**状态：SCOPING / RESEARCH COMPLETE (资料级)；SIMULATION NOT RUN；EDA UNCHANGED；GATE 0 REWORK；MANUFACTURING HOLD。**
**基线：** R11 `9a0be72b655b274c6712053ac32ebb90612b82eb`。本 R12 分支独立进行研究，不修改 R11 电路、BOM、PCB 或放行状态。

## 0. 成本口径与决策

- **HV-60（本轮硬性研发目标）：** 每块 3 位模块的完整高压供电、切断、OVP/OCP、残压、泄放、必要分支故障检测、阳极限流及分摊 PCB 材料，按人民币 **< ¥60/套** 的同批量询价口径核算；包含器件和必要板材分摊，不含人工、贴装、税运、辉光管及整机非 HV 子系统。分板方案必须计入高压接插件和分板成本。
- **M3-60（单独的探索目标）：** 整块三位模块所有物料 < ¥60；在 R10 原料号条件下，ESP32-S3 25.50 + 4×HC595 17.76 + OLED 9.78 + 管座 8.40 + 裸 PCB 13.00 = **¥74.44**，已超限，不可误报已实现。需要整机架构重构及真实采购报价，不能靠删安全功能。
- 所有金额仅在有**明确 MPN、数量、人民币阶梯报价、采购来源、日期、批量档和替代料**时标记 QUOTED；预算上限表 `HV_COST_CEILINGS.csv` 只是目标，不是商品价格或 BOM 资格证明。
- R10 247.38 元是单模块材料历史估算，不等于 R11 的 Type-C 更新后的完整实际成本。

## 1. 候选技术路线（均保留原理图/仿真/成本可追溯性）

| ID | 架构 | 开源来源 | 可复用资产 | 优势 | 开放风险 |
| --- | --- | --- | --- | --- | --- |
| A | 5→170 V DCM Boost, UCC3803, 33 µH | https://github.com/drkmsmithjr/NixiePowerSupply | KiCad、BOM、LTspice、TI UCC3803 模型 | 不需定制变压器；小板参考 | UCC3803 4.1/3.6 V UVLO、VREF/门极驱动余量、模型适配、开关 SOA |
| B | 5→180 V Flyback, LM3488, EFD15 | https://github.com/esynr3z/nixie-ps | KiCad、BOM、LTspice 及 LM3488_TRANS.LIB、实测数据 | 压力较小的初级开关；5 V 附近公开实测约 9.5–19.2 mA | 变压器 10:145 匝定制、漏感/钳位、磁件量产与版权许可待查 |
| C | 170 V Flyback, LT3757, DA2032-ALB 1:10 | https://github.com/tonyp7/170v-nixie-power-supply | 原理图 PDF/PNG、BOM、Gerber、实物记录（非原生可编辑 KiCad） | 现成磁件候选、已有装配实践 | DA2032-ALB 与 LT3757 实际采购价格、模型转移及低线表现未知 |
| D | R11 LM5155 22 µH Boost | 本仓库 R11 | ngspice 代理工况、真实 KiCad 原理图、应力和成本基线 | 保留可追溯对照 | TI 原始模型 ngspice 未收敛、低线掉压及大量 DRC/布线开项 |

**注意：** 开源项目在其他电路和测试条件下的成功不构成 NXT 的电气资格；B/C 的 100 V 初级 MOSFET 不得照搬到不带变压器的 Boost。授权须单独核实。

## 2. R11 故障根因假设与应排除事项

- 旧代理模型在 4.75 V 源端、0.190 Ω 回路、3.3 V 域 2.475 W、HV 9.9 mA 时，22 µH/100 kHz 的高压末段均值 **155.843 V**；22 µH/80 kHz 诊断 **169.847 V**；26.4 µH/100 kHz 为 **145.109 V**。这些结果说明需检验周期内可传输能量、峰流、最长导通时间、斜率补偿、损耗与真实输入塌陷，不可将其直接归罪于 LM5155 实物。
- TI LM5155-Q1 厂商模型在 ngspice 46 存在 COMP 子电路初值不兼容、ns 级数值发散或超时；替代模型必须先在**独立功率级**完成 0 V 冷启，再整合 eFuse、3.3 V 负载和保护逻辑。不得把代理模型通过当作厂家器件通过。
- R11 PWM 停止不是物理输入断开。独立高压输入断供/反灌保护、OVP、OCP、残压/双泄放、单路半导通热故障必须保留或证明等效机制。
- 输出电容由 3.3 µF / 450 V 改小时，需重算和测量纹波、阶跃、寿命、容量随偏压和温度的变化、故障储能、关断放电。不得仅依据价格下调规格。
- 单电感 Boost 的主 MOSFET 应对接近 HV 母线及尖峰；反激初级开关耐压需由反射电压、漏感尖峰及钳位确定。禁止直接降为 100 V。

## 3. 统一建模和验收矩阵

- 统一目标：**HV nominal 170 V**，候选筛选范围 165–175 V、稳态纹波 <=1 Vpp；要求明确记录筛选时窗、实际负载、数值方法和约束。此为当前工程目标，不是已实测的量产指标。
- 输入：5.00 V 源端标称；4.75 V 源端带 0.190 Ω 线缆及保护链；额外直接测试**升压控制器端 4.3 V**工况；高线 5.25 V，输入掉电、热插拔和重启。
- 负载：HV 0、7.65、9.9 mA 及短时阶跃；低压域同时按 0.76/2.475 W 边界扰动。三区静态数字驱动不能以理想电阻代替全部状态，模型边界要明确。
- 每组必须输出：0 V 初始条件证据、模型原始来源和 SHA、netlist、原始退出码/日志、HV/DC/纹波、首达稳态时间、I_L_pk、V_DS_pk、Q_gate、C_out 应力、正常/故障热功耗、效率、MOSFET/二极管/磁件降额及可复现脚本。
- 测试：正常冷启/满载/空载/低线，失供或拔线、关断/反灌、反馈开路、短路、OVP/OCP、重复重启、残压假低、单阴极半导通和单泄放失效。保护必须在不依赖 MCU 软件的情况下进入安全状态。
- 原理图/PCB：只有 A/B/C 的候选模型和 BOM 通过双人复核后才建立独立 KiCad 候选，不覆盖 R11；按真实电位差与环境绝缘协调、高压区隔离、开关回流/Kelvin、热与天线保留区设计；原生 ERC/DRC 必须闭合。
- 既有 R11 R40 DNP、尚未完成的 345 未连接项和 263 净距违规不因本成本项目而自动消除，整机制造继续 HOLD。

## 4. 多工作流职责（执行时每一项须留下可复核文件）

1. **A / baseline & numerical:** 隔离复现 R11 代理和厂商 LM5155 子电路，记录 COMP/init/step 收敛问题；不要为得到 PASS 而用假比较器替换厂商器件后冒称真实模型。
2. **B / Boost:** 导入 drkmsmithjr UCC3803 电路和料号，对 33 µH、40–100 kHz 工况进行与 R11 等条件匹配的 ngspice/LTspice 对照；校验 4.3 V UVLO 与驱动余量。
3. **C / flyback:** 分别复用 esynr3z LM3488 模型及 tonyp7 LT3757/DA2032 磁件路径，检查 Lp/Ls、反射电压、漏感尖峰、钳位损耗、磁件可采购性。
4. **D / procurement:** 用 BOM 源码逐一取得 1/3/10 套同口径中国大陆报价、替代 MPN、分板工艺和装配费用；在 `HV_COST_CEILINGS.csv` 的预算上线下给出真正的 QUOTED BOM。
5. **E / electrical safety:** 独立验证断供、故障可触及、残压、保护互锁、晶体管热 SOA、保护单点失效与绝缘协调；不得仅用软件禁显作为安全策略。
6. **F / independent review:** 用第二条检查链重跑模型和 BOM 数值，标注 VERIFIED / PROXY / QUOTED / BLOCKED，核对原理图和器件物理引脚。所有审核记录原始路径和复现指令。

## 5. 阶段放行（严格禁止把研究替代成已完成设计）

- G0 **SOURCE_READY**：开源来源、许可证/采购、厂商模型、参数齐全。
- G1 **SIM_REPRODUCED**：至少一套完整厂商/实用器件模型 0 V 冷启、低线、满载成功，波形经独立复算；另有真实负载和故障仿真。
- G2 **COST_QUOTED**：HV 子系统按同批量中国大陆来源采购、包括必需保护/分摊/连接，真实可下单的预算 < ¥60；给出成本敏感性和最差价格。
- G3 **EDA_VALIDATED**：独立候选 KiCad 原理图、PCB、ERC 0、DRC 0（采用有根据的绝缘设计）、0 未连、封装和管座完成实物尺寸验证。
- G4 **EVT_REVIEW**：独立高压测试计划、绝缘/热/关断/残压证据审查；仅经人工同意后制作受控验证板。G1/G2/G3 不能自动推出制造安全。
- 当前 **仅 G0 部分资料已取得**；G1–G4 均为 NOT DONE。没有完成新一轮器件级仿真或投板。

## 6. 开源与原始证据索引

- R11: `projects/NXT-M3/r11/BLOCKER_CLOSURE_REPORT.md`; `POWER_SIMULATION_REPORT.md`; `GATE0_SAFETY_ASSESSMENT.md`.
- R10: `projects/NXT-M3/r10/BOM_R10_COST.csv`.
- UCC3803 project: https://github.com/drkmsmithjr/NixiePowerSupply (KiCad + SimCalcFiles + LTspice; 已披露初始工作点收敛问题).
- LM3488 flyback: https://github.com/esynr3z/nixie-ps (KiCad + LTspice + 实测 5 V 附近高压电流；使用定制 EFD15).
- LT3757 flyback: https://github.com/tonyp7/170v-nixie-power-supply (BOM、Gerber、原理图图片/PDF；Coilcraft DA2032-ALB).
- TI: https://www.ti.com/product/UCC3803 ; https://www.ti.com/product/LM3488 ; https://www.ti.com/product/LM3478 ; https://www.ti.com/product/LM5155 .
- 官方模型可获得性不代表 ngspice 中模型已通过。资料/许可如不能确认，应标记 UNKNOWN。
