# QS30-6 REV.A 资料登记与版本记录

状态：**当前基线** ｜ 查阅日期：2026-10-18 ｜ 维护：REV.A 设计

原则（Evidence First / Claims Second）：本文件只登记**实际下载并核对过原文**的资料。
未取得原文的参数一律降到 `STRONGLY SUPPORTED` / `PROVISIONAL`，不得写成 VERIFIED。

| 编号 | 资料 | 版本/日期 | 用于 | 核对方式 |
|---|---|---|---|---|
| S1 | Espressif《ESP32-S3-WROOM-1 & WROOM-1U Datasheet》 | 官方英文 PDF，53 页 | 模组焊盘表 3-1、尺寸 18.0×25.5 mm、天线禁布、功耗 | 下载 PDF + 交叉核对 Espressif KiCad 符号库焊盘表 |
| S1b | Espressif《ESP32-S3 Hardware Design Guidelines》Schematic Checklist / PCB Layout Design | 在线 latest 版 HTML（2026-10-18 抓取） | EN 10 kΩ+1 µF、strapping（GPIO0/3/45/46）、USB 22/33 Ω、U0TXD 499 Ω、ADC 0.1 µF、天线禁布/净空 | 抓取正文逐条摘录 |
| S2 | Espressif `ESP32-S3-WROOM-1.kicad_mod` / `Espressif.kicad_sym` | kicad-libraries main 分支 | 焊盘 1–41 编号、中心焊盘 41、模组 18×25.5、天线区约 6 mm | 解析符号库引脚表与封装焊盘坐标 |
| S5 | Microchip《HV5622 32-Channel Serial-to-Parallel Converter》 | DS20005854A，2017 | 32 路输出、VDD 10.8–13.2 V、VPP 推荐 ≤220 V / 绝对最大 230 V、PQFP-44 与 PLCC-44 引脚表、Table 3-2 真值表、时序 | 下载 PDF，逐页核对 Table 2-1/3-2 |
| S6 | 南昌电子管厂《QS30 型辉光放电数码管说明书》（Dieter Wächter Nixie 档案扫描件） | 原厂说明书扫描 3 页（tube-tester.com） | **电极接线图（1/8 脚非显示电极、2=A、3=K0、4=K9…13=K1）**、基本参数、外形尺寸、管基 GB 787-74 J13-1A | 扫描页放大读图 + 表格识别 |
| S8 | TI《TPS54202 4.5–28 V Input, 2-A Synchronous Step-Down》 | SLVSD26C，Rev. 2026 | SOT-23-6 引脚 1GND/2SW/3VIN/4FB/5EN/6BOOT、Vref 0.596 V、500 kHz、5 ms 软启动、θJA 118.6 °C/W | 下载 PDF，核对 §4 Pin Functions |
| S9 | 双肖特基 OR 方案 | 通用工程做法（非单一器件） | 5V_SYS 反向阻断候选参考实现 | 设计推导，非原厂资料 |
| S10 | Silergy《SY8089/SY8089A 2 A Synchronous Step-Down》 | AN_SY8089/SY8089A 应用手册 | SOT-23-5 引脚 1EN/2GND/3LX/4IN/5FB、2.7–5.5 V、2 A、Vref 0.6 V、θJA 170 °C/W | 下载 PDF，核对 Pin Description |
| S12 | UMW《USBLC6-2SC6》 | Nov. 2024 | SOT-23-6 引脚 1/6=I/O1、3/4=I/O2、2=GND、5=VBUS；ESD ±30 kV | 下载 PDF + 渲染首页引脚图 |
| S13 | TI（Harris）《CD40109B CMOS Quad Low-to-High Voltage Level Shifter》 | SCHS099B（2003）/ CD40109B-Q1 SCHS380A | 16 脚：1=VCC、2/7/9/15=ENABLE A–D、3/6/10/14=A–D、4/5/11/13=E–H、8=VSS、12=NC、16=VDD；VCC/VDD 3–18 V；三态输出；VCC 与 VDD 任意上电顺序 | 扫描件渲染 Fig.1 逻辑图 + 引脚注记 |
| S14 | TI《LM393 双比较器》 | SLCS005AH，Rev. 2025 | SOIC-8 引脚 1=1OUT、2=1IN−、3=1IN+、4=GND、5=2IN+、6=2IN−、7=2OUT、8=VCC | 下载 PDF，核对 Table 4-1 |
| S15 | TI《SN74HC08 四路与门》 | SCLS081J，Rev. 2025 | SOIC-14 引脚 1–6=通道 1/2、7=GND、8=3Y、9=3A、10=3B、11=4Y、12=4A、13=4B、14=VCC | 下载 PDF，核对 Pin Functions 表 |
| S16 | TI《UC3843 电流型 PWM 控制器》 | SLUS223H，Rev. 2024 | DIP-8/SOIC-8 引脚 1=COMP、2=VFB、3=ISENSE、4=RT/CT、5=GROUND、6=OUTPUT、7=VCC、8=VREF；UC3843 UVLO 8.4 V/7.6 V；最大占空比 100% | 下载 PDF，核对 §5 |
| S17 | TI《TL431 可调基准》 | SLVS543S，Rev. 2024 | **DBZ(SOT-23-3)：1=CATHODE、2=REF、3=ANODE**（Table 5-1）；Ika 1 mA 起 | 下载 PDF，渲染第 4 页引脚图 |
| S18 | Vishay IRF740 / UF4007 数据手册 | **未取得原文（供应商链接 404）** | TO-220 的 G/D/S 与 SMA 的 K/A 为行业标准引脚 | **STRONGLY SUPPORTED**，归档时须补原厂 PDF |
| S19 | 分立器件（MMBT3904/3906、2N7002、DMP3098L、SS54、SS14、SMBJ16A、BAT54） | 通用器件 | 引脚形式为 SOT-23/SMB/SMA 标准；参数按型号标称 | **STRONGLY SUPPORTED**，采购前核对完整料号数据手册 |
| S20 | 立创商城 / 立创EDA 元件库 | 2026 年在线 | 料号、封装、库存（未逐项核对） | **HOLD（H05/H09）**：不能以"商城有料"替代数据手册 |
| S21 | GB 787-74《电子管管基尺寸》 J13-1A | **仅检索到标准条目，未取得正文/尺寸表** | 13 脚管基机械基准 | **HOLD（H03）**：不得凭"13 脚"推断机械兼容 |

## 资料使用边界（重要）

1. **S6 是本项目唯一可直接引用的 QS30-1 原始资料**。旧交接文件引用的 S6（《无线电通信用电真空器件手册》QS30 系列页）只是系列级参考；
   本次已用**南昌厂原厂说明书**替换该参考，脚号映射与工作参数按 S6 原厂页锁定（见 design_decisions D-01/D-03）。
2. S6 未给出**管座**尺寸；管座为 J13-1A 形式，但"J13-1A"只是管基型号，**不等于任何在售管座**。PCB 封装必须等 H03 证据。
3. S5 的 230 V 是绝对最大额定值，**不是工作点**；本项目 HV_BUS 设计 172 V、OVP 198.8 V。
4. S1b 的 15 mm 外壳净空是 Espressif 的整机建议，最终以官方模块布局图 + 整机 RF 实测为准（H08）。
5. 所有"仿真结论"来自 `design/sim_boost.py` 的开关级**行为模型**（已实际运行），不是器件级 SPICE；模型边界见 `sim/README.md`。
