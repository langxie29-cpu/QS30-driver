## 清点
- round1/a_low_50k：87,080 行后 t=2.85837 ms 报 `TRAN: Timestep too small`，步长 1.25e-19，节点 `e.x_ctl.xea.eb1#branch`；`uic` 跳过工作点，`v.x_ctl.vr2` 无值按 DC 0。
- round2/a_low_ea_trap：加 `cshunt` 187×1e-14 F 后 25,589 行，t=1.30254 ms 同一分支同类报错；加电容未消除。
- a_boost.inc：UCC3803 子电路；开关/整流为代理；反馈 645.12k/7.68k，补偿 220p，R_CT 60.4k。
- device_facts：UCC3803 UVLO 启动 3.7/4.1/4.5 V，停止 3.2/3.6/4.0 V；4.30 V 不能保证最坏器件启动。
- 限制：未运行仿真、未做物理测试；根因仍为待验证假设。
