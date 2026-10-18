# QS30-6 REV.A 工程交接总页（HANDOVER）

版本：REV.A ｜ 更新：2026-10-18 ｜ 状态：**软件侧工程包完成，实物侧未开始，禁止投板/下单**

> 本页是全部交付物的单一入口。所有数字均由机器可读结果生成，跨文档一致性由
> `design/doc_number_check.py`（5/5 PASS）守护；任何"已完成"的表述都对应可复现命令。

## 1. 结论（先读这一段）

| 维度 | 状态 | 依据 |
|---|---|---|
| 原理图/网表/BOM/封装草案/预布局 | **已完成（软件侧）** | 227 器件 / 736 引脚 / 172 网络 / 60 通道；ERC 19 项 0 错 0 警；DRC 预检 14/14 |
| 升压 + OVP 仿真 | **已完成（软件侧，分级证据）** | 开关级 SPICE 171.99 V/95.9%；平均模型闭环 8/8；OVP 保护逻辑 7/7；OVP 时序 7 组；行为模型 S1–S10 |
| 封装冻结（管座） | **未冻结** | 13 脚管座实测 H03 未提交（14 个 TBD 字段，脚本校验"无猜测尺寸"） |
| 实物验证（H02–H08） | **未开始** | 证据模板 0/7 已提交（`hold_closure_report.md`） |
| 原生 EDA 工程/ERC/DRC（H01/H09） | **未执行** | 环境无立创EDA/KiCad（`open_issues.md` I-19/I-20） |
| **投板/下单/Gerber** | **🚫 RELEASE BLOCKED** | `preflight_checklist.md`：机器检查 11/11 PASS，但 HOLD CLOSED 0/9 |

## 2. 交付物索引

### 2.1 仿真与证据（已执行）

| 交付物 | 路径 | 状态/要点 |
|---|---|---|
| SPICE 验证报告（自检+功率级+平均模型+OVP） | `sim/results/spice_validation.md` | 4 项自检/功率级 171.99 V/闭环 8/8/OVP 7/7 |
| 平均模型闭环与阶跃 | `sim/boost_averaged*.cir`、`spice_averaged_closed_loop.png` | 172.18 V、duty 0.931、负载 0.25 V、输入 3.90 V/8 ms |
| OVP 保护逻辑 + 时序 | `sim/boost_ovp_logic.cir`、`spice_ovp_latch.png`、`docs/ovp_timing.md` | 触发 198.92 V；复位最小脉宽 0.2 ms；不复位保持 |
| 环路参数扫描 | `docs/loop_scan.md`、`loop_scan_heatmap.png` | 27 组；Kp 主导下探；26/27 稳定 |
| 行为模型 S1–S10 | `design/sim_boost.py`、`sim/results/` | 启动/空载/短路/泄放/OVP 锁存 |
| 收敛性 | `sim/results/convergence.md` | Ts/80 收敛（≤0.4%） |
| **未执行** 厂商 ngspice/LTspice 网表 | `sim/boost_uc3843.cir` | 参考网表，文件头已注明；开关级闭环受算力限制（I-23） |

### 2.2 设计数据与文档

| 交付物 | 路径 |
|---|---|
| 逐引脚网表 / BOM / 通道映射 | `netlist/QS30-6_REV.A_netlist.csv`、`bom/QS30-6_REV.A_BOM.csv`、`docs/channel_mapping.csv` |
| 管座符号规范 / 封装草案 / 1:1 校对页 | `symbols/QS30-1_symbol_spec.json`、`symbols/QS30-1_socket_footprint_draft.json`、`docs/footprint/QS30-1_管座_1比1校对页.pdf` |
| 原理图 PDF / 系统框图 / 预布局 | `docs/schematic/QS30-6_REV.A_原理图连接表.pdf`、`docs/prelayout/QS30-6_REV.A_prelayout.pdf` |
| **审查包（29 页）** | `docs/QS30-6_REV.A_审查包.pdf` |
| ERC / DRC 预检 / 规则矩阵 | `docs/erc_report.md`、`docs/drc_precheck.md`、`docs/pcb_rule_matrix.csv` |
| 测试计划 + 机器可读一致性 | `docs/test_plan.md`、`docs/test_plan.csv`、`docs/test_plan_check.md` |
| 固件约束（派生） | `docs/firmware_constraints.md` |
| BOM 选型复核 / 热浪涌复核 | `docs/bom_review.md`、`docs/thermal_review.md` |
| 投板前检查清单 | `docs/preflight_checklist.md` |
| 决策/问题/来源/变更/冻结登记 | `design_decisions.md`、`open_issues.md`、`source_register.md`、`REV_A_CHANGELOG.md`、`HOLD_REGISTER.md` |

### 2.3 HOLD 证据与签署

| 交付物 | 路径 |
|---|---|
| 10 个证据模板（期望值自动填入） | `docs/evidence/` |
| 自动校验报告（当前 0/7 已提交） | `docs/hold_closure_report.md` |
| 进度看板 + 关键路径 | `docs/hold_dashboard.md` |
| 签署联动（CLOSED=证据通过+人工签审） | `docs/HOLD_SIGNOFF.csv`、`docs/hold_signoff_report.md` |
| 框架自测（合成数据，证明判据有效） | `docs/evidence_selftest.md` |

