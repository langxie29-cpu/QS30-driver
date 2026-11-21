# HV STOP 与硬件联锁

J6 为独立两芯常闭干接点。常态将 STOP_LOOP 拉至地，R509 220 Ω、R510 3.3 kΩ 使 Q35 栅极约 0.206 V。打开或任一导线完全断开，栅极向 3.3 V 上拉，Q35 下拉 FAULT_N。C64 1 nF 的开路上升时间常数约 3.3 µs，D15 为连接器侧 ESD 候选。按 0.94 mA 名义触点负载选择低电流适用的开关。故障路径在 MCU、OLED 与网络以外。 [2N7002BK](https://www.nexperia.com/product/2N7002BK) · [TVS](https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf)

| 原生审查 | 结果 |
|---|---|
| Analog_protection | U13 开集电极 OVP/OCP 与 STOP、U25 WDO 共用 FAULT_N。标称 OVP 分压约 188.84 V。OCP 比较 121.24 mV，对 50 mΩ 约 2.42 A，观察的是开关路径。比较器失供、分压故障和 FAULT_N 短高可绕过触发 |
| Hardware_inhibit | U9 将 FAULT_N 与 MCU_EN 送 U8 异步清除。U8 重新许可需 J4 新上升沿并采样 RESIDUAL_OK。MCU 看门狗 U25 的 SET0/SET1 高，CWD 悬空，器件名义上界约 1 s。可持续喂狗的异常和 Wi-Fi 失联本身不触发 |
| HV_cutoff | U11 EN/UVLO 由 ARMED 控制并经 R26 下拉。U11 是原有低压输入断供器，内部复位、反向阻断和直接关断时延需根据器件及实板审查。R40 原生仍 DNP |
| Shift_registers | U15 和 U19/U10 由 ARMED、偏置有效、HV_READY、DIGITS_REQ 逐级许可 Q31。R24 拉高四颗 595 的 /OE，输出高阻。SRCLR_N 只清移位寄存器，复位后仍需空白帧与受控时序 |
| HV_bleeders | 双四电阻被动泄放，残压比较器由另一分压链采样。RESIDUAL_OK 名义阈值约 54.92 V，只供重新许可判断。可触及前需独立验证残压 |

四个代理工况已保存完整波形。额外的 1 ms 量级启动滤波属于仿真夹具，避免理想母线在 ARM 脉冲内立即改变 D 输入。它没有进入原理图。以 t=0.600 s 开环计算，双泄放约 1.072 s 到 60 V，单路约 2.144 s。模型中重新接合环路不置位。单泄放在相同 ARM 时间仍受残压阻止。U11 卡通时仍有 5 V 输入，跨 Boost 电感与整流路径继续供电。短接环路线时停止事件被掩盖。代理还检查了其他 FAULT_N 源断言和逻辑电源复位。实际电气延迟、反向供能和硬件故障注入待资格。 [波形、测量与网表](evidence/simulation/) · [TPS25947](https://www.ti.com/lit/ds/symlink/tps25947.pdf) · [TPS3430](https://www.ti.com/lit/ds/symlink/tps3430.pdf) · [SN74LVC1G74](https://www.ti.com/product/SN74LVC1G74) · [SN74HC595](https://www.ti.com/product/SN74HC595)

低压控制仍由 3V3 路供电，MCU 可采集 FAULT_N 与 ARMED。日志保留仍依赖后续固件与失电策略。现有路径是单通道功能停止。线束短接、Q35 开路、U8/U9 失效和 U11 短通无法由该方案覆盖。需要时以独立串联断供、监督式回路及外壳联锁作为 ECR 候选。
