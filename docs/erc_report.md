# QS30-6 REV.A 自动一致性检查/ERC 记录

由 `design/build.py` 依据 datasheet 引脚库自动生成；立创EDA 内仍需重新执行原生 ERC 并逐条解释。

| 编号 | 结果 | 说明 |
|---|---|---|
| ERC-01 | **PASS** | 所有器件引脚均已分配网络或显式 NC |
| ERC-02 | **PASS** | 无单引脚网络 |
| ERC-03 | **PASS** | 43 个必需网络全部存在 |
| ERC-04 | **PASS** | GPIO/焊盘映射与交接表一致（19 项） |
| ERC-05 | **PASS** | HV5622 POL 固定接 DRV_VDD（避免 BL 有效时全开） |
| ERC-06 | **PASS** | DRV_BL 在 12 V 驱动域有 10 kΩ 下拉（默认消隐） |
| ERC-07 | **PASS** | HV_EN 有 100 kΩ 下拉 → GPIO/门控悬空时升压关断 |
| ERC-08 | **PASS** | GPIO0/BOOT 有 10 kΩ 上拉 |
| ERC-09 | **PASS** | GPIO46 保持 10 kΩ 下拉（启动条件） |
| ERC-07b | **PASS** | HV_EN_REQ 有外部 100 kΩ 下拉 → 复位期间默认不请求升压 |
| ERC-06b | **PASS** | DISP_ALLOW 有外部 100 kΩ 下拉 → 复位期间默认消隐 |
| ERC-10 | **PASS** | EN RC = 10 kΩ + 1 µF（Espressif 推荐值） |
| ERC-11 | **PASS** | 14 个 IC 均有电源去耦电容 |
| ERC-12 | **PASS** | HV5622 x2 = 64 路 ≥ 60 路（60 路已用） |
| ERC-13 | **PASS** | HV 网络 88 个（含阳极/阴极/采样/反馈） |
| ERC-14 | **PASS** | 3.3 V GPIO 与 DRV_VDD 域之间均有电平转换/隔离 |
| ERC-15 | **INFO** | HV5622 VPP 设计最大 172 V < 推荐 220 V / 绝对最大 230 V；驱动逻辑 VDD 11.5 V 在 10.8–13.2 V 内 |
| ERC-16 | **INFO** | BOM 状态分布: HOLD=6, PROVISIONAL=40, VERIFIED=181 |
| ERC-17 | **INFO** | HV 间距/爬电距离尚未冻结（H07），PCB 规则当前为 1.0 mm 占位，不得据此投板 |

## 未解决项

