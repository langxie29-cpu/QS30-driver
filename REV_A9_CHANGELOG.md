# REV.A9 变更记录（九位模块化重构）

## r9.1 — 2026-10-18（初始重构）

- 新增 docs9/：审计、架构、网表、90 路映射、接口、ERC9（36/36）、BOM-A/B/C、成本、机械、
  驱动比较、G0–G5、EDA 状态、最终 A–G 报告；
- 旧六位 REV.A 保留为 Legacy（commit 52eaa95，README 说明）；
- 修复：P0-03（HV5622 料号）、P0-01（LM393 共模，U8 改 1.0 V 基准）、
  P1-01（DRV_PG 11.2 V）、P1-03（OVP 窗口 192.5–204.5 V）、P1-02（DCM/CCM 分模式重算）；
- 新增 SAFETY_LOOP、模块接口、96 bit 帧、3×HV5622；
- 未实现：原生 EDA/ERC/DRC、Gerber、实物验证；禁止投板/下单。

> 本变更未做 force push / reset --hard；旧提交与文件保留。
