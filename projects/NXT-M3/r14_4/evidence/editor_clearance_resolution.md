# KiCad 10.0.8 PCB 编辑器间距解析

2026-11-22 打开交付路径 `eda/NXT-M3-R14.4.kicad_pcb`。编辑器 DRC 重填在会话内执行，列表显示净距 157、未连接 331。原理图一致性通过本目录机器可读 CLI 报告复验。

在 DRC 各违规的右键菜单运行 Clearance Resolution（间距解析）。以下为编辑器对话框所示电气间距和 DRC 列表实测净距。

| 对象 | 层 | 网络 | 生效规则 | 解析最小 mm | 实际 mm |
| --- | --- | --- | --- | ---: | ---: |
| D3.1–D3.2 | F.Cu | HV_BUS / SW_HV | Switch node provisional repetitive-peak screen | 3.2000 | 1.5000 |
| Q28.2–Q28.3 | B.Cu | GND / K3_7 | HV bus and display conservative creepage screen | 2.0000 | 1.1102 |

D3 解析时接口规则条件不满足，开关规则覆盖之前的约束。Q28 的开关规则条件不满足，解析保留 2.00 mm。对话框的物理间距分析是单独一节。实际违规由 [交付板 DRC](after/DRC.rpt) 归档。接口规则在冻结几何上命中 13 项，见 [原生解析探针](native_rule_resolution.json)。
