# 迁移结果

**LIMITED / INCONCLUSIVE**。已实跑源侧单页与全工程导出，目标侧有效转换 0 次。专业版项目打开、编辑、目标网表、ERC、BOM 和归档待验证。

|核验|实测结果|
|---|---|
|原始工作区|原工作树在 b12cd112 且有未提交修改。R4 工作树干净，R4 本地和实际远端均指向指定提交。R5 使用独立工作树。|
|冻结完整性|23 个当前文件写入 [源 SHA256](evidence/R4_SOURCE.sha256)，24 个历史文件通过 [历史清单](evidence/R4_HISTORICAL_SNAPSHOT.sha256) 复核。SAFETY_3 仅在历史快照，当前根图无对应引用。历史版 latest_review.json 与当前更新的指针各自记录。|
|源侧代表单页|POWER_1 真实导出 1 页、20 实例、54 针，全部网络与全工程对应页一致。|
|源侧全工程|KiCad 10.0.8 导出 14 页、212 实例、576 针，含 554 连接和 22 NC，25 种 NXT 库符号和 196 条封装记录。28 个不同的本地封装文件逐一验证哈希。旧 XML、新 XML 与 R4 针表交叉匹配。|
|源 ERC|0 错误，212 个 lib_symbol_issues 警告。库表配置为 UNINITIALIZED，使用内嵌符号导出。|
|转换器 1.10.1|从官方 CDN 下载。Windows 应用控制政策拦截执行，无转换输出。|
|专业版 4.1.97.04b092ac.331da4|真实 GUI 显示 Regist / 激活客户端。官方激活入口要求登录。CLI doctor 联系到桥接，session list 仅有注册窗口，正常 open 返回 BRIDGE_NOT_READY。|
|内置导入|无法进入工作区。KiCad 10 实际导入兼容性待测。|
|等价|576 行目标针全部 UNOBSERVED_TARGET。符号、封装、引脚、网络和装配差异未判定。|
|设计权威|R4 KiCad 保持冻结权威。无目标工程、无 PCB、无 PCB DRC，制造 HOLD。|

源侧专项复核确认 U100 RTN15/EP25 接 RTN100，GND17 接 PGND。RHOLD1–4 针 2 全接 GND_CTRL，针 1 各自接四个安全许可。Q101 唯一显式 DNP，R111 未定型。目标侧还须核对 EP 焊盘、NC、三处地网桥、OVP、锁存、双泄放及其参考网。

[引脚差异账本](MIGRATION_PIN_NET_DIFF.csv) · [库账本](MIGRATION_LIBRARY_AUDIT.csv) · [源审计](evidence/source_audit.json) · [EDA 事件](evidence/eda_events.txt)
