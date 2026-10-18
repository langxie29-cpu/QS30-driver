# 立创EDA 工程构建说明（REV.A 可复现步骤）

本仓库**没有**直接产出 `.epro`/立创EDA 工程文件（当前环境未安装立创EDA，无法创建并校验原生工程）。
按本说明可在立创EDA（专业版）中重建与 `netlist/QS30-6_REV.A_netlist.csv` **逐引脚一致**的工程。
不要去"凭记忆连线"——所有连接以 CSV 网表与 `docs/schematic/page_*.png` 连接表为唯一依据。

---

## 0. 输入文件

| 用途 | 文件 |
|---|---|
| 逐引脚连接（权威） | `netlist/QS30-6_REV.A_netlist.csv`（ref, pin, pin_name, net, net_class） |
| 网络汇总 | `netlist/QS30-6_REV.A_nets.csv` |
| 器件清单 | `bom/QS30-6_REV.A_BOM.csv` |
| 通道映射 | `docs/channel_mapping.csv` |
| 管脚映射 | `docs/qs30_1_pin_mapping.csv` |
| 分页连接表图 | `docs/schematic/page_01.png` … `page_09.png` |
| 系统框图 | `docs/schematic/QS30-6_REV.A_系统框图.png` |
| 预布局 | `docs/prelayout/QS30-6_REV.A_prelayout.png` |

## 1. 新建工程与图纸

新建"QS30-6 REV.A"，按 6 页组织（与网表 sheet 列一致）：

| 页 | sheet 代码 | 内容 |
|---|---|---|
| P1 | `01_PWR` | 输入保护、12V→5V、5V_SYS OR、5→3.3V、DRV_VDD 开关 |
| P2 | `02_MCU` | ESP32-S3-WROOM-1-N8、USB-C、UART0、按键、HV 采样/故障接口 |
| P3 | `03_DRV` | HV5622 ×2、CD40109B ×2、LM393 ×2、TL431、74HC08 |
| P4 | `04_HV` | UC3843 升压、OVP 与锁存、OVP 复位、HV 输入开关 |
| P5 | `05_TUBE` | J31–J36 管座、12 只 10 kΩ/2 W 阳极电阻 |
| P6 | `06_TP` | TP1–TP20、J4 扩展 |

## 2. 建库（必须先做，顺序不能反）

1. **QS30-1 符号**：13 脚，脚号 1–13 = 物理脚号；名称按 `docs/qs30_1_pin_mapping.csv`
   （1/8 = `IC_KEEP_OPEN`，2 = A，3=K0、4=K9、5=K8、6=K7、7=K6、9=K5、10=K4、11=K3、12=K2、13=K1）。
   - **禁止**把焊盘编号按数字 0–9 重排；符号脚号必须等于实物脚号。
   - 属性：Supplier Part 留空（H02 关闭后填批次）。
2. **13 脚管座封装**：当前为 **PROVISIONAL 草案**——
   - 焊盘数 13、编号 1–13 与符号一一对应；
   - 焊盘坐标/孔径/节圆直径：**留空并标注 TBD**，直到 H03 实测（不得猜测、不得复制相近管座）；
   - 建 1:1 打印页（A4 100%），用于与实物管座叠图。
3. 其余器件用 LM393/TL431/74HC08/CD40109B/UC3843/HV5622/TPS54202/SY8089A/USBLC6 的商城符号，
   **逐个核对脚号**与 `design/model.py` 的 PIN_DB 一致（TL431 用 DBZ：1=CATHODE/2=REF/3=ANODE）。

## 3. 符号→封装焊盘映射检查表（必须留档）

- [ ] QS30-1：1–13 ↔ 管座焊盘 1–13（1:1）
- [ ] HV5622：PQFP-44，HVOUT1=pin22、HVOUT22=pin1、HVOUT23=pin44、HVOUT32=pin35、VDD=30、VSS=29、POL=27、CLK=28、LE=31、DATA IN=32、DATA OUT=23、BL=33
- [ ] ESP32-S3-WROOM-1：1=GND、2=3V3、3=EN、27=IO0、36=IO44、37=IO43、39=IO1、40/41=GND
- [ ] CD40109B：1=VCC、2/7/9/15=ENABLE、3/6/10/14=输入、4/5/11/13=输出、8=VSS、12=NC、16=VDD
- [ ] TPS54202：1=GND、2=SW、3=VIN、4=FB、5=EN、6=BOOT
- [ ] SY8089A：1=EN、2=GND、3=LX、4=IN、5=FB
- [ ] LM393：1=1OUT、2=1IN−、3=1IN+、4=GND、5=2IN+、6=2IN−、7=2OUT、8=VCC
- [ ] TL431(DBZ)：1=CATHODE、2=REF、3=ANODE
- [ ] 74HC08：8=3Y、9=3A、10=3B、11=4Y、12=4A、13=4B、14=VCC
- [ ] UC3843：1=COMP、2=VFB、3=ISENSE、4=RT/CT、5=GND、6=OUT、7=VCC、8=VREF
- [ ] USB-C 16P：A4/A9/B4/B9=VBUS、A1/A12/B1/B12=GND、A5=CC1、B5=CC2、A6/B6=D+、A7/B7=D−

