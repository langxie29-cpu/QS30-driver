# QS30-6 REV.A — 六位静态辉光钟（ESP32-S3 / 南昌 QS30-1 / 立创EDA）

**工程状态：HOLD —— 可继续 PCB 预布局与实物验证，禁止投板、禁止生产放行。**
本仓库是 REV.A 的**可复现设计输入 + 已执行的仿真/检查证据**，不是已签审的完整 EDA 工程。

- 设计输入：`QS30-6_REV.A_ESP32_QS30-1_立创EDA工程交接_修订01.docx`（旧交接，已全程审查）
- 本基线：REV.A r1（2026-10-18）
- 规模：**227 个器件 / 736 个引脚 / 172 个网络 / 60 路数字阴极 / 2×HV5622**
- 自动一致性检查：**19 项全部 PASS（0 ERROR / 0 WARN）**，见 `docs/erc_report.md`

---

## 0. 交接入口

**先读 [`docs/HANDOVER.md`](docs/HANDOVER.md)**：交付物索引、证据分级、HOLD 解除路径、
从零复现验证结果与"禁止投板"结论。

## 1. 交付物索引

| 类别 | 文件 |
|---|---|
| 设计决策 | [`design_decisions.md`](design_decisions.md) |
| 未关闭问题 | [`open_issues.md`](open_issues.md) |
| 资料登记 | [`source_register.md`](source_register.md) |
| 变更记录 | [`REV_A_CHANGELOG.md`](REV_A_CHANGELOG.md) |
| HOLD 闸门 | [`HOLD_REGISTER.md`](HOLD_REGISTER.md) |
| 网表（逐引脚，权威） | [`netlist/QS30-6_REV.A_netlist.csv`](netlist/QS30-6_REV.A_netlist.csv) ｜ [`netlist/QS30-6_REV.A_nets.csv`](netlist/QS30-6_REV.A_nets.csv) ｜ [`netlist/QS30-6_REV.A_netlist.json`](netlist/QS30-6_REV.A_netlist.json) |
| BOM | [`bom/QS30-6_REV.A_BOM.csv`](bom/QS30-6_REV.A_BOM.csv) ｜ 已验证子集 [`bom/QS30-6_REV.A_BOM_verified_only.csv`](bom/QS30-6_REV.A_BOM_verified_only.csv) |
| 通道映射 | [`docs/channel_mapping.csv`](docs/channel_mapping.csv) ｜ [`docs/schematic/QS30-6_REV.A_通道映射表.png`](docs/schematic/QS30-6_REV.A_通道映射表.png) |
| QS30-1 脚号映射 | [`docs/qs30_1_pin_mapping.csv`](docs/qs30_1_pin_mapping.csv) |
| 原理图（连接表式分页图 + PDF） | [`docs/schematic/QS30-6_REV.A_原理图连接表.pdf`](docs/schematic/QS30-6_REV.A_原理图连接表.pdf)（11 页：系统框图 + 9 页分页连接表 + 通道映射表）｜ `docs/schematic/page_01.png` … `page_09.png` |
| 系统框图 | [`docs/schematic/QS30-6_REV.A_系统框图.png`](docs/schematic/QS30-6_REV.A_系统框图.png) |
| PCB 预布局 | [`docs/prelayout/QS30-6_REV.A_prelayout.png`](docs/prelayout/QS30-6_REV.A_prelayout.png) ｜ `.pdf` |
| BOM 数量汇总（114 组，含 DNP） | [`bom/QS30-6_REV.A_BOM_qty.csv`](bom/QS30-6_REV.A_BOM_qty.csv) |
| 逐页网络清单（立创EDA 录入用） | `netlist/by_sheet/{01_PWR,02_MCU,03_DRV,04_HV,05_TUBE,06_TP}_nets.csv` |
| 符号↔焊盘↔原厂脚号总表（H09 证据） | [`docs/symbol_footprint_mapping.csv`](docs/symbol_footprint_mapping.csv) |
| PCB 规则矩阵（H07 占位） | [`docs/pcb_rule_matrix.csv`](docs/pcb_rule_matrix.csv) |
| ERC 记录 | [`docs/erc_report.md`](docs/erc_report.md) |
| **DRC 预检（网表级，14/14 PASS）** | [`docs/drc_precheck.md`](docs/drc_precheck.md) ｜ [`drc_precheck.json`](docs/drc_precheck.json) ｜ 脚本 [`design/drc_precheck.py`](design/drc_precheck.py) |
| **HOLD 进度看板** | [`docs/hold_dashboard.md`](docs/hold_dashboard.md)（填写进度 + 关键路径） |
| **HOLD 签署与关闭联动（本次新增）** | 签署表 [`docs/HOLD_SIGNOFF.csv`](docs/HOLD_SIGNOFF.csv) ｜ 报告 [`docs/hold_signoff_report.md`](docs/hold_signoff_report.md) |
| **HOLD 证据模板与自动校验** | 模板 [`docs/evidence/`](docs/evidence/README.md)（10 个 CSV，含期望值与判据）｜ 校验 [`design/evidence_check.py`](design/evidence_check.py) ｜ 状态报告 [`docs/hold_closure_report.md`](docs/hold_closure_report.md) ｜ 框架自测 [`docs/evidence_selftest.md`](docs/evidence_selftest.md) |
| 立创EDA 构建步骤 | [`docs/lceda_implementation_guide.md`](docs/lceda_implementation_guide.md) |
| 上电验证计划 | [`docs/test_plan.md`](docs/test_plan.md) |
| 升压/OVP 仿真 | [`sim/README.md`](sim/README.md) ｜ 结果 `sim/results/`（6 张图 + 10 份 CSV + summary.json + convergence） |
| **平均模型闭环仿真** | `sim/boost_averaged.cir` ／ `sim/boost_averaged_steps.cir` ｜ 结果 [`sim/results/spice_averaged_closed_loop.png`](sim/results/spice_averaged_closed_loop.png) |
| **OVP 保护逻辑 SPICE** | `sim/boost_ovp_logic.cir` ｜ 结果 [`sim/results/spice_ovp_latch.png`](sim/results/spice_ovp_latch.png)（触发/锁存/泄放/复位/再触发，7 项判据） |
| **OVP 时序回归（本次新增）** | 复位脉冲宽度/锁存保持扫描：`design/ovp_timing_scan.py` ｜ [`docs/ovp_timing.md`](docs/ovp_timing.md) |
| **测试计划一致性检查** | `docs/test_plan.csv`（37 项机读）＋ `design/test_plan_check.py` ｜ [`docs/test_plan_check.md`](docs/test_plan_check.md) 5/5 PASS |
| **固件约束清单（本次新增）** | `design/firmware_constraints.py` 派生 ｜ [`docs/firmware_constraints.md`](docs/firmware_constraints.md) ／ [`.json`](docs/firmware_constraints.json)（8 控制脚、64 位帧、13 条约束） |
| **文档数字一致性检查** | `design/doc_number_check.py` ｜ [`docs/doc_consistency.md`](docs/doc_consistency.md) 5/5 PASS |
| **BOM 选型复核** | `design/bom_review.py` ｜ [`docs/bom_review.md`](docs/bom_review.md)（14 关键件降额/替代料，5/5 PASS） |
| **热/浪涌复核（本次新增）** | `design/thermal_review.py` ｜ [`docs/thermal_review.md`](docs/thermal_review.md)（HV5622 温升 0.7–6.3 °C；浪涌 I²t 0.0010 A²s） |
| **投板前检查清单（本次新增）** | `design/preflight_checklist.py` ｜ [`docs/preflight_checklist.md`](docs/preflight_checklist.md)（**RELEASE BLOCKED**：机器检查 11/11，HOLD 0/9） |
| **SPICE 子集求解器（仓库自带）** | [`sim/minispice.py`](sim/minispice.py) ｜ 验证网表 `sim/spice_tests/` ｜ 结果 [`sim/results/spice_validation.md`](sim/results/spice_validation.md) ｜ [`spice_boost_summary.json`](sim/results/spice_boost_summary.json) ｜ 波形 [`spice_boost_waveforms.png`](sim/results/spice_boost_waveforms.png) |
| 审查包（合并 PDF，15 页） | [`docs/QS30-6_REV.A_审查包.pdf`](docs/QS30-6_REV.A_审查包.pdf) |
| QS30-1 符号建库说明 / 规格 | [`symbols/README.md`](symbols/README.md) ｜ [`symbols/QS30-1_symbol_spec.json`](symbols/QS30-1_symbol_spec.json) |
| 管座封装草案（TBD，H03） | [`symbols/QS30-1_socket_footprint_draft.json`](symbols/QS30-1_socket_footprint_draft.json) ｜ 1:1 校对页 [`docs/footprint/QS30-1_管座_1比1校对页.pdf`](docs/footprint/QS30-1_管座_1比1校对页.pdf) ｜ 实测工作表 [`docs/footprint/H03_管座实测工作表.md`](docs/footprint/H03_管座实测工作表.md) |
| 仿真收敛性证据 | [`sim/results/convergence.md`](sim/results/convergence.md) ｜ [`.json`](sim/results/convergence.json) |
| 原始资料证据（扫描/渲染） | [`docs/source_scans/`](docs/source_scans/)（QS30-1 原厂页、HV5622 引脚表/真值表、CD40109B 引脚注记、TL431/74HC08/UC3843/USBLC6 引脚图） |
| 设计数据库与生成器 | [`design/model.py`](design/model.py) ｜ [`design/sheet_lv.py`](design/sheet_lv.py) ｜ [`design/sheet_hv.py`](design/sheet_hv.py) ｜ [`design/build.py`](design/build.py) ｜ [`design/render.py`](design/render.py) ｜ [`design/sim_boost.py`](design/sim_boost.py) |

