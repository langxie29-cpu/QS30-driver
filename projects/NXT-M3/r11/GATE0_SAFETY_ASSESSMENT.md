# Gate 0 电气安全评估

**GATE_0 = REWORK** · **ENGINEERING HOLD** · **MANUFACTURING_RELEASE = HOLD**

| 危险场景 | 实际证据 | 仍需关闭 |
| --- | --- | --- |
| PWM 停止与上游供能 | 5.5 V 输入且只停 PWM，电感/二极管代理在 7 s 仍给 5.114 V；强制 U11 打开时为 0.0313 V。R40 原生 DNP。 | TPS259474L 的反向保护、斜率和关断延时、失供、卡通、部分回灌都须独立验证。代理开关没有证明绝缘隔离。 |
| OVP 与板级保护 | 比较阈值测试 188.901 V。标称负载反馈短路 30 ms 击中 188.522 V 但未触发。空载同类故障代理在 21.893 ms 切断，母线峰值 188.876 V。 | TLV1702/基准/逻辑/输入开关的真实延迟、容差、不再启动、失电和多次故障热应力。 |
| OCP | 名义 121.242 mV 对应 2.425 A。对 150 mV 人为采样刺激，代理在 18.0014 ms 触发并撤销授权。 | 实际异常电流、比较器传播、U11 隔离与逐周期 100 mV 限流的相互作用开放。正常总电流下单路故障不保证触发。 |
| 双泄放、单路失效和残压 | 195 V、3.63 µF 与 500.96 kΩ 每路，双／单路至 60 V 为 1.07168/2.14337 s，至 54.92 V 为 1.15212/2.30424 s。 | 残压假低、断线诊断、失电行为、可触及能量与独立壳体联锁。60 V 为计算窗，正式可触及边界待定。 |
| 半导通与持续供能 | 零管压降、19.8 kΩ 阳极电阻和等阻故障时，97.50 V、4.924 mA、0.4801 W。一次电容放电吸收 29.80 mJ，上游维持 195 V 则 4 s 积分达 1.920 J 并继续累积。 | 晶导全温 SOA、二次击穿、实际瞬态热阻、相邻器件温升和独立支路诊断。损坏与过热风险保持 P0。 |
| 高压器件周边与整机触达 | 最终原生 DRC 保留高压封装及开关净距问题。交接处没有正式管座焊盘。 | 绝缘协调、板边/金属安装件、阻燃/防触碰和壳体互锁需要具体验证。 |

C47 名义 170 V 为 47.69 mJ，+10% 为 52.45 mJ。195 V 边界名义 62.74 mJ，+10% 为 69.02 mJ。TDK 实际候选 B32774M4335K000 为 3.3 µF／450 V、±10%，厂商数据为 70 °C、10 kHz 下 5.5 A RMS 与典型 ESR 13.4 mΩ，典型 ESL 17 nH，最大体积包络 11 × 19 × 31.5 mm，脚距 27.5 mm。450 V 档脉冲 dV/dt 上限 30 V/µs。功率模型使用 25 mΩ 且省略 ESL。约 100 kHz 开关频谱、实际温度、安装及寿命仍待复核。 [TDK B3277*M 数据手册](https://product.tdk.com/system/files/dam/doc/product/capacitor/film/mkp_mfp/data_sheet/20/20/ds/mkp_b32774m_778m.pdf)

Protection 与 discharge 结果来自实际 SPICE 台架文件，对应比较、锁存和切断使用边界代理。无危险实物故障注入或高压上电。 [关断](evidence/r2/cutoff/measurement.json) · [过压](evidence/r2/ovp_feedback_fault_noload/measurement.json) · [过流](evidence/r2/ocp_sense_fault_r4/measurement.json) · [残压与半导通](evidence/r2/residual/measurement.json) · [TI eFuse 器件手册](https://www.ti.com/lit/ds/symlink/tps25947.pdf)