## 4. 录入网络

两种方式，任选其一，但**不得两法混用后不核对**：

**方式 A（推荐，快）**：用脚本从 CSV 生成"ref.pin=net"清单，按页逐个放置器件后，
用"网络标签 + 短线"把同名网络连起来（连接表式画法）；每页完成后用"设计管理器 → 网络"核对引脚数。

**方式 B**：按 `docs/schematic/page_*.png` 的连接表逐条画线/贴标签。

录入顺序建议：GND/电源网络 → 页内信号 → 跨页信号（DISP_*、DRV_*、HV_*）。

**网络命名（必须与 CSV 完全一致，禁止另起别名）**：
`GND / EXT12_RAW / EXT12_F / EXT12 / EXT5 / VBUS / 5V_SYS / 3V3 / DRV_VDD / HV_IN / HV_BUS /
DISP_DIN / DISP_CLK / DISP_LAT / DISP_ALLOW / HV_EN_REQ / DRV_DIN / DRV_CLK / DRV_LAT / DRV_BL /
DRV_HV_EN_REQ / HV_EN / DRV_VDD_EN / EXT12_PG / P3V3_PG / DRV_PG / FAULT_OK / PG_12V3V / DRV_OK /
HV_FAULT_OD / HVF_NODE / HV_SENSE_ADC / K_T1_0 … K_T6_9 / A_T1 … A_T6`
**禁止把 DRV_VDD 与 3V3 混名，禁止 3.3 V 信号与 DRV 域直连。**

## 5. 网络类别（设计规则前提）

| 类别 | 网络 | 规则（占位，H07 后定稿） |
|---|---|---|
| HV | HV_BUS、SW_HV、CLAMP_N、K_T*、A_T*、A_MID*、OVP_SNS、FB_HV、HVS_* 等 | 间距 1.0 mm 占位；线宽 ≥0.5 mm；HV 回路尽量短 |
| DRV | DRV_VDD、DRV_DIN/CLK/LAT/BL/… | 间距 0.25 mm，线宽 0.2 mm |
| POWER | EXT12/EXT5/5V_SYS/3V3/DRV_VDD/VBUS | 间距 0.25 mm，12 V/5 V 线宽 0.5–1.0 mm |
| DIFF | USB_DP_*、USB_DM_* | 90 Ω ±10%，按板厂层叠计算 |
| SIGNAL | 其余 | 0.2 mm |

## 6. 关键布局约束（来自 `docs/prelayout`）

1. 模组天线端伸出板边；天线投影区及两侧全层禁铜/禁线/禁孔/禁件；外壳净空按 S1b 与实测。
2. 升压功率回路（L20–Q20–D20–C50）面积最小；RCD 钳位紧邻 D20。
3. HV 区与 USB/天线/按键/可触及金属分区，中间 2 mm 隔离带（H07 定稿）。
4. 3V3 去耦（C16–C18）紧邻模组焊盘 2；USB ESD（U11）紧邻 J2；USB 串联电阻靠模组。
5. 六个管座 J_T1..J_T6 按**观看者从左到右**为 1→6，原理图/PCB/固件/装配一致。

## 7. ERC/DRC

1. 执行原生 ERC，把每条错误/警告写入 `docs/erc_report_native.md`（新建），逐条说明保留理由。
2. 执行 DRC，重点：HV 间距、天线禁布、差分阻抗、未连接引脚、焊盘/孔径。
3. 与 `docs/erc_report.md`（本仓库网表级 17 项检查）交叉核对，两者不一致时以**更严格**者为准。
4. 导出：原理图 PDF、PCB 各层 PDF/截图、BOM、网络表、映射表、HOLD 记录（审查包）。

## 8. 已知限制（不得声称已完成）

- 本仓库**未**执行立创EDA 原生 ERC/DRC（无该软件）。
- 管座封装**未定义尺寸**（H03），PCB 预布局只是分区草案。
- 原理图以"连接表式"分页图 + CSV 网表交付，需在立创EDA 中重建为图形原理图后再签审。