## 2. 关键结论（VERIFIED）

1. **QS30-1 电极映射由原厂说明书直接确定**：2=A；3=K0、4=K9、5=K8、6=K7、7=K6、9=K5、
   10=K4、11=K3、12=K2、13=K1；**1、8 脚为非显示内部电极，悬空不接**。无小数点/冒号电极。
2. **QS30-1 工作参数（原厂基本参数表）**：起辉 ≤150 V、熄灭 ≥100 V、Ea=170 V、Ik=1.5/2.25/3 mA、
   Ra=20 kΩ、寿命 1000 h、φ30.2、总高 34±1.5、管基 GB 787-74 J13-1A。
3. **HV5622 每片 32 路输出** → 60 路需求用 **2 片（64 路）**，不是 3 片；帧长 **64 bit**。
4. **HV5622 危险态**：POL=低且 BL=低 → 全部输出导通。故 POL 硬件固定接 DRV_VDD，
   BL 在 12 V 域下拉（默认消隐），并且高压母线受 DRV_PG 门控。
5. **ESP32-S3-WROOM-1 焊盘 1–41、USB D−/D+ = GPIO19/20、strapping = GPIO0/3/45/46** 与交接表一致。
6. **TL431（DBZ/SOT-23-3）引脚是 1=CATHODE、2=REF、3=ANODE**（旧稿按 SOT-23-5 顺序写错，已修正）。

