# 来源登记（REV.A9）

| ID | 来源 | 用途 | 证据等级 |
|---|---|---|---|
| S9-01 | TI《LM393/LM2903》SLCS005AH（本地 docs9/sources/TI_LM393_LM2903.pdf） | VICR = 0…VCC−1.5 V(25 °C)、全温区 0…VCC−2 V | VERIFIED |
| S9-02 | Microchip HV5622 DS20005854A（旧仓库 source_register S5） | 32 路、VDD 10.8–13.2 V、VPP ≤220 V、PQFP-44 引脚表 | VERIFIED（引脚表） |
| S9-03 | Findchips/Microchip 分销数据（2026-10-18 抓取） | HV5622PJ-G=PLCC-44/Tube、HV5622PG-G=PQFP-44/Tray、库存/报价 | STRONGLY SUPPORTED（分销聚合，非原厂） |
| S9-04 | 旧仓库仿真（SPICE/平均模型/行为模型 S1–S10） | 功率级/OVP/泄放参考（拓扑级） | 旧证据，未在 REV.A9 重新执行 |
| S9-05 | 用户提供 | 9 只 QS30-1 已有；HV5622 零售 32.15 元；六位管座约 15 元 | UNVERIFIED |
| S9-06 | 本仓库计算 | POWER9/COST9/MECH9/ERC9 | PROVISIONAL（计算/规则） |
