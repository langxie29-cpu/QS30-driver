# R10 电源、阴极与保护审查

**GATE_0 = REWORK · ENGINEERING_RELEASE = HOLD**

电气依据为 [R10 原理图](eda/NXT-M3-R10.kicad_sch)、[导出的连接表](evidence/native_netlist.xml)、[R9 电源筛选](../r9/POWER_COMPONENT_REVIEW.md) 和 [R8 G0D](../r8/G0D_RESIDUAL_ENERGY_REVIEW.md)。数值分属数据手册、计算或低阶仿真。完整闭环与实际保护响应仍开放。

## 负载与低压电源

| 项目 | 工作值 | 保守峰值 / 依据 |
| --- | ---: | --- |
| U3 ESP32-S3-WROOM-1-N8 | 150 mA 活跃规划 | 500 mA 电源预留，待 Wi-Fi 发包瞬态资格 |
| 0.91 英寸 OLED | 40 mA 预留 | 40 mA 暂定。实物与涌流 TBD |
| U20–U23 与基极 | 3 路正常导通，按 ≤3.64 mA | 30 路全高 36.36 mA；单片 8 路 ≤9.70 mA |
| 硬件逻辑及控制余量 | 总计舍入到 200 mA | 23 mA 预留，总计约 600 mA |
| 三管母线负载 | 2.55 mA/管，1.3005 W | 3.3 mA/管，1.683 W |
| 四级电阻串联泄放 ×2 | 116.53 mW @170 V | 153.33 mW @195 V |
| FB、OVP 与残压三个分压串 | 约 47.0 mW @170 V | 约 61.9 mW @195 V，未计分压作为安全泄放 |
| HV 侧总功率 @170 V | 1.46 W | 1.85 W |
| 5 V 输入功率 | (3.3×0.20)/0.87 + 1.46/0.70 + 0.05 ≈ 2.90 W | (3.3×0.60)/0.80 + 1.85/0.65 + 0.12 ≈ 5.44 W |
| 5 V 和 4.4 V 输入电流 | 0.58 A / 0.66 A | 1.09 A / 1.24 A；三块同时约 3.71 A @4.4 V |

SJ 1123—76 给出 170 V／20 kΩ 条件下 1.5–3 mA，中心值 2.25 mA。表内 2.55/3.3 mA 延续 R9 规划和压力边界。U2 是 1 A 的 TPS62162，旁路 C4–C10 包括入口储能、双 22 µF 和模组本地 10 µF。确认 MLCC 偏压后的有效电容、降压器瞬态及线束端压降。例，额外 300 mA 持续 50 µs，若全靠储能且预算压降 0.15 V，有效 C 需 100 µF。这个上界用于安排瞬态检查，实际由降压环路供电。输入保护包括 F1、D4 和 U1，U1 的 1.65 kΩ 档为 2.03 A 典型，数据手册表列 1.80–2.20 A。含 C3 的异常计时约 8.4 ms 典型，USB 外部电源和反向极性输入须按实际线束验证。高阻 UVLO/OVLO 分压要计入引脚漏电，4.4 V 低线启动仍开放。

