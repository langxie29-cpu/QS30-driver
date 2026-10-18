# QS30-9 / REV.A9.1 三板电气架构冻结

日期：2026-10-18。基线 `b6a9082`；分支 `rev-a9-1-electrical-freeze`。
本文件与 QS30_PIN_MAPPING、INTERCONNECT_PINOUT、NETLIST_RECONCILIATION、EDA_ISSUE_REGISTER 为 A9.1 有效输入；旧 REV.A9 报告保留为历史证据，冲突处以本组文件为准。

## 冻结边界

| 实体 PCB | 功能及器件 DesignRef | 电源与接口 |
|---|---|---|
| 左 DISPLAY | T1–T3、U_L HV5622PG-G、U_LS_L 上转换、U_DS_L 下转换、6 个阳极串联电阻、本地去耦/泄放、R_SAFE_L | LV16P 与 HV2P 接 MAIN；本地不产生 HV |
| 中央 MAIN | T4–T6、U_C、U_LS_C、U_DS_C、6 个阳极串联电阻；U10 ESP32-S3；12V 输入/USB 电源 OR/5V/3V3；DRV_VDD 开关/PG；UC3843 升压、OVP/门控、安全回路 | 仅一块中央主板；中心显示部分为板内连接，没有第三组可拆电缆 |
| 右 DISPLAY | T7–T9、U_R、U_LS_R、U_DS_R、6 个阳极串联电阻、本地去耦/泄放、R_SAFE_R | 与左模块共用 DISPLAY 电气/PCB 模板；装配位置决定 T7–T9 |

因此是 **三块实物 PCB、两套 KiCad 原生项目**。MOD_L/MOD_C/MOD_R 是功能域，不是三个独立显示 PCB 加一块主板。早期 cost9.json/COST9.md 中“四块板”不是本轮冻结采购数量；本轮不重新报价、不生成制造文件。板框 100×100/120×90 mm 仍为占位，不是机械冻结。

每管 1 阳极 + 10 数字阴极：9 个独立阳极限流支路、90 个阴极网络。每颗 HV5622 只负责本模块 30 个阴极，剩余 HVOUT31/32 不接；3×32=96，90 使用、6 未使用。阳极不计入 96 路预算。

## 电源域与地

| 域 | 用途 | 边界与状态 |
|---|---|---|
| EXT12_RAW/EXT12 | 12V 输入，经保险/二极管保护后分配 | 实际输入范围/瞬态、功率裕量待验证 |
| VBUS/EXT5/5V_SYS/3V3 | USB/辅助降压、MCU 与连接器逻辑 | 3V3 信号不允许被 12V DOUT 直接驱动 |
| DRV_VDD | HV5622 与上转换输出域，推荐 10.8–13.2V | 受控 12V 电源；不是 HV_BUS；失电时序仍 HOLD |
| HV_BUS | 单一升压输出，名义 172.18V | 正常工作目标，不是实测值；OVP 192.5–204.5V 仅静态阈值目标，动态过冲未确定 |
| GND | LV 电源/逻辑地，包含 HV5622 VSS | 非隔离系统；承载管阴极电流，经 LV 地针回 MAIN |
| GND_HV | HV 电容/泄放返回 | 仅 MAIN 的 R_HV_STAR(0Ω) 接 GND；模块不再增加 GND_HV↔GND 连接 |

HV2P 的返回针承载模块电容充放电/泄放回流；阴极电流路径为 HV_BUS→本管20kΩ→管子→HVOUT→VSS→LV GND→MAIN。这样没有模块本地地桥形成第二条阴极并联回流。LV 的多个 GND 针有意并联，均必须接线；不是几种独立地。布局须隔开开关功率环、模拟参考和信号地，主板单点连接位置与线宽仍需验证。R_HV_STAR 是显式电气连接，不是已验证安规隔离器件。

## 串行与控制信号流

`MCU 3V3 → L上转换 → U_L → L下转换 → MAIN R62(0Ω) → C上转换 → U_C → C下转换 → MAIN R63(0Ω) → R上转换 → U_R → R下转换 → MAIN R61(100kΩ)`。

CLK/LAT/DISP_ALLOW 为 3V3 并行分配，每模块 U_LS_x 转为 DRV_VDD 域；中央 U_C 的 DIN 也必须经过 U_LS_C，不能绕过。HV5622 DOUT 是 VDD 域推挽输出；新增 U_DS_x CD40109B 将其转回 3V3。使用 CD40109BNSR（SOP/NS 16脚）；旧 CD40109BE 与 SOIC-16 的料号/封装不一致已更正，实际焊盘几何仍 HOLD。

每帧 96 个下降沿移位；先送 R32…R1，再 C32…C1，最后 L32…L1，字节 MSB-first。POL=DRV_VDD 时位1导通、位0关断；BL=0 全关；LE=1 透明装载、LE=0 保持。未用31/32位固定送0。上电先禁止 HV、BL保持0、装入全0并锁存，低压验证后才允许显示。未执行固件/逻辑分析仪实测。

依据 [Microchip DS20005854A](https://ww1.microchip.com/downloads/en/DeviceDoc/20005854A.pdf) Table 2-1、3-1、3-2：PG-G 为44脚PQFP；32路开漏输出；CLK下降沿；VDD推荐10.8–13.2V，HVOUT推荐最高220V（230V为绝对最大，不能作工作目标）。下转换依据 [TI CD40109B](https://www.ti.com/lit/ds/symlink/cd40109b.pdf) p1 的 VCC>VDD 工作方式。官方 PDF、URL 与 SHA256 已存 `sources/A9_1/`。新增转换级的传播延迟、波形与掉电行为仍需低压台架验证，100kHz是待验收目标而非已验证能力。

## 安全链及下一阶段边界

安全回路：3V3→R57→R64→左模块→R59→中心板内R_SAFE_C→R60→右模块→R58下拉，终点送 U7.13/U10.24。左右拔线应中断；中心直通只能证明板内回路存在，不能检测中心管是否装好。MCU请求、DRV_PG、FAULT_OK、安全回路参与 HV 许可，但当前模拟门控/OVP 有明确 P0 接线风险，见问题表。

架构/通道/板间信号定义已冻结，**保护功能与制造仍 HOLD**。机械需实际管座13触点→焊脚通断和XY/观察面、连接器确切型号/尺寸/额定、绝缘及装配间隙。下一步按 OVP_SIMULATION_INPUTS.md 建立“当前接线失败复现”和修正版仿真；不能沿用旧“极性正确/泄放PASS”作为放行证据。
