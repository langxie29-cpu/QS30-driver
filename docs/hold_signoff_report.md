# HOLD 签署与关闭联动报告

- 已关闭（CLOSED）：**0**；待签署（PENDING_SIGN）：0；未关闭（OPEN）：7；违规关闭（VIOLATION）：0
- 人工类（H01/H09）未签署：2

> 规则：CLOSED 需同时满足「自动证据判据通过」且「签署字段齐全」；证据未通过却签署 CLOSED 记为 VIOLATION。本报告由 `design/hold_signoff.py` 生成，签署表为 `docs/HOLD_SIGNOFF.csv`。

| HOLD | 自动证据 | 签署人 | 日期 | 版本 | 决定 | 联动结果 | 备注 |
|---|---|---|---|---|---|---|---|
| H01 | manual | FILL | FILL | FILL | OPEN | **MANUAL** |  |
| H02 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H03 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H04 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H05 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H06 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H07 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H08 | missing | FILL | FILL | FILL | OPEN | **OPEN** |  |
| H09 | manual | FILL | FILL | FILL | OPEN | **MANUAL** |  |

## 说明

- 自动证据：`docs/hold_closure_report.md`（未提交=missing，部分=partial，通过=complete，判据失败=fail）；
- 人工类 H01/H09 无 CSV 证据，需签署 + 附审查记录；
- 只有 CLOSED 才意味着该 HOLD 解除对投板/生产的阻塞；VIOLATION 必须撤销。