参考 [SJ 1123—76](https://www.tube-tester.com/sites/nixie/dat_arch/QS30-1.pdf)、[Espressif 电源硬件指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)、[TPS62162](https://www.ti.com/lit/ds/symlink/tps62162.pdf)、[TPS25947](https://www.ti.com/lit/ds/symlink/tps25947.pdf)。

## 74HC595、阴极和默认状态

- TI SN74HC595PWR 以 3.3 V 共轨工作，推荐 VCC 范围 2–6 V。TI 应用简报给出 3.3 V 处插值 VIH≈2.358 V 和 VIL≈0.942 V。逻辑输入负载很轻，长线/复位边沿和噪声仍需测。数据手册在 4.5 V/6 V 的带载规格不足以直接保证 3.3 V 下 IOH、VOH 和多路同时驱动。R10 的 3.0 kΩ/10 kΩ、±1% 筛选中，若 VOH≥2.4 V 且 VBE≤1.0 V，最小基流为 (2.4−1.0)/3030−1.0/9900 = 0.361 mA，可覆盖 3.3 mA/10 = 0.330 mA 的强迫 β 工程目标。VOH=2.4 V 是待证条件。3.6 V/2.97 kΩ 给出每路 1.212 mA 的引脚最坏电流上界。30 路全高是故障筛选而非显示指令。
- 晶导 MMBTA42 / C4749118，SOT‑23，1=基极、2=发射极、3=集电极。VCEO 300 V，VCBO 300 V，VEBO 5 V。厂商给出 25 ℃ 下 ICBO≤0.25 µA（VCB=200 V、发射极开路）；VCE(sat)≤0.2 V 是 20 mA/2 mA 条件。对实际 1.5–3.3 mA、高温、重复关断和长期半导通仍缺数据。若叠加估算的 10 µA 热反馈和 5 µA 高阻输出漏电，10.1 kΩ 将基极推到 0.152 V，仅为静态筛选。开关耦合和主电源衰减可能使此近似失效。
- U4 拉低 MCU_EN 时，HC 移位清零、OLED 硬件关闭以及 U8 授权清除。U25 的 WDO、独立电压和电流比较器共拉 FAULT_N，U9 据此清 U8。复位释放后仍需内部 J4 上升沿. U8 在边沿采样 RESIDUAL_OK。U15 要求 ARMED 与 BIAS_OK，U19 再要求 LM5155 的 HV_READY。U10 由 DIGITS_REQ 与 DRIVE_OK 控制，Q31 未获许可时，R24 使 /OE 为高。每个阴极基极有各自 10 kΩ 下拉。/SRCLR 仅清移位寄存器，固件必须在消隐期间移入全零并锁存。输出位 30/31 NC，R9 帧协议仍应写零。
- TPS3430 的初始候选为 WDI 下降沿每约 1.1 s，名义窗口 0.8–1.6 s。软件端时序未实现，下一轮需用有效租约及整个输出链活动产生心跳。MCU 尚未完成事务、通信超时等状态由固件撤销 DIGITS_REQ。上电斜坡、断电顺序、Ioff、输入毛刺、瞬时故障脉宽、部分器件断供、假许可和探测共因故障均待证明。
- OLED 走 TPS22918 断电与 QOD，TCA9517A 的 A 域是切换后的 OLED 电源，B 域是常开的 MCU 3.3 V。MCU_EN 在复位时硬件切断 OLED，单纯 HV 或看门狗故障时若 MCU_EN 仍高，OLED 可用于低压状态显示，R9 协议负责撤销过期语义。J3 为可拆连接器候选，两个外侧 4.7 kΩ 默认 DNP 避免与实物上拉叠加。实物脚序、复位脚、物料版本、VIL 和高低边逻辑、电流和黄光接受均开放。J2 是 3.3 V UART0 ROM 恢复口，RX 有 Ioff 缓冲，无适配器电源引脚，外部 EN 控制用开漏；USB D+/D− 保留为未接引脚。

参考 [TI SN74HC595](https://www.ti.com/lit/ds/symlink/sn74hc595.pdf)、[TI 3.3 V 逻辑插值](https://www.ti.com/document-viewer/lit/html/SBAA808/GUID-F7CBECE2-5469-41E4-AC23-D67A055422CD)、[晶导数据表](https://datasheet.lcsc.com/lcsc/2208091800_Shandong-Jingdao-Microelectronics-MMBTA42_C4749118.pdf)、[晶导采购条目](https://www.lcsc.com/product-detail/C4749118.html)、[TPS3430](https://www.ti.com/lit/ds/symlink/tps3430.pdf)、[TCA9517A](https://www.ti.com/product/TCA9517A)。

## 约 170 V 转换器和硬件边界

| 项目 | R10 原理图计算 / 判断 |
| --- | --- |
| 拓扑 | LM5155DSSR、UCC27511、STD13N60M2、ES1G、22 µH 非隔离 DCM。TPS61040 用 845 kΩ/100 kΩ，1.233 V FB 名义约 11.65 V。其被动预充只达到输入附近，BIAS_OK 名义 9.36 V 后才能放行主 PWM。 |
| 主环路 | R79=220 kΩ，数据手册曲线约 100 kHz；R81–R84=4×422 kΩ，R85=10 kΩ，1 V 反馈名义 169.8 V。补偿 R80/C43/C44 为初值，SS 值、变输入、负载跃变、无负载以及从预充跨入 DCM 均开放。 |
| 低线功率筛选 | 4.4 V、100 kHz、65% 效率、1.85 W 时，L=17.6–26.4 µH 得 Ipk≈1.80–1.47 A，ton/T≈0.72–0.88，toff/T≈0.02。在后一角落占空占用约 0.90。未计磁芯损耗、恢复电流和启动暂态，需验证控制器最大占空与限流裕量。 |
| 主开关与整流 | MOSFET 筛选 VDS≤320 V，器件标称 600 V。D3 标称 400 V、1 A 平均。最大估算 IL 峰值 1.80 A 只是稳态窗口；MOS RMS 约 0.88 A，对 0.38 Ω 估计 0.30 W，热态若 RDS 翻倍约 0.59 W。22 µH 候选最大 DCR 约 39.5 mΩ，低感量角落电感铜耗约 32 mW（无磁芯损耗）。D3 的 1 A 平均规格不能代替脉冲、反向恢复和热态核对。SNUB 候选 100 pF 在每周期全摆幅 170 V、100 kHz 时，CV²f 量级约 0.29 W。 |
| 电容 | C47 3.3 µF/450 V ±10% 薄膜候选。170 V 名义储能 47.69 mJ，3.63 µF 时 52.45 mJ；195 V 和 3.63 µF 时 69.02 mJ。以 13 mA、250 µs、2.97 µF 估算压降 1.09 V，1 ms 为 4.38 V。纯电荷估算不含 ESR、ESL 和闭环。三角整流波估计 0.13–0.15 A RMS，须查频谱、厂商降额、寿命和安装温升。 |
| 阳极限流 | 每管 2×10 kΩ。正常 2.55 mA 时每颗约 65 mW、25.5 V。3.3 mA 时每颗约 109 mW、33 V。195 V、两颗均在 −1%、灯管通路与 C–E 同时短路时，整支路 1.92 W、单颗约 0.96 W、97.5 V，已接近候选 1 W 标称。最坏热环境、单颗短路、脉冲与长期退额未通过。 |
| 半导通 | 保守用零管压降和 19.8 kΩ。195 V 下峰值为 V²/(4R)=0.480 W，发生在 VCE≈97.5 V、IC≈4.92 mA。按晶导 350 mW@25 ℃、150 ℃结温线性筛选，85 ℃时约 182 mW。总输入或无故障阈值触发时，危险功率可持续。需要独立支路诊断或重开储能隔离设计。 |
| 过压与过流 | 独立 U13 与 REF3312，OVP 名义 188.84 V（1.25 V、4×499 kΩ/13.3 kΩ）。还未进行容差、峰值、失供与响应收口。LM5155 100 mV 逐周期限流对应 50 mΩ 名义 2 A，数据手册 ±7%；U13 的独立比较名义 2.42 A；U11 低压支路保护是另外一级。主电流比较和总电流限幅不能判别单管低流半导通。 |
| 实际断能与反馈 | R40 为 DNP 的常开工程电源连接，后端元件也标 DNP。设计中的 U11 切断 5 V 功率通路，并有反灌阻断候选，U15 禁止 PWM。已切断的开关支路仍有 C28/C37 储能与电感电流。非隔离升压经 L3/D3 的输入直通须计入，若 U11 卡通、辅助域供电或实际器件关断漏电，进一步量化残余路径。 |
| 双路泄放和残压 | R400–R407 每路 496 kΩ ±1%，无源常连。四颗均分 195 V 时各约 48.75 V、19 mW。U14 的残压名义阈值 54.92 V（4×453 kΩ/42.2 kΩ）；用于再 ARM 的门槛和防触碰验证仍 OPEN。采样断线会造成假低读，且共用参考及 3.3 V。双链某一路开路检测和独立安全访问联锁均开放。 |

参考 [LM5155](https://www.ti.com/lit/ds/symlink/lm5155.pdf)、[UCC27511](https://www.ti.com/lit/ds/symlink/ucc27511.pdf)、[TPS61040](https://www.ti.com/lit/ds/symlink/tps61040.pdf)、[TDK C47](https://www.tdk-electronics.tdk.com/en/3191480/products/product-catalog/film-capacitors/capacitors-for-dc-link/search-results-deltacap-capacitors?so=%7B%22orderingCode%22%3A%22B32774%2A%22%7D)、[STD13N60M2](https://www.st.com/resource/en/datasheet/std13n60m2.pdf)。

## 原生仿真证据及局限

`<KiCad bin>/python.exe run_residual_spice.py` 调用 KiCad 自带 ngspice‑46。输入 [residual_energy.cir](residual_energy.cir)，命令及原始结果见 [ngspice.log](evidence/ngspice.log)。195 V 初始、3.63 µF、理想瞬时断开时，双泄放至 60 V 为 **1.07168 s**；单泄放为 **2.14337 s**。等阻半导通代理峰值 **0.480106 W**，一次吸收 **29.7964 mJ**。此为固定 19.8 kΩ 轨迹，R9 已报告可变轨迹能量更高。另用 5.5 V 与通用二极管模拟关 PWM，3 秒时母线 **5.06406 V**，理想切断支路 **0 V**。此模拟用于区分拓扑路径；SOA、烧机后的实际残压和安全切断时间均不由这些观察确认。

TI 发布了 LM5155‑Q1 Rev. H 非加密 PSpice 库。工作环境的二进制下载无法访问，curl 报 DNS 错误 6，搜索接口也无法返回 ZIP。R10 没有闭环厂商模型运行结果，也没有通过 ngspice 验证该库兼容性。晶导热态 SOA/漏电、QS30‑1 电离/弧光、U11 反灌与动态切断当前无可用、已核对的全温模型。后续优先验证低线满负载启动、空载过压、单点故障和前后供电顺序。 [TI 模型入口](https://www.ti.com/product/LM5155#design-development)
