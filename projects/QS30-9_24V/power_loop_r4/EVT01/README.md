# NXT-PWR-EVT01 — 原生KiCad候选，禁止制造/高压上电

权威工程为 **NXT-PWR-EVT01.kicad_pro**，根图同名.kicad_sch。KiCad10.0.8原生CLI真实读取、导出XML网表和全部SVG；不是把CSV/JSON当原理图。工程共14页、212个器件/声明实例、576个物理针脚，包含明确HOLD/DNP区。

选择KiCad：本机实际安装CLI且有可读取原生封装库；嘉立创专业版既有文件不具有本轮完整导出/审查链，因此不设为R4权威。未改动旧工程。design_source.json是主控物理针脚/连接生成输入，最终可检查原生.sch才是图纸交付；pin_connections.csv与实际原生XML比较仅验证生成一致性，不能代替厂家针脚审查。

最新审查 **evidence\eda_runs\20261118T044238_8e26b4**：网表/SVG导出返回0，ERC返回5，**0错误、212个lib_symbol_issues警告**。当前CLI配置未识别项目NXT自定义符号库登记；文件和嵌入缓存确实存在，独立sym upgrade解析返回0，但库配置问题未解决，不能宣称ERC干净通过。早期3错误/893警告、后续失败配置探测均完整保留，未增加自定义ERC排除。CLI默认ignored_checks（单次全局标签、四线交点、SPICE模型、封装过滤）原样记录在erc.json，不声称覆盖所有默认未启用规则。原生网表554个预期已连接引脚全部相同；其余显式NC。

真实图形预览位于上述审查目录/svg，证据快照含当次完整原生工程。UI首次启动停在更新/隐私选择页，未替用户选择；**未观察到GUI打开本项目**。因此交付可解析的真实原生文件，GUI首次打开检查仍待用户环境完成。此限制不被CLI成功掩盖。

关键器件厂商针脚详见 ../SAFETY_CIRCUIT_IMPLEMENTATION.md；footprint_audit.json核对本机实际.kicad_mod文件及pad集合，不等于热焊盘/焊接/本体机械资格。Q101、HV连接器、按钮/温度安装件等未定型，无封装的HOLD被显式列出。

Q101不装、R111未定、四个安全许可实物下拉，图纸不具备可运行完整前级。未提供PCB布局，没有.kicad_pcb，没有DRC或制造包。PCB_PLAN.svg只是无尺寸分区，不能据此采用2mm/3mm统一绝缘间距。所有原HOLD保持。

重新生成/检查步骤见 ../REPRODUCE.md。不要跨接HOLD节点或以导出成功当上电许可。
