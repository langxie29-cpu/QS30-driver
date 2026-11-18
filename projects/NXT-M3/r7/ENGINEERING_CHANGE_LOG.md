# R7 工程变更

- 以 R6 冻结 SHA 建立独立 R7 原生工程。根图与各层图标题块标识 R7，根图列出 J4 DNP、保护时序、残压 ARM 与 PCB 绝缘 HOLD。生成器、原生符号、原生 footprint 和设计数据一起保留。
- R27/R28/R49/R50 指定同一 Vishay TNPW1206100KBEEA。每只 100k、0.1%、1206，节点、物理端号、阻值与仿真假设保持一致。原厂系列 200 V。正常 170 V 和故障筛选 195 V 的单只静态功耗约 71/94 mW；采用保守普通功率及 PCB 降额。分压单只短路故障仍需评审。 [原厂资料](https://www.vishay.com/docs/91000/tnpwe3.pdf)
- 高压路径保持 P1，替换偏置、控制器、栅驱、热件和 HV5622 封装仍是独立研究。没有为成本目的改缩保护或隔离距离。 [替换矩阵](COMPONENT_SUBSTITUTION_MATRIX.csv)
- 真实 KiCad 10.0.8 ERC 0 违规。保留软件默认忽略项，特别是仿真模型及 footprint filter，设计另跑针脚和座图核验。120 个元件/机械实例、418 针槽、135 个网络，117 个 footprint 仍待 PCB 几何，三管座未绑定。 [ERC](evidence/erc.json) · [EDA 审查](evidence/eda_audit.json)
- 原始 KiCad BOM、XML 与逐 ref 物料对齐，机械和 DNP 保留状态。原 R6 端点网络做回归检查。仍使用 [R6 固件](../r6/FIRMWARE_PROTOTYPE/) 和同一 RS‑485 设计。 [网表差分](evidence/native_delta.json) · [BOM](FINAL_BOM.csv) · [软件回归](evidence/firmware_check.txt)
- 仿真使用相同关键电路值和额定研究目标。各模型中的保护代理、供电及负载区别见 [原理图到仿真的映射](BASELINE_RECONSTRUCTION.md)。
