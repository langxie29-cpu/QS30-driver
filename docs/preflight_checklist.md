# 投板前检查清单（自动汇总）

**当前状态：🚫 RELEASE BLOCKED — 不得投板 / 下单 / 释放 Gerber**

- 机器检查：11/11 通过；HOLD：CLOSED 0/9；未关闭 9 项
- 判定依据：任一 HOLD 未 CLOSED，或任一机器检查 FAIL → RELEASE BLOCKED。本脚本**不会自动放行**，最终放行必须人工在 `HOLD_REGISTER.md` 签署。

## 1. 机器检查

| 检查 | 结果 | 详情 |
|---|---|---|
| ERC（19 项，0 错 0 警） | PASS | 器件 227/引脚 736/网络 172/通道 60；错误 0 告警 0 |
| DRC 预检（14 项） | PASS | 14/14 |
| SPICE 自检 4/4 | PASS | RC/RL/二极管/B 源 |
| 开关级功率级 | PASS | Vout 171.99 V，效率 95.9% |
| 平均模型闭环 8/8 | PASS | 8/8 |
| OVP 保护逻辑 7/7 | PASS | 首次触发 198.92 V，峰值 201.92 V |
| 测试计划一致性 5/5 | PASS | 5/5 |
| BOM 选型复核 5/5 | PASS | 5/5 |
| 文档一致性 5/5 | PASS | 5/5 |
| 热/浪涌复核 | PASS | HV5622 温升 0.7–6.3 °C；启动峰值 3.12 A；I²t 0.0010 A²s |
| 固件约束派生 | PASS | 13 条；帧 64 bit；8 控制脚 |

## 2. HOLD 状态（来自签署联动报告）

| HOLD | 状态 |
|---|---|
| H01 | **MANUAL** |
| H02 | **OPEN** |
| H03 | **OPEN** |
| H04 | **OPEN** |
| H05 | **OPEN** |
| H06 | **OPEN** |
| H07 | **OPEN** |
| H08 | **OPEN** |
| H09 | **MANUAL** |

## 3. 投板前必须关闭/冻结的事项

| 事项 | 解除条件 | 关联 |
|---|---|---|
| H01 旧基线原理图/PCB 原件 | 需原始工程文件与版本确认 | H01 |
| H02 QS30-1 六管工作点/脚位实测 | 需实物管 + 单管夹具 | H02 |
| H03 13 脚管座实测 → 封装冻结（14 个 TBD 字段） | 需购样管座 + 卡尺/影像仪 | H03 |
| H04 walking-one 位序回填（当前 PROVISIONAL） | 需焊好的驱动板 + 低压测试负载 | H04 |
| H05 低压电源/USB 实测 | 需样机（低压部分） | H05 |
| H06 高压实测（含 OVP 时序/温升/Coss/PPTC） | 需隔离测试区 + 差分探头 | H06 |
| H07 高压间距/爬电标准定稿 | 需结构/标准输入 + PCB | H07 |
| H08 整机 RF（装壳后） | 需外壳与整机 | H08 |
| H09 立创EDA 工程与原生 ERC/DRC 验收 | 需立创EDA + 人工审查 | H09 |
| U20 封装冻结（DIP-8 / SOIC-8） | 结构与散热确定后二选一 | D-29 |
| HV5622 手册参数（VDD 电流/Von/Rth_ja） | 需厂商手册核实 | thermal_review |
| PPTC 手册 I²t / 触发曲线 | 需厂商手册 + H05/H06 波形 | I-25 |

## 4. 放行流程（人工）

1. 实物测试 → 回填 `docs/evidence/*.csv` → `python design/evidence_check.py` 判据通过；
2. 在 `docs/HOLD_SIGNOFF.csv` 填写签署人/日期/版本并决定 CLOSED → `python design/hold_signoff.py`；
3. 重建原生 EDA 工程并跑 ERC/DRC（H09），记录到 `docs/`；
4. 重新运行本清单：状态变为"机器检查全绿"且所有 HOLD=CLOSED；
5. 人工复核后按 `HOLD_REGISTER.md` 签署放行，才允许生成/释放 Gerber。

> 摘要：本设计当前**不具备投板条件**——所有阻塞均需实物数据或原生 EDA，不是软件侧可关闭项；已执行部分见审查包与各检查报告。
