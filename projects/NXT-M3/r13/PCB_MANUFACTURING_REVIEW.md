# R13 原生 PCB 与制造审查

2026-11-22 在 KiCad 10.0.8 复跑冻结 R11 工程，原理图、板及规则沿用 R12 基线。

| 检查 | 冻结 R11 原生结果 |
| --- | --- |
| ERC | 退出 0，0 error / 0 warning，原项目有 4 类 ignored checks。 |
| DRC | 退出 5，263 条净距违规，345 个开项，涉及 166 个网络。 |
| 端点与一致性 | 原生网表 244 个网络，206 个多端点网络。40 个多端点网络未报开项。parity 0 项。 |
| 文件预检 | Gerber、Excellon、BOM 各退出 0。共导出 7 层 Gerber、作业文件及 PTH/NPTH 钻孔。 |
| 管座 | 6×Ø3.5 mm 为现有候选孔。33 条交接有 2 条导通，30 条阴极和 ANODE_1 仍开。 |

[原生报告及导出](evidence/eda_baseline/) · [独立端点核对](evidence/eda_baseline/native_audit.json) · [Worker 板级复核](evidence/workers/round_01/native_baseline_review/inventory.md)

候选 KiCad 设计尚未达到建板门槛。导出的 R11 预览用于核查工艺文件和暴露开项。新板需按实际电位差清算功能绝缘和触及隔离。确认工作电压、重复开关尖峰、故障等级、场地海拔、污染等级、板厂层叠材料 CTI 以及邻近金属螺钉与管座。对高于 30 kHz 的周期应力检查适用高频条款，同时先确定产品标准。原规则由 R11 保留，需在新的设计中由绝缘矩阵逐项重新论证。 [IEC 60664-1](https://webstore.iec.ch/en/publication/107319) · [IEC 60664-4](https://webstore.iec.ch/en/publication/2804)

G3 前需确认原生符号到物理引脚、器件封装和可制造焊盘、关键功率与采样回路、连续低压回流和天线净空、管座键位及孔距、板边和安装件。PCB 实物验证、报价和安全审查后再提交 EVT 审批。
