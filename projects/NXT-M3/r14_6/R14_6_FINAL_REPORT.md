# Σ / NXT-M3 R14.6 工程与制造放行评估

**已交付可编辑 KiCad 10.0.8 工程。EVT、制造及高压上电均为 HOLD。** 从实际 R14.5 实板关闭 19 项未连接及 24 项净距违规。剩余 65 项未连接、79 项净距违规。30/30 阴极、180/180 端点保持铜连通，原有铜分组无回退。 [KiCad 工程](eda/NXT-M3-R14.6.kicad_pro) · [PCB](eda/NXT-M3-R14.6.kicad_pcb) · [原生结果](ROUTING_GATE_RESULTS.json)

## 实际设计修改

- 将 R81–R83 转至 F.Cu，重走两段反馈链铜，关闭 R81.1→C47.1 与 R83.2→R84.1。反馈与残压链的 5 项外部高压违规降至 0。 [外部净距台账](HV_EXTERNAL_CLEARANCE.csv)
- C48 改为 KEMET 2220 C0G 1 kV 的原厂中密度焊盘，铜距由 1.80 增至 3.80 mm。避开 C47 庭院并接通两端，开关封装违规由 4 项减为 3 项。该吸收件继续 DNP。 [开关封装 ECR](SWITCH_PACKAGE_ECR.md)
- U6、U13、U14 改用 TI DGK0008A 推荐焊盘，改接 U14 三条入口。关闭 18 项低压 IC 本征违规，U1/U11 的 16 项仍 HOLD。 [34 项资格台账](LV_IC_CLEARANCE_QUALIFICATION.csv)
- C35 迁至 U13 同侧，恢复 OVP 测量端和局部地回路。其余本轮接通包括 U23 的锁存、时钟及清除分支，以及部分 GND、3V3、BIAS_S 与 HV_COMP 铜组。 [保护端点](PROTECTION_NET_CONNECTIVITY.csv) · [四级 595 铜分组](SHIFT_REGISTER_CONNECTIVITY.csv)
- 实板新增 370 段走线与 17 个过孔，替换或移除 17 段旧走线。130 × 80 mm、四层、MH1–MH4、J2–J6、33 个背面线束焊盘和 7.50 mm 阴极阵列节距均经原生脚本回归。六个专用管座孔没有恢复。最终原理图节点映射与基线一致。 [PCB 对象差异](evidence/object-and-net-diff.json)

## 原生回归

| 检查 | R14.5 重跑 | R14.6 保存后重开 |
| --- | ---: | ---: |
| ERC 错误 / 警告 | 0 / 0 | 0 / 0 |
| 原理图–PCB parity | 0 | 0 |
| 原生未连接 | 84 | 65 |
| 标准 / 全走线 DRC 净距 | 103 / 103 | 79 / 79 |
| 外部高压净距 | 5 | 0 |
| MMBTA42 本征 | 60 | 60 |
| 低压 IC 本征 | 34 | 16 |
| 开关封装本征 | 4 | 3 |
| 阴极端点 | 180/180 | 180/180 |
| J6 保护端点 | 39/49 | 39/49 |
| 其他保护审查对 | 14/23 | 20/23 |

原生差异无新增违规或短路，规则逐字节相同，无局部规则例外。两个独立目录按相同构建阶段生成的 PCB 与交付板 SHA-256 一致。 [原始报告](evidence/after) · [分类差异](DRC_BEFORE_AFTER.csv) · [复现记录](evidence/reproducibility.json)

## 制造门禁

[可机器读取的门禁结论](GATE_DECISIONS.json)

| 门禁 | 判定 | 依据与剩余风险 |
| --- | --- | --- |
| CATHODE_ROUTING | PASS | 30/30 阴极，180/180 端点，基线连接分组保留。 |
| SHIFT_REGISTER_CHAIN | FAIL | SER2、SER3、SR_CLK_BUS、HC_CLEAR_N 各剩 1 项。 |
| FULL_BOARD_ROUTING | FAIL | 65 项开路，原生 DRC 退出 5。 |
| LV_IC_CLEARANCE | HOLD | 18 项实施焊盘整改。16 项 RPW 违规和电气、制造资格待闭。 |
| MMBTA42_INSULATION | HOLD | 全部 60 项继续触发规则。装配空气距、爬电、实测应力及材料证据未齐。 |
| SWITCH_NODE_CLEARANCE | HOLD | D3/Q32 三项仍触发筛查，重复峰值和最坏热态未知。 |
| HV_EXTERNAL_CLEARANCE | PASS | 5/5 外部原生筛查项关闭。装配与跨层介质资格仍在制造门。 |
| PROTECTION_CONNECTIVITY | FAIL | J6 39/49、其他 20/23。OVP 串链、整流母线、看门狗及许可仍开。 |
| POWER_SIMULATION | HOLD | 8 个代理案例可复跑。实板启动、异常、保护、泄放和重复峰值未验证。 |
| MECHANICAL_ASSEMBLY | HOLD | 33 个板端映射已核对，管座实件、焊点保持力和三维绝缘待证。 |
| BOM_COMPLETENESS | CONDITIONAL | 322/322 原生位号，170 位号精确 MPN 未填，器件选型仍开放。 |
| PROCUREMENT_READINESS | HOLD | 6/80 个装机采购组有公开人民币价，正式批量报价和实物配置待核。 |
| EVT_RELEASE | HOLD | 剩余开路、封装、保护和装配验证均阻塞。 |
| MANUFACTURING_RELEASE | HOLD | 工艺、材料、绝缘、供货及试验门禁待闭。 |
| HV_POWER_ON | HOLD | 禁止对该工程对应实板进行高压上电。 |

## 阻塞与下一轮整改

- [剩余 65 项逐点](BLOCKED_ROUTES.csv) 和 [按网汇总](UNCONNECTED_NETS.csv) 指出 GND 剩 12、3V3 剩 4、HV_BUS 剩 4。U21/U22/U23 逃逸区需为 SER2/SER3 和 U22 的时钟清除预留过孔区。现有四层内部铜受外层阳极投影限制，先在现层叠重划阳极和显示控制走廊，再复核 180 对端点。本轮未触发板层降级或分板决策。
- 将 OVP 串链、L3–D3–Q32–C47 功率环路、U11→U17 供电切断和 J6 许可/地列为下一轮联动重布区域。根据仍连通的端点和功率回流审查结果规划，不靠删除保护铜或缩减开关筛查值接线。 [保护与仿真](POWER_AND_PROTECTION_REVIEW.md)
- 与板厂锁定四层材料、CTI、铜重、钢网和贴装工艺，取得管座/焊缝/金属件的实物间距，补齐 D3/Q32 与晶导阵列的装配及故障资格。 [高压绝缘](INSULATION_REVIEW.md) · [低压 DFM](LV_IC_DFM.md) · [线束装配](MECHANICAL_ASSEMBLY.md)
- 一块板的材料预算 ¥155.82–688.61，三块系统 ¥444.31–2,042.68。三块按公开价可测算的子集现金 ¥366.46，三块 EVT 条件预算 ¥1,996.39–5,720.76。价格覆盖按装机位数为 25.7%，正式成交报价与完整 MOQ 现金额待确认。 [成本与采购](COST_R14_6.md)

## 独立审查

本任务的独立 Worker 使用 DeepSeek Harness。主会话负责 PCB 串行集成、原生工具核验、证据复核和门禁决定。 [Harness 记录](evidence/harness) · [复现说明](REPRODUCE.md)
