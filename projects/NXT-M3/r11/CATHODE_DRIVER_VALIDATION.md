# 74HC595 与 MMBTA42 驱动验证

KiCad 原生网表 827 个引脚网络条目与 R10 一致。逐路复核 30 个 595 输出、3 kΩ 限流、10 kΩ 下拉、晶导管 1=B/2=E/3=C 与逻辑管座引脚。U20–U23 的 /OE 已走通，SER1–SER3 及复位清零线仍开放。上电 MCU_EN、故障清锁、/OE 硬件上拉和 Q31 许可下拉属于原理图逻辑。/SRCLR 仅清移位寄存器，固件仍需在消隐期清零并锁存。GPIO0、45、46、3 出厂与启动组合，UART 输入限幅和外部 EN 开漏仍需低压实测。 [原生审计](evidence/r5/pins.json) · [分网清单](evidence/r5/net_completion.csv)

TI 74HC595 的 VCC 允许 3.3 V，TI 对输入阈值的 3.3 V 插值为 VIH 约 2.358 V、VIL 约 0.942 V。电平、负载与边沿需要同时成立。TI 在 4.5/6 V 的带载 VOH 和 IOH 表不足以给出 3.3 V、每片多路同时驱动的保证。用 3.3 mA 和强迫 β=10 作工程目标，若 VBE=1.0 V，3.03 kΩ/9.9 kΩ 角落所需 VOH 约 **2.306 V**。当 VOH=2.4 V 时最小基流 0.361 mA，目标为 0.330 mA。未取得 3.3 V 最小带载保证。 [TI 595 手册](https://www.ti.com/lit/ds/symlink/sn74hc595.pdf) · [TI 输入阈值应用简报](https://www.ti.com/document-viewer/lit/html/sbaa808)

常温代理在约 3.168 V VOH 时，IB/IC/VCE 为 0.723 mA/3.297 mA/0.069 V。85 °C 弱驱动代理在约 2.270 V VOH、低 β 参数时得 0.470 mA/3.295 mA/0.098 V。该代理的 VBE 假设低于 1.0 V 边界，结果与保守电阻算式的差异必须保留。晶导数据表的饱和指标适用于 IC=20 mA、IB=2 mA，25 °C 的 ICBO 上限适用于发射极开路测试。代理截止电流约 0.13–0.15 nA，没有实物热态漏电代表性。 [常温测量](evidence/r2/cathode_drive/measurement.json) · [85 °C 测量](evidence/r2/cathode_hot_weak/measurement.json) · [晶导器件手册](https://datasheet.lcsc.com/lcsc/2208091800_Shandong-Jingdao-Microelectronics-MMBTA42_C4749118.pdf)

三态与热漏电合计 15 µA 的假定给带下拉基极 0.1515 V，取消该下拉后代理为 0.458–0.578 V。30 路以 36.36 mA 同时加载 44 µF 理想电容、50 µs 无稳压器支援时，跌落 41.3 mV。夹位二极管在输入高、595 供电关闭代理下形成 2.36–2.44 mA 回灌，具体回流随真实供电路径与器件变化。ESP32 发送、OLED 启动、3.3 V 下垂和半导通热资格均开放。
