# 固件约束清单（从设计数据库派生）

由 `design/firmware_constraints.py` 自动生成；网络名/GPIO 从 `netlist/QS30-6_REV.A_netlist.csv` 与 `docs/channel_mapping.csv` 反查。

## 控制引脚（ESP32-S3 侧）

| 网络 | ESP32 引脚 |
|---|---|
| DISP_DIN → DRV_DIN | U10.19（IO11） |
| DISP_CLK → DRV_CLK | U10.20（IO12） |
| DISP_LAT → DRV_LAT | U10.22（IO14） |
| DISP_ALLOW → DRV_BL | U10.8（IO15） |
| HV_EN_REQ | U10.9（IO16） |
| OVP_RST | U10.11（IO18） |
| HV_SENSE_ADC | U10.39（IO1） |
| HVF_NODE | U10.7（IO7） |

## 帧与位序

- 帧长 **64 bit**（2×HV5622，器件 U21, U22）
- 已用通道 **60** 路；位序：MSB-first（bit63 先发），ch → bit = 63-ch（H04 待实测确认）

## 约束项

| 编号 | 约束 | 值 | 说明 |
|---|---|---|---|
| F01 | 帧长度 64 位 | 64 | 2×HV5622（32 位/片），60 路已用、4 路备用；不得按 96 位或 60 位发送 |
| F02 | 位序 | MSB-first，bit=63-ch | PROVISIONAL：必须由 B3 walking-one 实测回填 docs/channel_mapping.csv 后冻结 |
| F03 | SPI 时钟 | ≤200 kHz，起始 100 kHz | CD40109B 电平转换 + 长线；先 100 kHz 验证，逐级提高 |
| F04 | 时钟/锁存极性 | CLK 下降沿移位；LE 高装载 | 对应 HV5622 真值表（S15）；POL 硬接 DRV_VDD，固件不得控制 POL |
| F05 | 消隐 | MCU DISP_ALLOW(IO15) → CD40109B → DRV_BL；BL=0 → 全关 | 更新序列：BL=0 → 移位 → LE 脉冲 → BL=1；DRV_BL 有 10 kΩ 下拉，复位期间为安全态 |
| F06 | 上电顺序依赖 | HV_EN_REQ 只在自检通过后置 1 | HV_EN = DRV_PG·FAULT_OK·HV_EN_REQ；DRV_VDD_EN = EXT12_PG·3V3_PG·HV_EN_REQ；HV_EN_REQ/DISP_ALLOW 均有下拉，复位期间不得为高 |
| F07 | 故障响应 | HVF_NODE 高 → 锁存故障；FAULT_OK=0 → 硬件立即关 HV | HVF_NODE 经 R31/R32/C29/D7/D8 到 U8 比较器与 MCU IO7；固件读 IO7 判故障，不得自动反复复位 |
| F08 | OVP 复位 | 脉宽 ≥0.2 ms，且仅当 HV<198.8 V | OVP 有效时复位无效（等价 SCR 不可关断）；建议先读 HV_SENSE_ADC 确认 <190 V 再复位 |
| F09 | USB-only 供电 | 总电流 ≤500 mA | USB-C 默认电流；固件应在仅 USB 供电时禁止点亮或大幅降占空比 |
| F10 | 显示范围 | 000000–999999，静态驱动 | 每管恒有 1 路阴极导通，无扫描；六位数字分别对应 J_T1..J_T6 |
| F13 | 备用通道 | ch60–63 不使用（NC），发送时填 0 | 映射表 64 行中 60 路接 QS30-1、4 路预留；帧仍需发满 64 位 |
| F11 | 恢复通道 | USB 原生下载 + UART0 | Boot/复位时序见测试计划 A4/A5；TXD0 无过冲 |
| F12 | 版本与位序冻结 | 映射表 + 固件 LUT 同一版本号 | H04 通过后同时冻结 docs/channel_mapping.csv 与固件 LUT 哈希 |

## 与设计/HOLD 的对应

- F05/F06 对应 `design_decisions.md` 门控与下拉设计（ER-14/ER-16）；
- F08 对应 `docs/ovp_timing.md`（复位脉宽 ≥0.2 ms、仅 HV<阈值）；
- F02 冻结依赖 H04（walking-one）；F09 依赖 H05（USB 电流实测）；
- 本清单不替代固件测试计划（`docs/test_plan.md` 阶段 A/B/E）。
