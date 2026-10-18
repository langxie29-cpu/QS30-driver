# HOLD 登记（REV.A9 九位模块化基线）

由 REV.A9 重构引入的未冻结项。旧六位 HOLD Register 保留在 `HOLD_REGISTER.md`（Legacy）。

| ID | 项目 | 关闭条件 | 证据文件 | 状态 |
|---|---|---|---|---|
| H9-01 | 架构冻结（三板 vs 四板、BOM-B） | 用户评审 G0 | docs9/GATES.md | OPEN |
| H9-02 | HV5622 真实价格/库存/真伪 | 询价 + 收货验真 | bom9/BOM9_B.csv | OPEN |
| H9-03 | 13 脚管座机械尺寸 | 实测 10 项（H03 模板） | docs/evidence/H03_*.csv | OPEN |
| H9-04 | OVP 极性器件级验证 | BJT 级 SPICE + 台架 | docs9/POWER9.md（待补） | OPEN |
| H9-05 | 90 路位序 | walking-one 实测回填 | docs9/channel_map9.csv | OPEN |
| H9-06 | 原生 EDA 工程 + ERC/DRC | KiCad/立创EDA 工程 | docs9/EDA_STATUS.md | OPEN |
| H9-07 | HV 连接器额定/防触碰 | 选型手册 + 结构 | docs9/interface9.csv | OPEN |
| H9-08 | PCB 尺寸/机械冻结 | H9-03 后 | docs9/MECH9.md | OPEN |
| H9-09 | 高压台架（G3） | 实测 172 V/OVP/泄放/浪涌 | H06 证据 CSV | OPEN |
| H9-10 | 模块断连安全回路 | 故障注入实测 | docs9/ARCHITECTURE.md | OPEN |
| H9-11 | 轻载 DCM 稳定性 | G3 台架三点测试 | docs9/POWER9.md | OPEN |
| H9-12 | 成本/PCB 报价 | 询价单 | docs9/COST9.md | OPEN |
