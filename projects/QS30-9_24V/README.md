# QS30-9 — 24V重构项目

状态：S06B-QUALIFICATION-AUDIT，已接续核查原失败、精确器件模型、损耗/退磁与PG/USB边界；24V-07未通过，08未进入，制造HOLD。

目标：24V输入，170V九管高压，约12V驱动/控制辅助轨，3.3V逻辑；本轮优先24→5V→3V3与USB电源选择，USB启动/枚举资格仍未通过。

- 本轮方案与执行：[docs/S06B_PLAN.md](docs/S06B_PLAN.md)、[docs/SPRINT06B_REPORT.md](docs/SPRINT06B_REPORT.md)
- S06历史交付：[docs/SPRINT06_REPORT.md](docs/SPRINT06_REPORT.md)
- 最新接续断点：[docs/BREAKPOINT_S06B_2026-11-15.md](docs/BREAKPOINT_S06B_2026-11-15.md)
- S05历史交付：[docs/SPRINT05_REPORT.md](docs/SPRINT05_REPORT.md)
- 原始完整范围：[docs/NEXT_SPRINT.md](docs/NEXT_SPRINT.md)
- 机读任务及验收：[docs/TASKS.csv](docs/TASKS.csv)
- 项目参数入口：[config/project.json](config/project.json)，当前为[S06B资格审查增量](config/sprint06b.json)，继承[S06候选](config/sprint06.json)与[S05数值要求](config/sprint05.json)
- 旧电源域逐引脚审查入口：[docs/LEGACY_POWER_CONNECTIONS.csv](docs/LEGACY_POWER_CONNECTIONS.csv)
- 12V设计与Sprint04只读来源：baseline_snapshot/；旧电路快照不是24V原理图。

design/sim/kicad/bom/netlist/sources为新版本独立输出区域，目前没有已改造的原生工程。禁止运行旧生成器向旧目录回写；新生成器必须显式绑定本项目目录并验证写入边界。
