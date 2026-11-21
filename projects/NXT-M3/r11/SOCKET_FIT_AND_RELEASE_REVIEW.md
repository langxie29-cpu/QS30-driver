# R11 管座手焊接口和投板审核

最新 Type-C 布线、孔径和仿真结果见 [堵塞续轮报告](BLOCKER_CLOSURE_REPORT.md)。以下为管座提交时的检查快照。

**结论：整板投板 NO-GO。Gate 0 保持 REWORK，制造保持 HOLD。**

基线为先前的 Type-C 提交 `db00df02893e169ddcf2583da06f930f07f9dc97`。原工作区存在 KiCad 锁，因此本轮在隔离分支 `codex/r11-socket-fit` 编辑。当前会话附件未找到可读取的淘宝原图，孔位、孔径与交接焊盘坐标沿用本地 R10 的 GZC13-F 参考。上线前可用 1:1 孔位图或实件复核 28 mm 孔距、两孔同轴、座体/螺钉间隙及线束路径。

## 已落实在实际 PCB

- 三组安装孔，每组两个 **Ø3.5 mm NPTH**，组内中心距 **28 mm**。相对板左上角的 X 为 **13、41、51、79、89、117 mm**，Y 均为 **52 mm**。原四个 Ø3.2 mm 装配孔保留。原生 Excellon 成功区分 PTH/NPTH，审计读取并匹配六个新增孔位。钻孔导出存于本机临时审核位置；交付包含核验报告和散列。
- 每组预留 **11 个带网名的 1.8 × 2.6 mm 正面无孔焊盘**，标为 A 和 0–9。使用原逻辑针号映射核对全部 33 路。支架与针脚采用分别固定、飞线手焊的做法，留在板上的孔只作支柱安装。
- 按 R10 参考移位 SW1、TP4、C47。孔周在双层设置 Ø8 mm 铜线、过孔、铺铜禁区，复核未检出焊盘或铜线侵入。恢复 BOOT_N 和 TP4 本地铜线，推进阳极、高压母线及 Type-C 区布线。ANODE_3 已闭合，Type-C 的 USBC_CC2 通过 PCB 导通检查。 [孔位和手焊审核](evidence/socket_fit/final/socket_fit_audit.json) · [原生钻孔报告](evidence/socket_fit/final/drill_report.txt)

## 哪些项目仍阻塞生产

| 项目 | 实际结果 | 放行所需证据 |
| --- | --- | --- |
| 原理图与 PCB | ERC 0 错误、0 警告。PCB 与原理图一致性 0 项。仅移除手焊接口中不使用的 2/8 虚拟端点，已连接引脚网络无变化。 | 实物管座逐针通断、键位、焊线装配与机械公差。 |
| 实际连接 | DRC 仍有 **349 个未连接项**。新增的 33 个手焊位置中 **1 个已通、32 个未通**。余下为 30 路阴极及 ANODE_1、ANODE_2。 | 闭合对应连接、重新做原生 DRC 和实物安装核对。 |
| 阴极封装净距 | 板上 30 个候选 Q 的 SOT-23 本体焊盘间距触发工程规则。Q1 基极到集电极铜边实测 DRC 为 **0.655 mm**，当前筛选为 **2.00 mm**。 | 结合真实重复峰值、CTI、污染等级和绝缘类别完成绝缘协调。调整封装、工艺或结构，重新证明可制造和安全。 |
| 高压隔离与工艺 | DRC **277 条规则项**，含 **263 条净距错误、12 条钻孔错误、2 条丝印警告**。已有功能器件的裸铜/安装段仍开放。 | 通过 PCB 工艺、绝缘、插拔可触及和完整 DRC。规则仍为原工程筛选。 |
| Type-C 和电源 | J1 到 F1、CC1、U26 去耦、HV 功率回路仍有开项。本轮 J1→F1 的边沿改线候选发生冲突并撤回。源端 4.75 V 满载上一轮代理只到 155.666 V，真实 LM5155 模型仍超时。 | 完成 Type-C、电源与回流，验证 5 V/3 A 安装样件、低线满载、真断路、反灌、残压联锁和实际开关应力。 |
| 半导通 / 驱动 | 既有 195 V 半导通代理约 0.480 W 可持续。国产 MMBTA42 的热态 SOA、独立支路诊断、3.3 V 595 带载仍未关闭。 | 完成真实器件和单故障验证，通过热应力和安全评审。 |

[最终 ERC](evidence/socket_fit/final/ERC_REPORT.txt) · [最终 DRC](evidence/socket_fit/final/DRC_REPORT.txt) · [布局布线记录](evidence/socket_fit/routing_summary.json) · [前轮电源与保护](TYPEC_ECO_REPORT.md) · [KiCad DRC 文档](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) · [IEC 绝缘协调](https://webstore.iec.ch/en/publication/107319)

没有提交采购或交付生产文件。六孔有原生钻孔证据，可用于手焊装配设计复核。整板包括低压输入与高压部分，目前均未达到放行门槛。

## 检查复现

在 `projects/NXT-M3/r11` 中运行：

```powershell
$k='C:/Program Files/KiCad/10.0/bin'
python native_checks.py evidence/socket_fit/final
& "$k/kicad-cli.exe" pcb export drill --format excellon --excellon-separate-th -o <审核目录> eda/NXT-M3-R11.kicad_pcb
& "$k/python.exe" socket_fit_verify.py <审核目录>/NXT-M3-R11-NPTH.drl
```

`socket_fit.py`、`socket_symbol.py`、`socket_route_repair.py` 与 `socket_prune_dangling.py` 用于从基线重演本轮局部操作。最终保存的 PCB 是交付依据。