## 3. 本 REV.A 已实施的设计（要点）

- 电源：12 V → 5.08 V（TPS54202）→ 双肖特基 OR → 3.315 V（SY8089A）；DRV_VDD 由默认关断的
  高边开关供给；3.3 V 按 800 mA 分配；USB-C 仅逻辑供电（≤500 mA 限制写入固件要求）。
- 门控：EXT12_PG(10.80 V)、3V3_PG(3.107 V)、DRV_PG(10.41 V)、FAULT_OK → 74HC08 →
  DRV_VDD_EN / HV_EN；MCU 只能请求（GPIO16），复位/掉电默认全关。
- 高压：UC3843 升压 78 kHz → **172.18 V**；6×（2×10 kΩ/2 W）阳极限流；OVP **198.8 V**
  独立比较器 + 分立 SCR 锁存 + GPIO18 受控复位；200 kΩ 泄放（仿真 172→50 V 用时 3.84 s）。
- 驱动：2×HV5622（PQFP-44）+ 2×CD40109B 电平转换；60 路阴极映射表 + walking-one 验证要求。
- 布局：230×120 mm 建议外形、4 层、天线禁布/高压分区/隔离带，见预布局图。

## 4. 仿真结论摘要

### 4.1 功率级 SPICE（仓库自带 `sim/minispice.py`，已执行）

| 项目 | SPICE 结果 | 解析/理论 | 偏差 |
|---|---|---|---|
| 稳态输出 | **171.99 V** | 171.95 V（DCM 公式） | +0.02% |
| 电感峰值电流 | **503 mA** | 510 mA | -1.4% |
| 输出纹波（单周期） | **8.7 mVpp** | 9.0 mVpp | -3% |
| 效率（h=10 ns） | **95.9%** | 器件损耗估算 ≈96% | — |
| Coss 敏感性 | 100 pF 开关电容 → **91.0%** | ½CV²f≈0.12 W | 5 个百分点 |

求解器自检：RC（1.8 mV）、RL（0.46 mA）、二极管（5.6e-17 V）、B 源（1.0e-2 V）全部 PASS。
厂商 ngspice 网表 `sim/boost_uc3843.cir` **未执行**（环境无 ngspice）。

### 4.2 闭环/保护行为（`design/sim_boost.py`，行为模型，Ts/80）

| 场景 | 结果 |
|---|---|
| 启动（六管） | 172.08 V，过冲 180.75 V（+4.97%），未触发 OVP；浪涌峰值 2.91 A |
| 六管稳态 | 172.08 V，纹波 1.1 Vpp，效率 77.6% |
| 空载（消隐） | 172.19 V，过冲 187.4 V（+8.8%） |
| 反馈开路 | 198.80 V 触发 OVP 并锁存（142 ms）；受控复位后 558 ms 再触发 |
| 断电泄放 | 172 V → 50 V：**3.84 s** |
| 输出短路 10 Ω | 电流限流，输出 10.8 V，OVP 不误动 |

