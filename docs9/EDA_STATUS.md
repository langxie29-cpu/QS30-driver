# EDA 工程状态（如实记录）

| 项 | 状态 | 说明 |
|---|---|---|
| 可编辑原生工程（KiCad/立创EDA） | **未实现** | 本环境无 KiCad/立创EDA；winget 安装需管理员；不伪造工程 |
| 符号库 | 已生成本项目符号（`kicad/QS30_symbols.kicad_sym`） | 引脚来自已验证表；未经 KiCad 打开验证 → PROVISIONAL |
| 封装 | **未生成**（管座 TBD；QVFP/PQFP 尺寸未核实） | 绝不用相似封装替代（H03） |
| 网表 | 已生成逐引脚 CSV（`netlist9/`） | 可导入自建工具；未与原生 EDA 网表对比 |
| 原生 ERC/DRC | **未执行** | 不具备条件；不标 PASS |
| Gerber | **未生成** | 禁止 |

后续：拿到 KiCad（或立创EDA）后，按本目录 netlist9 + 接口 + 90 路映射重建工程，
跑原生 ERC/DRC，并与本 CSV 网表逐引脚对比；在此之前一切"设计完成"均指软件侧数据。
