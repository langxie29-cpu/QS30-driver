# G1 原理图/选型复核检查表（REV.A9）

> 对照 `docs9/ARCHITECTURE.md` 与 `netlist9/QS30-9_REV.A_netlist.csv` 逐项签核。
> 本表不替代 KiCad/立创EDA 原生 ERC（H9-06），只用于 G1 人工复核。

## A. 电源与门控
- [ ] EXT12/5V_SYS/3V3/DRV_VDD 电压域与器件耐压匹配（含 12 V−5% 工况）
- [ ] DRV_PG = 11.2 V（迟滞 ≥0.3 V），关断阈值 >10.8 V（HV5622 VDD 下限）
- [ ] EXT12_PG 在 12 V−5% 输入时仍为高（当前 10.5 V 触发，需实测确认）
- [ ] DRV_VDD_EN / HV_EN 逻辑：`(EXT12_PG·P3V3_PG)·HV_EN_REQ` 与 `(DRV_PG·FAULT_OK)·SAFETY_OK·HV_EN_REQ`
- [ ] Q2/Q4 P-FET 默认关断（栅极上拉）、Q3/Q5 驱动电阻/下拉正确
- [ ] 上电/掉电顺序：3V3 先于 DRV_VDD、HV 最后；失电无显示乱码/误亮

## B. 高压与 OVP
- [ ] 升压功率级参数（220 µH/78 kHz/20 µF/IRF740/UF4007）与 POWER9.md 一致
- [ ] OVP 分压 1500k/19.1k、TL431 2.5 V、LM393 EXT12 供电（共模 2.5 V 合法）
- [ ] OVP 锁存 Q21-Q25 偏置（R44/R45/R46/R47/R48/R52/R53）与图纸一致
- [ ] OVP 复位仅经 Q25；固件脉冲 ≥0.2 ms 且 HV<198.8 V 时才有效（I9-03 待实测）
- [ ] HV 采样分压 1500k/14.3k → 172 V 时 ~1.63 V，OVP 上限 ≤3.3 V
- [ ] 泄放：主板 200 kΩ + 每模块 200 kΩ；172→50 V 计算 0.76 s

## C. 驱动与接口
- [ ] 3×HV5622PG-G（PQFP-44）引脚表与 DS20005854A 一致（POL=27、CLK=28、LE=31、DIN=32、DOUT=23、BL=33、VDD=30、VSS=29）
- [ ] 每片 30 路使用、HVOUT31/32 留空；90 路映射与 channel_map9.csv 一致
- [ ] 96 bit 帧：设备顺序 L→C→R，L DOUT 回主板进 C（R62/R63 0 Ω 回线）
- [ ] 模块 LV 16P 接口左右一致（除 DIN/DOUT）；HV 2P 独立且 ≥300 V 额定（H9-07）
- [ ] SAFETY_LOOP 串联路径与拔线行为（H9-10 待实测）
- [ ] 每模块 1×CD40109B：ENABLE=3V3，输出 12 V 域下拉 100k，BL=0 时全关

## D. 器件与 BOM
- [ ] BOM-B 与网表位号一一对应（脚本 D13 类检查）
- [ ] 关键降额：Q20 400 V、D20 1000 V、C11/C12 250 V、L20 Isat ≥5 A、R_AN 1.48 W/2 W
- [ ] 价格未知项全部标记 UNKNOWN（BOM9_INQUIRY.csv）

## E. 结论
- 全部勾选 → G1 通过（仍需 EDA 原生 ERC 后放行打样）
- 任一未勾选 → 保持 G1，禁止打样
