# Σ / NXT-M3 · R14.4 P01 工程交付

2026-11-22。R14.4 可编辑整板从 R14.3 冻结基线 `3f9531a456b8a0195363034341071bc9ffd264d1` 修订。工程入口为 [NXT-M3-R14.4.kicad_pro](eda/NXT-M3-R14.4.kicad_pro)，整板为 [NXT-M3-R14.4.kicad_pcb](eda/NXT-M3-R14.4.kicad_pcb)。R14、R14.2、R14.3 和 R13 Harness 归档保留在独立分支的基线历史中。本轮由 Codex 使用本地工具修改、验证并提交。付费 Worker 调用 0 次，费用 0。

## KiCad 10.0.8 原生回归

| 核查 | R14.3 冻结整板 | R14.3 三路样片 | R14.4 整板 |
| --- | ---: | ---: | ---: |
| ERC error / warning | 0 / 0 | 0 / 0 | 0 / 0 |
| DRC 相异网络净距 | 253 | 18 | **157** |
| DRC 其他违规 | 0 | 0 | 0 |
| 原生未连接 | 337 | 0 | **331** |
| Schematic–PCB parity | 0 | 0 | 0 |
| Q1 指定端点 | 6/6 | 独立样片 | **6/6** |
| J6 相关保护端点 | 36/49 | 独立样片 | **36/49** |

DRC 常规与 `--all-track-errors` 均为 253 → 157，按类型和对象 UUID 比对新增 0。外部 HV/LV 及接口／MCU 项共 132 → 52，其他外部高压项 9 → 7，开关节点外部项 14 → 0。保留 60 项 MMBTA42 封装内候选例外、4 项 D3/C48/Q32 固有开关间距和 34 项低压封装净距。原生网表针脚到网络映射相同。958 个可比焊盘的 PCB 铜分组从 589 减至 583，既有连通端点对无回退。 [原生回归摘要](evidence/summary.json) · [完整 DRC 对照](P01_DRC_BEFORE_AFTER.csv) · [逐网开路](evidence/opens_by_net.csv)

三路样片重算的三个 C–B、C–E 均为 1.1102 mm，D1/D2/D3 焊盘对均为 1.5000 mm。独立临时目录重建并重填后，交付 PCB 逐字节一致。SHA-256 为 `9b1a1c5bdc5c3086b3a30ccaf5617d1122255836876e50fa47528c12d35d34a5`。

六项原有开路完成实铜连接。R303.2–V1.1（ANODE_1），R60.1 接入 R306.1–C47.1（HV_BUS），R63.2–R64.1（HV_OVP_S），R81.2–R82.1（HV_FB_1），R84.2–R85.1（HV_FB），D3.2–Q32.2（SW_HV）。R302–R303、R60–R61 和 R62–R63 原有局部铜随元件组一同移动，其余既有分压及保护端点保持连通。R61.2–R62.1 的 OVP 中间级、开关至吸收网络和其他冻结开路仍待闭合。 [实际端点核查](evidence/terminal_pairs.csv)

## MMBTA42 原厂封装