## 3. 设计基线数字（单一事实来源）

- 器件 **227** / 引脚 **736** / 网络 **172** / 已用通道 **60**（2×HV5622，64 路中 4 路备用）；
- HV_BUS **172.18 V**；OVP **198.8 V**（SPICE 首次触发 198.92 V）；功率级效率 **95.9%**；
- 平均模型闭环判据 **8/8**；OVP 保护逻辑 **7/7**；DRC 预检 **14/14**；测试计划 **5/5**；
- BOM 复核 **5/5**；文档一致性 **5/5**；热/浪涌：温升 0.7–6.3 °C、I²t 0.0010 A²·s。

## 4. 证据分级（D-18）

| 级别 | 含义 | 本项目 |
|---|---|---|
| A | 厂商/器件级 SPICE | **未执行**（无 ngspice/LTspice） |
| B | 仓库自带 SPICE（有解析对照） | 已执行：功率级、平均模型闭环、OVP 保护逻辑、OVP 时序 |
| C | 行为模型（S1–S10，Ts/80 收敛） | 已执行：启动/过冲/短路/泄放/锁存/复位 |
| D | 实物实测 | **未开始**（H02–H08 证据 0/7） |

**任何 B/C 级结论都不能替代 D 级实测**；器件级尖峰、EMI、温升、PPTC 时序、环路相位裕度
必须以 H06 实测为准。

## 5. HOLD 解除路径（放行前唯一路径）

1. 实物测试 → 回填 `docs/evidence/*.csv`；
2. `python design/evidence_check.py`（未提交/部分/通过/失败）；
3. `docs/HOLD_SIGNOFF.csv` 填写签署人/日期/版本 → `python design/hold_signoff.py`；
4. 在立创EDA 重建工程并跑原生 ERC/DRC（H09），记录归档；
5. `python design/preflight_checklist.py` 必须变为"机器检查全绿 + HOLD 全 CLOSED"；
6. 人工按 `HOLD_REGISTER.md` 签署放行后才允许生成/释放 Gerber。

当前阻塞项（均非软件可关闭）：
H01 旧基线原件、H02 QS30-1 实物管、H03 13 脚管座样件实测、H04 焊好的驱动板（walking-one）、
H05 样机低压实测、H06 高压测试条件、H07 结构/标准输入、H08 整机 RF、H09 立创EDA。

## 6. 复现（从仓库根目录）

```powershell
cd design
python build.py                 # 网表/BOM/ERC/映射
python export_extra.py          # BOM_qty/分页网表/符号封装映射/规则矩阵
python drc_precheck.py          # 14 项网表级 DRC 预检
python evidence_templates.py; python evidence_check.py
python hold_dashboard.py; python hold_signoff.py
python test_plan_check.py; python firmware_constraints.py
python bom_review.py; python thermal_review.py; python preflight_checklist.py
python render.py; python footprint_draft.py      # 原理图 PDF/预布局/1:1 页
python loop_scan.py; python ovp_timing_scan.py   # 环路扫描/OVP 时序（各约 1 分钟）
python sim_boost.py; python sim_check.py         # 行为模型 S1–S10 + 收敛性（约 1–2 分钟）
python doc_number_check.py; python review_package.py   # 一致性 + 审查包
cd ..\sim
python spice_validation.py      # 自检 + 功率级 + 平均模型 + OVP（约 35 s）
```

## 6.5 从零复现验证（本轮执行）

在临时副本中清空所有生成物后按第 6 节顺序重跑全部脚本，结果与工作区**逐项一致**：

| 指标 | 工作区 | 复现副本 |
|---|---|---|
| 器件/引脚/网络/通道 | 227/736/172/60 | 227/736/172/60 |
| 功率级 Vout / 效率 | 171.987 V / 95.867% | 171.987 V / 95.867% |
| 平均模型闭环 | 通过 | 通过 |
| OVP 触发 / 峰值 | 198.921 / 201.925 V | 198.921 / 201.925 V |
| DRC 预检 | 14/14 | 14/14 |
| 投板判定 | RELEASE BLOCKED | RELEASE BLOCKED |
| 热复核 I²t / 温升 | 0.0010 A²s / 0.74–6.28 °C | 相同 |
| 环路扫描 | 27 组 / 1 组不稳定 | 27 组 / 1 组不稳定 |

脚本流水线 `FINAL_EXIT=0`，审查包页数一致（本次交接页加入前为 28 页）。
唯一非确定性来源为图像渲染的字体缓存，不影响任何判定。

## 7. 环境限制（如实记录）

- 无立创EDA/KiCad（安装需管理员）→ 无原生工程/ERC/DRC（I-19/I-20，H09）；
- 无 ngspice/LTspice（下载 403）→ 厂商网表未执行；已用自带 SPICE 子集 + 平均模型 + 行为模型组合替代（I-23）；
- 无 QS30-1 实物管、管座样件、高压测试条件 → H02–H08 无法关闭；
- 无旧基线原件 → H01 无法关闭。

## 8. 版本

REV.A r13（2026-10-18）。变更历史见 `REV_A_CHANGELOG.md`；冻结登记见 `HOLD_REGISTER.md`。
