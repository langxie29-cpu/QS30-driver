# 绝缘与 C48 变更复核

- 范围/判定：仅基于 `r14_6` 三份摘要做桌面筛查复核；本清单为 **screening/ECR 复核**，不是 release 或装配资格。
- 路由筛查：KiCad 10.0.8 native before/after 均为 ERC 0/0；clearance 计数 103→79，unconnected 84→65；`added_violations=0`、`prior_connections_lost=0`。after 分组：MMBTA42 60、LV 同封装 16、开关封装 3；OVP/FB/SNUB 计数 14→20、J6 39→39；`register_opens` 中 SER2/SER3/SR_CLK_BUS/HC_CLEAR_N 各 1。
- Q1–Q30：60 对 C–B/C–E 约 1.1102 mm，低于 2.00 mm 筛查阈值，全部 **HOLD**；300 V C–E/C–B 为器件电气额定，不是已装配封装绝缘认证；峰值端点电位未测，引脚/共面/贴装/焊锡/污染/CTI/海拔/凝露待评。MJE340G 替代需独立 ECR。
- 外部铜/分压：R81–R83 由 B.Cu 改 F.Cu；文档称反馈链与残压链五对异面铜通过当前 2.00 mm 原生筛查；不同面介质材料、厚度和工厂公差仍须实际四层叠构验证。理想静态计算：170 V 时 41.53–42.25 V，195 V 时 47.64–48.46 V；195 V 且另一上臂短路时健康同阻值上臂约 63.04–64.50 V；下臂短路每颗约 48.75 V；上臂开路可近满母线。脉冲、耦合、电阻额定、爬电与实际料号未定。R60–R63、R65–R68、R81–R85 维持既有 DNP。
- C48/开关：C48 改为 KEMET C2220C101JDGACTU（100 pF、±5%、C0G、1 kVDC；2220 median land 1.50×5.40 mm、中心距 5.30 mm、铜距 3.80 mm）；C48 与 R86 保持 DNP。ECR 记录两端接回、原 1.80 mm 违规消除；SNUB 新铜约 14.14 mm、GND 新铜约 12.17 mm，均背层无新增换层但会改变脉冲环路电感。仍需测有效电容、脉冲电流、焊料外缘、使用温度和工作峰值。SW_HV/SNUB 使用 3.20 mm 原生筛查；重复峰值、地弹、关断过冲均为 **UNKNOWN**。D3（ES1G，400 V/1 A、25 ns 条件）、Q32 原生净距 **HOLD**；D3.1→C47.1 仍开路。
- 限制：`MMBTA42_INSULATION.csv`、`HV_EXTERNAL_CLEARANCE.csv`、`SWITCH_PACKAGE_CLEARANCE.csv` 被引用但未随输入提供，逐对台账未能独立复核；外部 URL 未独立打开。
- 下一闸门证据：逐对 CSV/坐标与规则哈希核对；四层叠构与介质证据；C48 有效电容/脉冲/温升/焊料外缘/工作峰值；开关节点重复峰值与回路电感波形；D3/Q32 反压、恢复、SOA、热与布局资格；IEC 60664-1 适用性及 60664-4 重复波形评审。
