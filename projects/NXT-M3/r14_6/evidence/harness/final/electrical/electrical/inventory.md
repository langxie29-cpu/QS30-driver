## R14.6 保护端点与模型边界

| 项目 | 复核结果 |
|---|---|
| 原生 DRC | KiCad 10.0.8：ERC 0/0；clearance 组 103→79；未连接 84→65；parity 0；新增违规 0；既有连接丢失 0；阴极 30/30、端点 180/180。 |
| 保护计数 | OVP/FB/SNUB 14→20；J6 39→39；寄存器开路 SER2/SER3/SR_CLK_BUS/HC_CLEAR_N 各 1。 |
| 端点状态 | 已接通项见 R81.1→C47.1、R83.2→R84.1、SNUB 两端、C35.1→U13.2；R61.2→R62.1、D3.1→C47.1、看门狗及部分 J6/许可/硬件消隐仍未接通，不能签署实板 STOP/OVP/OCP/重新使能/泄放。 |
| 模型边界 | 可见 8 个仿真 case 均 exit 0、ngspice-46 DLL、applied_to_final_hardware=false；OVP 代理 trip 约 21.893 ms、25 ms 母线约 187.86 V 属 R11 空载反馈故障 fixture，非最终板验证。 |
| 门禁 | POWER_SIMULATION、EVT_RELEASE、HV_POWER_ON 均 HOLD；下一门禁需端到端布线、DNP/装配确认、独立硬件保护路径及最终模型/实板复测计划。 |
