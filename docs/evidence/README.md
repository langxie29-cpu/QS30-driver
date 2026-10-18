# HOLD 关闭证据（模板）

用法：
1. 现场测试后，把 `FILL` 替换为实测值（保持列名与行序不变；Excel 另存为 UTF-8 CSV）。
2. 运行 `python design/evidence_check.py`，生成 `docs/hold_closure_report.md`：
   - 全部为 FILL → 该项记为"未提交"；
   - 部分填写 → "部分提交（需补全）"；
   - 全部填写 → 自动判据校验，输出 PASS/FAIL 与失败原因。
3. 证据 PASS 后仍需人工签署 `HOLD_REGISTER.md` 的关闭记录；自动校验不替代签审。

| 文件 | 对应 HOLD | 自动判据 |
|---|---|---|
| H02_tube_pin_test.csv / H02_tube_operating_point.csv | H02 | 期望发光/不发光；U_tube/I 范围 |
| H03_socket_measurement.csv / _views.csv / _continuity.csv | H03 | 全部数值已填、3 样本一致性、13 触点连通 |
| H04_walking_one.csv | H04 | 观测=期望，60 路双射（无重复/遗漏） |
| H05_power.csv | H05 | 每项落在 limit_min..limit_max |
| H06_hv.csv | H06 | 同上（OVP/浪涌/泄放/温升） |
| H07_spacing.csv | H07 | 实测 ≥ required（占位值，标准定稿后更新） |
| H08_rf.csv | H08 | 记录齐全（阈值待整机 RF 目标确定） |
