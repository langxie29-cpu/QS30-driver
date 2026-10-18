# Legacy：六位 REV.A（REV6）

本目录只放说明；旧六位设计的全部文件仍在原路径（README/design/docs/sim/netlist/bom/symbols），
对应 git 提交 `52eaa95`。

- 旧基线：6 位、2×HV5622（PQFP 映射、料号 PJ 为错误）、60 通道、单板 230×120；
- 旧证据：SPICE、平均模型、OVP 行为模型、ERC 19 项、DRC 14 项、审查包 29 页；
- 新基线（REV.A9）在 `docs9/`，两者并存，不删除旧证据。

已知旧问题（在 REV.A9 修正）：LM393 3.3 V 共模（U8）、HV5622 PJ/PG 混用、DRV_PG 10.41 V、
OVP 窗口 ±1.5 V 过严、DCM/CCM 模型混用。
