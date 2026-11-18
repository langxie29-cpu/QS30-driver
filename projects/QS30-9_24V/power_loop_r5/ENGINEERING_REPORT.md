# Σ · QS30-9 POWER LOOP R5

2026-11-18 · EVT01 · 制造与实物高压 **HOLD**

R5 完成了冻结源复核、商城证据采集、试制预算和前级保护窗口重算。**嘉立创原生迁移未验收，完整试制成本仍未知。** 官方格式转换助手被 Windows 应用控制阻止，已装专业版 4.1.97 停在账号激活。复现入口与完整的源侧审查材料已归档。

|维度|结论|
|---|---|
|EDA 迁移|LIMITED / INCONCLUSIVE。源侧已核验 14 页、212 实例、576 针（554 连接、22 NC）。目标侧未核验任何针。|
|电气资格|INCONCLUSIVE / HOLD。当前 1.6492 A 启动政策下，LM5069 直接替代的 Rs 下界 42.359 mΩ，高于上界 29.117 mΩ。否决直接替代，现有链继续 HOLD。|
|器件可采购性|16/43 个准确候选 MPN 有 SKU 证据，覆盖 35/188 个实际物料位号。其中 5/43 来自大陆商城，其余 11 个提供目录身份。|
|BOM 价格|大陆商城 5 个准确 MPN、11/188 位号有公开价阶。SMT 含税目录另核对 3 个准确扩展库 SKU。结算价覆盖 0。|
|PCB/SMT 报价|裸板和 SMT 有引用费率的可重复预算。正式计价均未获得。|
|原始证据|23 个当前文件、24 个历史快照哈希已复核。Git 基线保留 R1–R4 历史工程及证据。|
|制造放行|正式 PCB 布局与制造 HOLD。H01–H10、24V-07/08/09/10 和四个安全许可继续维持原状态。|

## 交付入口

- [冻结 KiCad 工程](../power_loop_r4/EVT01/NXT-PWR-EVT01.kicad_pro) · [单页与全工程迁移结果](EDA_MIGRATION_RESULTS.md) · [专业版入口状态](EASYEDA_PROJECT/README.md)
- [逐针差异账本](MIGRATION_PIN_NET_DIFF.csv) · [迁移库审查](MIGRATION_LIBRARY_AUDIT.csv)
- [物料总表](LCSC_BOM_MASTER.csv) · [价格证据](LCSC_PRICE_EVIDENCE.csv) · [替代审查](BOM_SUBSTITUTION_REVIEW.csv)
- [PCB](PCB_COST_SCENARIOS.md) · [SMT](SMT_COST_SCENARIOS.md) · [自行装配与完整 EVT01 预算](EVT01_TOTAL_COST.md)
- [前级架构](FRONTEND_ARCHITECTURE_R5.md) · [资格矩阵](QUALIFICATION_MATRIX.json) · [制造阻塞](MANUFACTURING_BLOCKERS.md) · [下一轮决定](NEXT_ENGINEERING_DECISIONS.md)

## 最终审查答复

1. 桌面工具运行到了激活界面，正常 CLI open 返回 BRIDGE_NOT_READY。官方转换器未进入可运行状态。KiCad 10 转换兼容性待实际运行。
2. 14 页、576 针经过源侧复核。专业版逐针等价验证仍待做。
3. 专业版符号、封装、装配、针脚与网络差异未判定。当前 CSV 明示目标未观测。
4. 专业版原生图纸未观察到打开或编辑。有效 .epro/.epro2 归档尚无。
5. 国内准确 SKU 包括 B32774D4106K000 C3799662、STP9NK50Z C38617、LM5069MM-1/NOPB C486026、CRCW251249K9FKEG C242561、MSS1583-154KED C7427458。其余 11 项的来源见物料表。STPSC4H065D、SN74HCS14DR、RS20 的准确国内 SKU 未核实。
6. TDK 和 Coilcraft 有足够的显示现货及数量档，5/10 片合计 ¥234.80/430.40。MOS 两只，LM5069 为 MOQ 1000 的订货品，泄放电阻无商城可用库存。结算与有效税运仍待验证。
7. PCB 面积模型约 ¥24.60–55.20。SMT 公开费率子项为 5 片 ¥65–75、10 片 ¥80–100。自装含裸板及工时假设的部分总计 5 片 ¥1,064.60–2,127.60、10 片 ¥2,119.20–4,215.20。
8. 完整成本为 TOTAL_COST_UNKNOWN。缺料件、绝缘机械、税运、贴片分项和真实裸板报价。
9. 没有候选通过电气等价和成本两项批准。
10. 当前前级冲突尚无实物解决，R5 重算出了启动与热态的必要条件，也明确了独立检测和支路开断的研究方向。
11. Q101 有准确研究候选 IPB017N10N5LFATMA1，实际器件仍 DNP。需要实际加载切断、热态 SOA 和库存证明。
12. 保护、封装与绝缘仍未收敛，正式布局 HOLD，无 PCB DRC。
13. 阻塞包括迁移、加载保护时序、热态磁件、故障储能、恢复联锁、绝缘/外罩/连接器以及供货。关闭证据见制造阻塞表。
14. 原始制造和实物高压 HOLD 全部保留。

[独立复核与资源](evidence/review_and_resources.md) · [复现](REPRODUCE.md)
