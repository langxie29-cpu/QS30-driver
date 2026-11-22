# NXT-M3 R14.2 · 原厂封装与绝缘协调工程结论

```text
Q1_INSULATION_DECISION = HOLD
EVT_RELEASE = HOLD
MANUFACTURING_RELEASE = HOLD
```

2026-11-22。冻结起点为本地 `nxt/nxt-m3-safety-layout-r14` 的 `5470020e10f5d6d98f6e21cc93951ca573e20965`。执行分支为 `nxt/nxt-m3-insulation-r14-2`。仓库为 `langxie29-cpu/QS30-driver`。执行前从 GitHub 查询未见 R14 基线分支，已在本地核对该提交对象、工程源与历史证据。 [复现](REPRODUCE.md)

## Q1 工程判定

晶导 MMBTA42（C4749118）原厂署名文件日期 2020.12、页 3 标识 201210。核对了 SOT-23 的 1=B、2=E、3=C、焊盘及机械尺寸。原厂名义几何把 C–B 和 C–E 的最短铜距从 **0.6552 mm** 增至 **1.1102 mm**，B–E 从 1.3000 mm 变为 1.1000 mm。R14.1 向外延伸的铜尾对三个同封装最短间距的损失为 **0 mm**。原厂投影距现行 2.00 mm 筛查仍差 0.8898 mm，直接替换还会失去四条现有引出接触。 [原厂核查](MMBTA42_MANUFACTURER_FOOTPRINT_AUDIT.md) · [几何对照](Q1_PAD_GEOMETRY_BEFORE_AFTER.csv) · [引出线证据](evidence/q1_track_contacts.json)

在 170 V 和 195 V 持续应力的计算中，原厂投影不满足通用 PD2 材料组 II/III 的名义爬电筛查。确认适用 PCB 专用列、其他有资格的材料路径或 IEC 60664-3 涂覆可改变技术结论。合格的终端产品分类、海拔、污染等级、CTI、装配后最短路径和 B/E/C 实际最坏差分应力仍缺失。C–B/C–E 在截止代理中分别接近 170 V 和 195 V，浮置、启停与反向回灌的实际峰值仍没有经资格确认的边界。HOLD 解除条件和四种方案的适用性已逐项登记。 [绝缘决策](INSULATION_COORDINATION_DECISION.md) · [电压矩阵](INSULATION_VOLTAGE_MATRIX.csv) · [195 V 截止代理](evidence/off_195/)

工程继续使用 R14.1 原生 PCB、原理图、局部库和规则。原厂铜形状已在 KiCad 坐标中进行碰撞复核，未将其装入交付板。该选择保留已完成的六组铜连通，并与标准条件和真实电压尚未确认时的停改要求一致。无带电高压试验、采购、制造或高压电源拓扑变化。 [原生工程](../r14/eda/NXT-M3-R14.kicad_pro)

## KiCad 10.0.8 原生复跑

| 检查 | 冻结基线本地复跑 | R14.2 交付工程 |
| --- | ---: | ---: |
| ERC，沿用四项忽略类别 | 0 errors / 0 warnings | 0 / 0 |
| DRC clearance | 253 | 253 |
| 未连接 | 337 | 337 |
| Schematic–PCB parity | 0 | 0 |
| Q1 已登记端点 | 6/6 | 6/6 |
| J6 已登记端点 | 36/49 | 36/49 |
| Q1 C–B / C–E 违规 | 2，均 0.6552 mm | 2，均 0.6552 mm |

ERC 四项忽略沿用全局标签仅出现一次、四线交接、SPICE 模型、封装过滤器匹配。DRC 的 253 个违规以类型和对象 UUID 与归档完全一致。未连接总数及各网络计数一致，部分飞线端点的 KiCad 原生列举在同一板上会变化，原始差异计数记录于审计 JSON。Q1/J6 的复核基于 pcbnew 实际铜连通图。新导出的原理图针脚到网络映射与归档一致。交付工程与指定提交的 `r14/eda` 内容相同，因此报告适用于前后状态。 [ERC](evidence/ERC.rpt) · [DRC 与 parity](evidence/DRC.rpt) · [端点审计与工程哈希](evidence/terminal_audit.json) · [原生调用记录](evidence/native_commands.json)

## 热安全交叉检查

晶导 p. 1 规定环境 25 °C（另注除外），P_C = 0.35 W、RθJA = 357 °C/W、T_J = 150 °C。p. 2 图 2 在 25 °C 后降额，未给参考装板铜面积、热态 SOA 或瞬态热阻。按 `min(0.35, (150−Ta)/357)` 的稳态筛查，25/60/85 °C 分别约为 **0.350/0.252/0.182 W**。 [晶导 p. 1–2](https://ruelectronics.com/files/Datasheet_MMBTA42_Jingdao-f4487c6fcbed9717aa589a3e4524c22c.pdf)

R14 的 195 V 持续供能代理给出 **97.328 V × 4.916 mA ≈ 0.4784 W**，25 °C 下超出 0.350 W 约 36.7%，4 s 吸收 1.914 J。19.8 kΩ 负载、零管压降的独立上包络为 `195²/(4×19,800)=0.4801 W`。170 V 持续半导通代理为 0.3634 W，也高于 25 °C 额定。理想切断后 3.63 µF 储能工况约吸收 29.67 mJ，需按实际起始结温、脉冲宽度、重复率、瞬态热阻及二次击穿 SOA 判断。0.4784 W 来自等效 C–E 故障路径，是真实晶体管需要承受的应力情景之一，代理 BJT 本身的电流与故障电阻的电流分别记录。 [R14 原始测量](../r14/evidence/simulation/cathode_measurements.csv) · [故障网表](../r14/evidence/simulation/half_195_sustain/circuit.cir)

四秒是仿真观察窗。持续供能模型没有证实保护会在此时间内动作，理想断供模型从初始条件移除供能。R14.1 的 0–5 V STOP 代理能检查逻辑状态及重新 ARM 的顺序，实际切断延迟、卡通常供、温升与脉冲 SOA 仍需实证。即使绝缘条件满足，持续半导通热风险仍是独立放行阻塞项。 [热/SOA 证据](../r14/THERMAL_SOA_REVIEW.md) · [STOP 代理](../r14/evidence/r14_1/proxy/measurements.json)

## 放行条件

- **Q1 绝缘 HOLD** 需取得产品分类、装配路径与最坏电压证据，并完成所选裸板、涂覆、重布或替代封装方案的资格验证。 [绝缘决策](INSULATION_COORDINATION_DECISION.md)
- **EVT HOLD** 仍有 Q1 绝缘和热态 SOA、J6 余下 13 组铜连通、断供及残压保护实证等阻塞。 [R14 阻塞登记](../r14/R14_BLOCKER_REGISTER.md)
- **制造 HOLD** 还需冻结合格的板材/叠层、装配与检验工艺，完成整板开路和高压净距处置并通过正式放行审查。 [R14.1 工程结论](../r14/R14_1_COMPLETION.md)

## 协作与交付

沿用 R13 已登记的 sealed-text Worker 配置和验收边界。只读预检通过，Worker 工具集合为空，关闭后台模型请求。本轮付费 Worker 调用 0 次，原生 EDA、证据计算、工程决策及 Git 写入由 Codex 执行。 [预检](evidence/worker_doctor.json) · [既有协作配置](../r13/config.json)