30 颗全部使用晶导 C4749118 名义公制矩形 0.90 × 0.80 mm。B.Cu 安装角度 0°，底层镜像后的 B/E/C 焊盘在相对中心的 `(-1,+0.95)`、`(-1,-0.95)`、`(+1,0)` mm，三个编号焊盘分别提供 B.Cu、B.Mask、B.Paste 的同几何轮廓。有效阻焊扩展和钢网补偿均为 0。Q1 保持 (60.5, 115.0) mm，1/2/3 依次连接 BASE_00/GND/K1_0。其四个旧 B.Cu 触点已重布，外侧引出。Q2–Q30 对应的六个既有基极过孔及相邻走线回撤 0.125 mm，消除换封装后约 1.9699 mm 的六处外部候选违规。 [晶导原厂数据表](https://datasheet.lcsc.com/lcsc/2208091800_Shandong-Jingdao-Microelectronics-MMBTA42_C4749118.pdf) · [90 个实板焊盘](MMBTA42_PAD_INTEGRATION.csv)

| Q1 铜距 | 冻结板 | R14.4 |
| --- | ---: | ---: |
| C–B | 0.655249 mm | 1.110180 mm |
| C–E | 0.655249 mm | 1.110180 mm |
| B–E | 1.300000 mm | 1.100000 mm |

Q2–Q30 的 87 个焊盘在两版均是独立铜连通分组，网名与编号已逐一核对。Q1 已证明其单元能够完成正确连接。其余 29 路的 B/E/C 布线仍需完成。约 5 mm 的相邻单元摆位、邻近基极过孔与相反电位阴极铜会限制外侧出线。后续应先完成一组相邻单元的全铜布线并复核外部边界，再扩展到其他组。 [逐项未决](P01_UNRESOLVED_ITEMS.csv)

## 高压与低压边界

R302/R303 整组旋转并移至靠近 V1 的显示线束区。R60/R61 移到远离 R52 与 U14 的区域，R62/R63 移出 OLED 保护旁边，R64 旋转并让开残压分压链首。原生几何审计确认板边、安装孔、V1–V3 手焊线束焊盘和 UART、按钮、STOP 连接器坐标沿用冻结工程。R302/R303 所在 V1 两排手焊焊盘之间需在后续外壳阶段核对外接管座、线束与 1 W 电阻的实际高度和受热空间。 [边界坐标、网络和铜距](P01_HV_LV_BOUNDARY_AUDIT.csv)

| 实际铜对 | 冻结板 mm | R14.4 mm |
| --- | ---: | ---: |
| R302.1 HV_BUS–U3.18 BTN1_GPIO | 1.0928 | 25.2592 |
| R302.1 HV_BUS–U3.17 WDI | 0.9750 | 24.1958 |
| R302.2 ALIM_1–U4.3 RST_REQ_N | 1.1750 | 22.1769 |
| R303.1 ALIM_1–J2.4 RST_REQ_N | 1.8831 | 14.5423 |
| R60.1 HV_BUS–R52.2 GND | 0.8500 | 14.7748 |
| R61.2 HV_OVP_S_2–U14.4 GND | 1.1000 | 24.5656 |
| R62.1 HV_OVP_S_2–D1.1 OLED_SDA | 1.5293 | 15.5055 |

J2 最近母线铜由 1.8750 mm 增至 14.4687 mm，最近显示铜由 1.8750 mm 增至 8.3500 mm。J5 最近显示铜约 2.6320 mm，对象为 V1.1。J6 最近母线铜由 21.6492 mm 增至 45.6685 mm。证据是同层铜投影。J2/J5/J6 用户线束和公共地故障能量转移仍需整机边界审查。 [接口逐层筛查](P01_HV_LV_BOUNDARY_AUDIT.csv)

## 开关节点与规则验证

D3 旋转后，D3.2 到 U17.7 的铜距从 1.5328 mm 增至 3.5127 mm。D3.2 通过 F.Cu 0.50 mm 铜接入 Q32.2 与既有 L3.2 开关支路。移开 R86 与 C48 后，原本对 R65/R66、R82、C36 等的 14 项开关外部违规全部消除。保留 D3 的 1.5000 mm、C48 的 1.8000 mm 和 Q32 的两项 2.0000 mm。开关支路至 R86 与 SNUB 到 C48 仍开路，实际最大瞬态与重复峰值为 `UNKNOWN`。 [端点检查](evidence/terminal_pairs.csv) · [逐项未决](P01_UNRESOLVED_ITEMS.csv)

保留 2.00 mm 高压铜筛查、3.20 mm 开关筛查和原安装件规则。新增单独命名的接口及 MCU 2.00 mm 规则，优先级低于开关规则。已从交付路径打开 PCB 编辑器并运行 Clearance Resolution。D3.1/D3.2 的解析值为 3.20 mm，Q28.2/Q28.3 为 2.00 mm。原生 CLI 在冻结铜对上进一步确认 13 项接口匹配、188 项其余高压铜匹配、18 项开关匹配。 [KiCad 规则](eda/NXT-M3-R14.4.kicad_dru) · [编辑器间距解析](evidence/editor_clearance_resolution.md) · [原生规则解析探针](evidence/native_rule_resolution.json)

## 决策与后续门槛

```text
P01_SOT23_DECISION = CONDITIONAL
P01_HV_LV_BOUNDARY = HOLD
P01_SWITCH_NODE = HOLD
P01_OVERALL = HOLD
EVT_RELEASE = HOLD
MANUFACTURING_RELEASE = HOLD
```

SOT-23 的 CONDITIONAL 限于 30 颗名义封装映射和 Q1 工程布线。打板前仍需闭合未布网、处理残余外部间距、确认材料 CTI 与装配后最坏空气和爬电路径、核对放电及接口故障能量、取得适用的开关峰值证据或通过 ECR 更换未达资格的封装。本轮 170 V 实物上电状态为 HOLD。 [分项判定和资格证据](P01_CLEARANCE_DECISION.md) · [复现入口](REPRODUCE.md)
