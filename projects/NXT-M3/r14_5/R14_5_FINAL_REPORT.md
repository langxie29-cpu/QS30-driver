# Σ / NXT-M3 · R14.5 工程交付

**30/30 路阴极通过实板铜连通审计。** 整板关闭 241 项未连接，仍有 84 项。外部高压净距违规从 24 项降至 5 项。J6 相关端点从 36/49 增至 39/49。保护网络与整板放行仍停在 G5、G6。

工程采用外置管座。PCB 删除六个管座专用 Ø3.5 mm 安装孔和对应禁布区，V1–V3 改成 B.Cu 无孔线束焊盘，共 33 个接线端点。MMBTA42 组内节距扩至 7.50 mm。保留 130 × 80 mm 板外形、MH1–MH4 和 J2–J6 原位置。R14.4 原工程在基线提交 f1d07975d1479ff30372078b562e66f7913cdb1c 保留。 [可编辑工程](eda/NXT-M3-R14.5.kicad_pro) · [保存的 PCB](eda/NXT-M3-R14.5.kicad_pcb) · [布线架构](ROUTING_ARCHITECTURE.md)

## 路由与连通 Gate

| Gate | 结果 | 实板证据 |
| --- | --- | --- |
| G1 | PASS | 原布局先闭合 U20.1–R101.1，Q2 达 6/6。原生 DRC 对象集合无新增，未连接 325 → 324。外置管座重布后 Q1、Q2 仍分别为 6/6。 |
| G2 | PASS | Q3–Q5 共 18 对端点全部铜连通。V1–V3 的背面阴极路线验证了重复单元的独立出线。 |
| G3 | PASS | Q1–Q10 共 60 对端点全部铜连通。基线已连通的控制端点分组保留。 |
| G4 | PASS | Q1–Q30 共 180 对端点全部铜连通。Q3–Q30 的 84 个隔离焊盘减至 0。 |
| G5 | BLOCKED | J6 为 39/49。另列的 OVP、反馈、开关与看门狗 23 对中，14 对连通。 |
| G6 | BLOCKED | 5 项既有外部高压净距、84 项未连接。常规及 all-track 模式均为 103 项净距，新增违规、意外短路、悬空走线或过孔均为 0。 |

G4 审计覆盖各级 595 输出、基极串联与下拉、发射极地及对应阴极焊盘。SER2 与 SER3 的级联输入以及部分 595 公共时钟、清除和锁存支路仍开路。因此，当前 PCB 的 30 路端点结果仅证明从各 595 输出到相应线束端点的实际铜连接，整机显示控制仍待完成。 [第一组审计](GROUP_1_ROUTING_AUDIT.csv) · [30 路审计](CATHODE_30_CHANNEL_AUDIT.csv) · [595 控制端点](evidence/shift-register-control.json) · [Gate 台账](ROUTING_GATE_RESULTS.json)

## 保护与电源

- OVP 新闭合 R64.1→U13.2 及 R64.2→U13.4。R61.2→R62.1 和 C35.1→U13.2 仍开路。R61.2 在 F.Cu 的 (128.5375, 92.0) mm，R62.1 在 B.Cu 的 (133.0, 56.0375) mm。双面换层、细网格和扩大窗口后，仍落在分离的可达铜区。测试的前层迁移位置还受到 V2 阳极及 DRV_18/21/23 铜约束。
- 反馈新增 R85.2→U17.7。R83.2→R84.1、R81.1→C47.1 仍开路。R83.2 与 R67.2 的 B.Cu 间距为 1.1728 mm。将 C45 从 (167, 68) mm 移到 (171.25, 65) mm 后清除了该区域的 HV/LV 违规，反馈与残压分压走廊仍需进一步分开。
- D3.2→R86.1 接通，新增支线长 8.75 mm，换层一次。D3.1→C47.1、R86.2→C48.1、C48.2→R79.2 仍开路。C48 两个同形焊盘中心距 2.95 mm，名义铜距 1.80 mm。新增铜在同层可靠接触一个焊盘时，至另一焊盘的距离至多接近 2.95 mm，达不到 3.20 mm 筛查。C48 需要带实际器件和焊盘的 ECR 候选。SW_HV/SNUB 强制间距保持 3.20 mm，实际重复峰值为 UNKNOWN。
- J6 新闭合 U14.1→U8.2、U15.3→J6.2、R25.2→J6.2。尚有硬件许可电源及地、HV_READY、DIGITS_REQ、消隐地和部分 U11 端点开路。U11 与 R40 保持 DNP。STOP 的全部 49 对端点逐项记录。
- 原生未连接项中，GND 从 117 项降至 16 项，3V3 从 21 项降至 6 项，HV_BUS 仍有 5 项。实际 GND 铜分组从 118 组降至 17 组，3V3 从 22 组降至 7 组。基线已连通焊盘分组均无回退。

[保护端点](PROTECTION_NET_CONNECTIVITY.csv) · [逐网未连接](UNCONNECTED_NETS.csv) · [电源铜分组](evidence/power-copper-components.json) · [84 个剩余端点和局部障碍](BLOCKED_ROUTES.csv)

## 净距与原生验证

19 项原有外部 HV/LV 违规全部清除。剩余 5 项均为反馈和残压分压链之间的 2.00 mm 外部筛查项。

| 铜对 | 最终实距 mm |
| --- | ---: |
| R81.1 / R66.1 | 1.5852 |
| R81.2 / R66.2 | 1.5852 |
| R82.2 / R67.1 | 1.1621 |
| R83.1 / R67.1 | 1.1728 |
| R83.2 / R67.2 | 1.1728 |

整板 103 项包含 60 项 MMBTA42、34 项低压 IC、4 项开关器件本征间距。阵列外部最小同层铜距为 2.016451 mm，位于 Q6 的 V1.9 焊盘与 B.Cu 侧 GND 过孔之间。沿用原规则，边界筛查结果需结合装配间距和工差评估。KiCad 10.0.8 重开、网表映射、ERC 0/0、原理图一致性 0。对象差异包含 2,466 段新增走线和 170 个新增过孔。 [原生报告](evidence/after) · [净距逐项比对](DRC_BEFORE_AFTER.csv) · [对象差异](evidence/object-and-net-diff.json)

## 放行决策

```text
CATHODE_ROUTING = PASS
PROTECTION_NET_CONNECTIVITY = PARTIAL
HV_EXTERNAL_CLEARANCE = PARTIAL
FULL_BOARD_ROUTING = PARTIAL
P01_LAYOUT = HOLD
EVT_RELEASE = HOLD
MANUFACTURING_RELEASE = HOLD
HV_POWER_ON = PROHIBITED
```

本地 Harness 预检、架构审查、铜连通审查和净距审查均有记录。无付费 Worker 调用。 [复现与远端核验](REPRODUCE.md)
