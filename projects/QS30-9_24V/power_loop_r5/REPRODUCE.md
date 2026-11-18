# 复现与证据路径

R5 工作树基于 ff6af65b557905308f7c3fcb318848eaca1a1d0b。以下命令从本目录运行，使用系统 Python 标准库及 KiCad 10.0.8。

~~~powershell
python freeze_source.py
python frontend_analysis.py
python procurement.py
~~~

第一条命令复制 R4 工程到暂存目录，先核对当前和历史 SHA256，再导出单页与整工程的 KiCad 网表和 ERC。日期、临时路径和日志可能随复跑变化。采购默认复用 [公开 HTTP 快照](evidence/lcsc_public_snapshot.json) 和 [Edge 实测价阶](evidence/vendor_live_catalog.json)。更新报价先归档旧证据，重新读取公开页面的价阶、MOQ、可用现货和供应方式，然后更新实测价阶文件并执行 `python procurement.py --refresh`。原 HTTP 正文 SHA256 用于识别采集版本，页面全文未存入仓库。

官方安装包由 [嘉立创下载中心](https://lceda.cn/page/download) 提供，捕获的 SHA256 在 [EDA 日志](evidence/eda_events.txt)。专业版迁移遵循 [验收流程](EDA_MIGRATION_PLAN.md)，不从源侧 CSV 构造目标网表。示例包新增的两个 ZIP 均是字节保真的冻结输入，属于 KiCad 转换材料。R4 原始波形、模型和运行日志仍通过其原目录与历史提交访问。

两轮 DeepSeek 复核分别执行一次，输入是公开参数和抽象情景，凭证从既有本机配置读入进程。提交的 JSON 含预算、用量和文本，复跑脚本拒绝覆盖已有回执。详见 [核验记录](evidence/review_and_resources.md)。

目标网表可用后，独立提取列 reference、unit、physical_pin、pin_name、net、mpn、footprint、population，保留 NC 空网络与实际 DNP。版本间命名转换须保留原值和显式映射，并单独检查一对一网络映射及焊盘等价。运行 `python compare_target.py target_normalized.csv target_diff.json` 检查所有字段、漏针与多针。NORMALIZED_FIELDS_MATCH 仍需图纸、封装和实际打开审查。
