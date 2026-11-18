# 复现入口与证据边界

冻结R3=98b6f81927592f0576e7eb4148e97fe2b14eab1c；R2=bd1762f6b801a004b01de0f31ba5bbb8e2a60a3d；R1=96a1afef5e55f84d002f754510b97d8cbd49334f。R4独立worktree/branch。evidence/preflight/baseline.json记录最初HEAD与2594个历史文件验证。禁止重新运行preflight.py覆盖原收据；收尾用final_verify.py。

## 读取与独立验算（不消耗LT/Flash调用）

Python解释器使用现有numpy环境：D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe。脚本r4lib.py明确标出本地历史路径，不声称任意机器零配置。需要先checkout冻结的R1/R2/R3或修改路径映射，再用SHA确认来源。

evidence/measurement_index.json与measurements/*.json是原始波形确定性提取。时间加权stats()包含窗口端点插值，峰峰值读取全部原采样点，不平滑/不挑低波动子窗。cap-only固定100–120ms，只有一个末段窗口；未声称完整新电路足够长稳态已资格。独立静态阈值/能量计算在calculations.py；先阅读calculation_corrections.json，不能覆盖旧计算证据。补充模型端口KCL/步长比较见supplemental_analysis.py及其输出（若存在）。

## 原生工程

在本目录执行：

```powershell
& 'D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe' design_data.py
& 'D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe' build_eda.py
& 'D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe' audit_eda.py
```

audit_eda每次新建时间戳目录，先快照再调用真实KiCad10.0.8 netlist、erc、svg，保留stdout/stderr与原生ERC JSON。CLI exe路径见r4lib。ERC返回5是存在违规，不能被视作0。当前NXT库配置警告未解决，配置探测失败保留；不修改用户全局库或自动豁免。GUI首次运行的更新/隐私页未代选，项目GUI加载未观察；原生CLI加载已证实。没有PCB/DRC。

## 六次原生LTspice

solver准确版本24.0.12.0 Windows Normal，exeSHA见preflight。每次实验都有执行前preregister.json：假设/唯一变量、完整网表/模型SHA、.tran、最大运行秒数、Gear与原容差、分析窗、预定义指标和输出路径；执行后日志/raw/SHA均保留。所有COMPLETED_UNREVIEWED只是进程状态；电气分类以measurements和QUALIFICATION_MATRIX为准。

experiments.py是已执行的六项定义，不是请求再执行。runner.py总台账最多12次，本轮已6次；继续调用需要有新的获批且可判别问题，不能因为剩余配额就自动运行。不要重新运行以覆盖既有目录。厂商模型不修改，未上传；从source_register*.json/ST_model_acquisition*.json的原厂URL取得并逐个SHA核对。授权模型使用条件仍由使用者遵守。LT .lib/.sub/EXE/PDF不在Git或release。

## 原始波形归档与恢复

所有R4 raw本地仍在；21个90MiB以内分卷存于GitHub私有草稿release qs30-power-loop-r4-evidence-20261118，未发布。清单evidence/raw_archive_manifest.json、github_artifacts.json包含原SHA、分卷SHA、远端digest和API地址。使用已授权git credential，不打印凭据：

```powershell
python download_evidence.py --list
python download_evidence.py --case sic_1ns --download-root NEW_DOWNLOAD_DIR --restore-root NEW_RESTORE_DIR
```

目的地必须新建，既有raw不覆盖。download_evidence解码R2原封不动QS30RAW1，少量mixed raw采用原字节gzip。只下载、校验、重建，不产生SPICE/API模型调用。final_verify.py核对历史2594文件、六个封存目录、七个已有解析/codec测试、21远端digest、一个远端下载恢复抽查；全部raw本地压缩重建也逐一验证。

保护：R1/R2原机制继承，R3与R4实验目录的Windows ACL禁止本账户写/删；Flash仅远端文本API，无工具/文件系统权限；执行器为主控。ACL不能抵抗管理员改ACL，不是独立安全账户沙箱。models/PDF在忽略的.local；raw无覆盖无删除。本轮新增缺失0；历史R2两份raw永久缺失照实登记，不伪造。

## Flash

两轮A/B/C与D/E/F，共六会话，0子Codex。prompts、drafts完整保存输入/响应/usage/终止原因；E达到4500输出token截断，审查不完整。不要自动重跑flash.py；会话数不等同token或人民币硬上限，账单UNKNOWN。主控所有采纳/否决见codex_*决策文件；任何草稿都不能解除HOLD。
