# 测试计划 ↔ 证据一致性检查

由 `design/test_plan_check.py` 从 `docs/test_plan.md`（人读）+ `docs/test_plan.csv`（机读）自动生成；**5/5 项通过**。

| 编号 | 结果 | 内容 |
|---|---|---|
| T1 | PASS | 37 项；阶段 ['A', 'B', 'C', 'D', 'E']；重复序号 无；非法状态 无 |
| T2 | PASS | 每个测试项的 evidence_target 均指向存在的证据文件 |
| T3 | PASS | 证据 CSV 10 个，全部被测试计划引用 |
| T4 | PASS | 阶段↔证据映射正确（C→H06、C0→H07、D→H02/H03、B→H04、E3→H08） |
| T5 | PASS | test_plan.md 序号 37 个，CSV 37 个，一致 |

## 测试项一览（阶段 / 证据目标 / 状态）

| 阶段 | 序号 | 测试 | 证据目标 | 状态 |
|---|---|---|---|---|
| A | A1 | 12V 上电测五路电源 | H05:H05_power.csv | 待执行 |
| A | A2 | 仅 USB-C 供电 | H05:H05_power.csv | 待执行 |
| A | A3 | 电源切换四状态 | H05:H05_power.csv | 待执行 |
| A | A4 | BOOT/RESET/EN 时序 | N/A:示波器截图 | 待执行 |
| A | A5 | USB 原生下载与 UART0 恢复 | N/A:记录归档 | 待执行 |
| A | A6 | GPIO 默认状态 | N/A:逻辑分析仪记录 | 待执行 |
| A | A7 | Wi-Fi 峰值电流与 3V3 压降 | H05:H05_power.csv | 待执行 |
| A | A8 | 按键/LED/I2C 预留 | N/A:目视记录 | 待执行 |
| B | B1 | 3.3V→12V 电平转换 | N/A:示波器记录 | 待执行 |
| B | B2 | 64bit 帧时序 | N/A:逻辑分析仪记录 | 待执行 |
| B | B3 | walking-one 位序 | H04:H04_walking_one.csv | 待执行 |
| B | B4 | 60 路通道映射 | H04:H04_walking_one.csv | 待执行 |
| B | B5 | 消隐与全关 | N/A:示波器记录 | 待执行 |
| B | B6 | 上电/复位默认态 | N/A:示波器记录 | 待执行 |
| B | B7 | 更新流程 | N/A:逻辑分析仪记录 | 待执行 |
| C | C0 | PCB 高压间距/爬电实测 | H07:H07_spacing.csv | 待执行 |
| C | C1 | 空载/单管/六管稳态 | H06:H06_hv.csv | 待执行 |
| C | C2 | 启动与软启动 | H06:H06_hv.csv | 待执行 |
| C | C3 | 输入 11.4/12/12.6V | H06:H06_hv.csv | 待执行 |
| C | C4 | 负载突变 6→1→6 | H06:H06_hv.csv | 待执行 |
| C | C5 | 反馈分压开路 | H06:H06_hv.csv | 待执行 |
| C | C6 | 输出短路 10Ω | H06:H06_hv.csv | 待执行 |
| C | C7 | 输入突然断开 | H06:H06_hv.csv | 待执行 |
| C | C8 | 浪涌电流 | H06:H06_hv.csv | 待执行 |
| C | C9 | 阳极电阻单管短路 | H06:H06_hv.csv | 待执行 |
| C | C10 | 长时运行 30min | H06:H06_hv.csv | 待执行 |
| D | D1 | 逐脚限流点亮 | H02:H02_tube_pin_test.csv | 待执行 |
| D | D2 | 起辉/熄灭电压 | H02:H02_tube_operating_point.csv | 待执行 |
| D | D3 | 工作点 | H02:H02_tube_operating_point.csv | 待执行 |
| D | D4 | 管座插拔 | H03:H03_socket_measurement.csv;H03:H03_socket_views.csv;H03:H03_socket_continuity.csv | 待执行 |
| D | D5 | 批次记录 | H02:H02_tube_operating_point.csv | 待执行 |
| E | E1 | 静态六位 000000–999999 | N/A:视频记录 | 待执行 |
| E | E2 | 整机功耗与温升 | H05:H05_power.csv | 待执行 |
| E | E3 | Wi-Fi 三状态干扰 | H08:H08_rf.csv | 待执行 |
| E | E4 | 长时间显示与轮换 | N/A:记录归档 | 待执行 |
| E | E5 | 故障注入 | N/A:记录归档 | 待执行 |
| E | E6 | 失效状态与下载恢复 | N/A:记录归档 | 待执行 |

说明：`evidence_target` 为 `HOLD:CSV` 时，CSV 位于 `docs/evidence/`；`N/A:*` 表示该测试只需人工记录（截图/波形/视频），不进入自动证据判据。
