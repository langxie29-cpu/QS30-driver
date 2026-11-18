# 嘉立创 EDA 专业版迁移与验收

冻结输入为 R4 提交 ff6af65b557905308f7c3fcb318848eaca1a1d0b 的 [KiCad 工程](../power_loop_r4/EVT01/NXT-PWR-EVT01.kicad_pro)。

1. 在允许执行的 Windows 环境运行官方格式转换助手 1.10.1。用 [POWER_1 单页包](evidence/R4_POWER_1_INPUT.zip) 验证 LT3757A、UCC27511、Q20、D20、L20 和采样链，记录所有未识别条目。官方格式表列出现代后缀，内置导入指南列明 5.1/5.9，R4 文件头版本 20250114 须实测。
2. 在专业版打开单页输出，编辑后撤销、保存、重开和导出网表。核对 20 实例、54 针的编号、名称、网络及属性，重点是 LT3757A EP、UCC27511 分离输出和功率器件焊盘映射。
3. 单页通过后转换 [完整包](evidence/R4_FULL_INPUT.zip)。导出 14 页原生网表、BOM、ERC 和封装资料。按 212 实例、576 针、554 个预期连接核对，逐项验证跨页标签、层级端口、PWR_FLAG、多单元、隐藏针、NC、DNP 与热焊盘。
4. 比较每个网络的针集，追查遗漏、新增、合并或拆分。保持 RTN100 和三处地网桥两侧的参考网，核对 RHOLD1–4 下拉、START/RESET、OVP、锁存、V12/V5/INTVCC、Kelvin、双泄放与残压。
5. 通过图纸开、改、存、再导出验证后，归档目标原生工程及哈希。独立审查通过才能记 MIGRATION_EQUIVALENCE_PASS 并切换唯一权威源。若实测转换失败，可原生重建并复用同一验收，保持 HOLD 默认状态和全部参考地语义。

[转换助手](https://prodocs.lceda.cn/cn/import-export/easyeda-pro-format-converter/) · [KiCad 导入](https://prodocs.easyeda.com/cn/import-export/import-kicad/) · [专业版 CLI](https://prodocs.lceda.cn/cn/api/guide/cli.html) · [BOM 导出](https://prodocs.lceda.cn/cn/schematic/export-bill-of-materials-bom/) · [BOM 价格](https://prodocs.easyeda.com/cn/schematic/bom-preview-and-price/)