> 模型边界：行为级、非器件级 SPICE；开关损耗/振铃/反向恢复/温升未建模。ngspice 参考网表
> `sim/boost_uc3843.cir` **未执行**（本机无 ngspice/LTspice）。

## 5. 当前阻塞（必须优先关闭）

`H01` 旧基线、`H02` 实物管脚/工作点、`H03` 管座与封装、`H04` 驱动时序/位序、
`H05` 供电实测、`H06` 高压实测、`H07` 高压间距标准 → 任一未关闭**不得投板**；
`H08` RF、`H09` EDA 验收未关闭 **不得生产**。详见 `HOLD_REGISTER.md` / `open_issues.md`。

HOLD 关闭的证据模板已生成（`docs/evidence/`），填表后运行 `python design/evidence_check.py`
即可自动判断「未提交/部分/完整/失败」，通过后才进入人工签署（当前 0/7 已提交，符合"无实物数据"现状）。

最需要立即处理的三个务实动作：
1. 购样 13 脚管座并实测（H03）——这是唯一阻止 PCB 封装的机械项。
2. 单管夹具逐脚点亮 QS30-1 并记录 U_tube/I（H02/H06）。
3. walking-one 位序测试（H04）——固件 LUT 冻结前必须完成。

## 6. 复现方式

```powershell
cd design
python build.py        # 生成 netlist/、bom/、docs/*.csv、docs/erc_report.md
python render.py       # 生成 docs/schematic/、docs/prelayout/
python export_extra.py # 生成 BOM 数量汇总、逐页网络清单、符号/焊盘总表、规则矩阵
python footprint_draft.py  # 生成管座封装草案 JSON + 1:1 校对页
python review_package.py   # 生成 docs/QS30-6_REV.A_审查包.pdf
python sim_boost.py        # 生成 sim/results/（开关级仿真与图表）
python sim_check.py        # 行为模型步长收敛性检查
python sim/spice_validation.py  # 执行 minispice：解析解自检 + 升压功率级 SPICE + 步长/Coss 敏感性
python evidence_templates.py   # 生成 HOLD 关闭证据模板（期望值自动填入）
python evidence_check.py       # 校验已提交证据（未提交/部分/完整/失败）
python evidence_selftest.py    # 证据校验框架自测（合成数据，证明判据有效）
python hold_signoff.py         # HOLD 自动证据 + 人工签署联动（CLOSED 需两者同时满足）
python ovp_timing_scan.py      # OVP 复位脉宽/锁存保持扫描（约 90 s）
python test_plan_check.py      # 测试计划 ↔ 证据模板一致性（37 项，5 条规则）
python firmware_constraints.py # 从网表/映射表派生固件约束（GPIO/帧长/位序）
python doc_number_check.py     # 跨文档关键数字一致性（防 95.8%/158ms 类漂移）
python bom_review.py           # 关键器件降额/替代料/封装状态复核（14 件）
python thermal_review.py       # HV5622 功耗/温升估算 + PPTC 启动浪涌 I²t
python preflight_checklist.py  # 投板前汇总（HOLD + 全部机器检查 → RELEASE BLOCKED）
```

依赖：Python 3.12 + numpy + matplotlib（均已在本环境验证可用）。
设计数据唯一来源是 `design/*.py` 中的器件/连接定义；网表、BOM、连接表式原理图、
映射表均由同一份数据生成，避免"图-表-网表"不一致。

## 7. 环境限制与诚实声明

- 当前环境**没有**立创EDA、LTspice、ngspice；已验证：KiCad 只能通过 winget 安装且
  需要管理员权限（本会话非管理员，安装无法完成），ngspice 的 SourceForge 下载被 403 拦截。
  作为替代，仓库自带 `sim/minispice.py`（SPICE 子集求解器），已用**解析解**自检通过并
  **实际执行了升压功率级 SPICE 网表**（见 `sim/results/spice_validation.md`）；
  厂商 ngspice 网表 `sim/boost_uc3843.cir` 仍未执行。
  因此**没有**生成可编辑的立创EDA 工程，
  也**没有**执行原生 ERC/DRC 与 SPICE。替代交付物为：完整网表、BOM、封装定义要求、
  连接表式分页原理图（PDF）、立创EDA 逐步构建说明、可运行的 Python 开关级仿真。
- 管座 PCB 封装**未定义尺寸**（H03）；预布局只是分区与约束优先级，不是可投板版图。
- 全部器件状态见 BOM 的 `status` 列：`VERIFIED` / `PROVISIONAL` / `HOLD`；
  `BOM_verified_only.csv` 仅为资料已核对子集，**不是可下单清单**。
