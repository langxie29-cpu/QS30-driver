# R11 续轮：5 V Type-C 输入与 R10 管座参考

**GATE_0 = REWORK · ENGINEERING HOLD · MANUFACTURING_RELEASE = HOLD**

## 原生工程

J1 改为 GCT USB4125-GF-A 供电专用 Type-C。A9/B9 为 VBUS，A12/B12/SH 为地，A5/B5 两路 CC 独立进入 U26 STUSB4500LQTR。CC1DB/CC2DB 连接各自 CC 端，支持设备无电时的 Rd。两路 CC 有 D5 ESD 候选。STUSB4500L 的有效 VBUS 和 3 A 声明输出各驱动一条默认夹低 U1 EN 的硬件通路，两个条件同时满足才准许 U1 接通。F1、TVS、U1/U11 保护、R40 DNP 及 UART 恢复保留。J1 仅承载 5 V，设备不发起 USB PD 升压。工程选定 3 A Type-C 电源声明作为启动条件，默认档或 1.5 A 档不启动。3 A 是供电能力声明，实际负载由设备决定。 [GCT J1](https://gct.co/connector/usb4125) · [STUSB4500L 数据手册](https://www.st.com/resource/en/datasheet/stusb4500l.pdf) · [TPS25947 数据手册](https://www.ti.com/lit/ds/symlink/tps25947.pdf)

- [输入与 3.3 V 子页](eda/Input_and_3V3.kicad_sch) · [PCB](eda/NXT-M3-R11.kicad_pcb) · [引脚核验](evidence/typec/final/typec_pin_audit.json)
- J1 与 12 个新增电气器件已落板，板上 2,340 段铜迹、197 个过孔。已有两路 CC 的部分铜迹及闭合的 FRONT_EN，J1→F1、J1 的两路 CC、U26 两路退耦和部分许可链仍未闭合。连接器选择在板边，实际外壳和 OLED 插拔区尚需用样品核验。若双层原区重摆仍难以接通，验证输入区域换位或分板。 [最终分网表](evidence/typec/final/net_completion.csv)
- KiCad 10.0.8 原生 ERC 0 错误、0 警告。825 个原 R11 引脚网络条目保持原样，所有已放焊盘的网络与新网表一致。DRC 280 条规则项（266 净距、12 钻孔、2 丝印）、313 个未连接项、3 个缺失管座封装，退出码 5。工程仍为布局布线草案。 [ERC](evidence/typec/final/ERC_REPORT.txt) · [DRC](evidence/typec/final/DRC_REPORT.txt)

## Type-C 电源仿真

采用 5 V 源、线缆回路/接口/保险丝电阻、两种方向的独立 CC、厂商 dV/dt 方程对应的 0.426 V/ms、两级保护开关、低压负载及 R11 功率级。低压降压器是输入功率边界，U26 带时序的 CC 和 U1/U11 为代理模型。USB 坡度、CC 防抖、UVLO/OVLO 与器件延时仍需样件核验。本轮 20 个工况中 19 个完成并核对 RAW，另一个厂商模型超时。波形保留仿真初始 0 V 的证据。有载开关仿真中的 R40 模拟装入，硬件原理图仍 DNP。 [可执行网表和日志](evidence/typec/runs) · [模型与运行器](sim/typec_run.py)

| 运行条件 | 结果 |
| --- | --- |
| 5 V，标称负载，CC1 / CC2 | 两方向均约 169.799 V，47.2 mVpp；44.60 ms 首次超过 161.5 V。接通后适配器峰值约 1.02 A。仿真绝对时间包含 15 ms ARM 延迟。 |
| 默认 USB / 1.5 A | 两种都无 3 A 许可，保护轨及 HV 均近零。 |
| 5 V，三管及 3.3 V 满载 | 169.880 V，0.833 Vpp，保护轨最低 4.773 V。 |
| 4.75 V，负载上沿 | 线缆回路 0.190 Ω 时，保护轨最低 4.364 V，母线 155.666 V。回路改为 0.050 Ω 时仍只到 163.309 V。标称负载下同 0.190 Ω 导线可到 169.844 V。 |
| 5.25 V，负载上沿 | 169.800 V，45.6 mVpp。 |
| 5.5 V 源端 OVLO | U1 分压理想滞回代理的典型上／下门槛为 5.455/4.955 V。5.5 V 在阈值范围内可有不同结果，典型角落回到 5.0 V 仍保持切断。 |
| 降档 / 拔线 | 48 ms 事件后，前端撤销许可。低压衰减到代理监督点约 0.30 ms 后 ARM 下降。65 ms 母线仍约 127.4 V。 |
| 55 ms 重新 ARM | 65 ms 时未恢复。延长至 95 ms，末段平均 169.798 V。55 ms 再授权后约 21.3 ms 超过 161.5 V。ARM 为外加边界，包含实际残压许可和故障锁存的重新授权仍待独立验证。 |
| R40 开路 | 5 V 低压保护轨工作，HV 近零。 |
| U1 断开反灌 / 假设短接 | 后级 5 V 经 10 Ω 注入时，1 GΩ 关断代理约 5 nA，假设低阻失效时为 0.485 A。无真实器件或线缆损伤定论。 |
| 接入 Type-C 后的 OVP/OCP | 空载短反馈触发 OVP，峰值 188.866 V。施加 150 mV CS 代理刺激，约 1.4 µs 触发 OCP。比较器、锁存、切断的实际延迟保持开放。 |
| TI LM5155-Q1 Rev. H | 接入新前端后尝试零偏置启动，仍在内部约 1.08 µs 数值停滞并超时。厂商闭环资格保持 UNKNOWN。 |

热插入源上升沿假设下出现 5.50 A 瞬态，接通后的运行峰值单独从 RAW 计算。需用被测 5 V 适配器及线束阻抗实测。拔线代理将源强制拉到 0 V，连接器侧电容可形成短时放电脉冲。其条件和器件关断反灌对照保留在单独网表及原始波形。 [Type-C 资格矩阵](TYPEC_POWER_QUALIFICATION.csv)

## R10 管座参考

从原 R10 本地 GZC13-F 预览纳入 33 个手焊交接坐标和六个支柱参考位，在原生 PCB 的 `Cmts.User` 层可见。参考的 28 mm 支柱距和 Ø3.5 mm 孔仅作为候选投影，手焊坐标来自 PCB 交接布局。实物座的焊脚分布、安装高度、方向和绝缘仍待测量。当前投影发现 MH5L 与 SW1/BOOT_N、MH7L 与 DRV_27、MH7R 与 C47 高压焊盘包络相交，需优先复核或移位。最终网表、PCB 没有创建管座焊孔或将预览作为制造资格。 [原参考坐标](socket_reference/handwire-pads.csv) · [支柱投影复核](evidence/typec/socket_projection.json)

## 复现

```powershell
python sim/typec_run.py
python sim/typec_reverse.py
python sim/typec_run.py --vendor-zip <TI原包路径>
& 'C:/Program Files/KiCad/10.0/bin/python.exe' sim/typec_measure.py
python native_checks.py evidence/typec/final
python typec_audit.py
& 'C:/Program Files/KiCad/10.0/bin/python.exe' audit_board.py evidence/typec/final
```

仿真可用 `--case` 多次选择具体工况。重跑写入对应工况；复核已执行的精确电路时使用运行目录里的 `circuit.cir` 副本。原始 RAW 保存在各工况目录，SHA-256 与 ngspice 命令、返回码、耗时和波形抽样均交付。Git 包含网表、日志、测量、抽样及散列，完整 RAW 保留在本机工作树。
