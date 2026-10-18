# REV.A9 网表级 ERC（机器生成）

由 `design9/build9.py` 生成：**36/36 通过**。

> 这不是立创EDA/KiCad 原生 ERC；原生 ERC/DRC 仍未执行（见 docs9/EDA_STATUS.md）。

| 编号 | 结果 | 内容 |
|---|---|---|
| E01 | PASS | 所有网络 ≥2 端点（未连接引脚以 NC 记录） |
| E02 | PASS | 阴极网络 90 个（应为 90） |
| E03 | PASS | 阳极网络 9 个（应为 9） |
| E04 | PASS | 阴极网络均为 (HV5622 输出, 管座) 两端点 |
| E05 | PASS | 阳极网络均为 (限流电阻, 管座) 两端点 |
| E06 | PASS | 9 个管座 |
| E07 | PASS | 3 颗 HV5622 |
| E08 | PASS | HV5622 料号统一为 PG-G（PQFP-44，P0-03） |
| E09 | PASS | 低压器件/连接器上无 HV 网络 |
| E10 | PASS | 模块 HV 连接器只承载 HV_BUS/GND_HV |
| E11 | PASS | L 模块 DATA OUT 回到主板（回线） |
| E12 | PASS | 中心模块 DATA IN 接 L 模块回线 |
| E13 | PASS | R 模块 DATA IN 经连接器 |
| E14 | PASS | CLK 并行分配到 3 模块（含主板） |
| E15 | PASS | BL/ALLOW 并行分配 |
| E16 | PASS | 安全回路起点/终点存在 |
| E17 | PASS | 安全回路在 3 个模块内直通 |
| E18 | PASS | 安全回路终点有下拉 |
| E19 | PASS | 比较器基准 1.0 V ≤ VCC−2 V=1.3 V（LM393 全温区共模） |
| E20 | PASS | 基准同时满足 25 °C 共模上限 1.8 V |
| E21 | PASS | DRV_PG 门槛 11.20 V ≥ HV5622 VDD 下限 10.8 V |
| E22 | PASS | DRV_PG 迟滞 0.45 V（R22=1M） |
| E23 | PASS | OVP 验收窗口 (192.5, 204.5) V 覆盖 1% 电阻+0.5% 基准 worst-case（解析 192.9–204.1 V） |
| E24 | PASS | OVP 关键节点均有 ≥2 连接 |
| E25 | PASS | OVP 比较器三个关键点均连接 |
| E26 | PASS | DRV_PG/FAULT_OK 比较器输入输出均连接（无悬空） |
| E27 | PASS | EXT12_PG/P3V3_PG 比较器连接完整 |
| E28 | PASS | DRV_VDD_EN = (EXT12_PG·P3V3_PG)·HV_EN_REQ |
| E29 | PASS | HV_EN 由 HV_EN_B·HV_EN_REQ 合成 |
| E30 | PASS | HV_EN 经 Q5 驱动 P-FET 高侧开关关断 HV 输入 |
| E31 | PASS | 帧长 96 bit = 3×32（90 用 + 6 备） |
| E32 | PASS | 3 个驱动器件 U_L/U_C/U_R |
| E33 | PASS | 左右模块 LV 接口公共引脚（1–9/12–16）定义一致 |
| E34 | PASS | 左右模块接口差异仅数据网络（DIN/DOUT） |
| E35 | PASS | 主板 HV_BUS 泄放电阻 |
| E36 | PASS | 每模块本地 HV 泄放 |
