# R3 复现、原始数据恢复与范围

基线`bd1762f6b801a004b01de0f31ba5bbb8e2a60a3d`；仅新增`projects/QS30-9_24V/power_loop_r3/`。全部16次原生预算已用完，禁止为复核自动调用Flash或重跑仿真。无需付费模型即可恢复raw并复核指标。

本机Python：`D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe`，含numpy/matplotlib/pymupdf。本机LT为24.0.12.0，exe位置虽含ltspice26，不能称26版。`r3lib.py`登记当前本机路径；移机只更新路径配置，不改原始证据。R1/R2脚本及原模型按指定SHA原样保留。

## 1. 恢复原始字节

大raw保留在每例独有运行目录，本地OS ACL禁止普通写/删；Git保存网表、预登记、日志、命令、SHA清单及独立指标。原始字节封存在GitHub**草稿发布附件**，需要仓库访问权；这不是发布产品或制造授权。源模型/凭据不上传。

`evidence/raw_archive_manifest.json`给出每份raw的原长度/SHA、分片顺序、每片SHA和恢复验证；`github_artifacts.json`给出对应远端资产及服务端SHA。一般raw使用原R2测试过的QS30RAW1无损位变换/gzip；小型无实例烟雾probe的mixed raw使用`gzip-original-bytes`。两种恢复都验证每个原字节，不重采样、舍入或修补尾部。

```powershell
<PY> projects/QS30-9_24V/power_loop_r3/download_evidence.py --list
<PY> projects/QS30-9_24V/power_loop_r3/download_evidence.py --case front24_fast --download-root D:/QS30_R3_DOWNLOAD --restore-root D:/QS30_R3_RESTORED
```

省略`--case`恢复全部15份现存raw。恢复目标必须全新；已存在则拒绝覆盖。脚本从现有Git凭据管理器取授权，不打印凭据；跳转到附件存储时移除授权头。MODE加密解析失败例没有raw，原日志/rc1必须一起保留。R2两份被删除raw永久缺失，R3不伪造恢复。

## 2. 独立计算

`analyze.py`和`consolidate.py`使用R2严格原生raw解码器：UTF16/UTF8、double/mixed、单调时间、有限值及物理长度检查。输出均值用时间积分，Vpp/峰值用完整保存样本与边界插值。不是自适应样本的算术平均，也不是带宽滤波结果。

正常名义100–120ms、其他三个正常输入/斜率60–80ms为整段评价；名义原预登记遗漏显式窗口，执行期间在未查看输出指标时作盲补充声明，见`measurement_declaration.json`（未冒称其属于原始预登记）。40–60ms尾振数据同时公开。故障/失电不使用正常稳压门槛判通过。

所有启动COUT=0，真正系统启动使用原生LT3757A闭环和SS。局部器件单元为明确89.17V/1.4A初态与20ns外部门沿；仅研究换流，不能当0V启动或固定PWM系统候选。原生UIC首样本有电流不一致，完整极值和非零时间/事件窗口并列保存。内部电流未直接导出时明确标为由节点/原电阻推断；异常内在电流和KCL超筛查值使本征损耗/SOA保持INCONCLUSIVE。

```powershell
<PY> projects/QS30-9_24V/power_loop_r3/bounds.py
<PY> -m unittest discover -s projects/QS30-9_24V/power_loop_r2 -p test_*.py -v
<PY> projects/QS30-9_24V/power_loop_r3/checks.py --historical
```

本机完整结果复核用`consolidate.py`、`internal_analysis.py`、`operating_point.py`；恢复到不同路径时将各脚本的实验根映射至恢复目录，并把小网表/预登记/命令同目录复制。生成的新指标写新复核目录，不能覆盖封存原始文件。原指标缓存保留审查版本，最终以`metrics_final/`和`QUALIFICATION_MATRIX.json`为准。

## 3. 如另获预算需要重跑

每例`preregister.json`保存完整netlist/model/exe SHA、准确.tran/.options、预计时间与停止条件。先在**全新目录**复制网表和合法取得且SHA匹配的4个库，再执行原生`LTspice.exe -b circuit.cir`。`.options threads=1 method=gear reltol=.001 abstol=1n vntol=1u plotwinsize=0 numdgt=15`保持。没有修改TT/BV或厂家模型。原生日志中的线程数/终点需复核，rc0不是电气合格。

`runner.py`是本轮主控确定性执行器，16次已封账，主动拒绝第17次；不要删账重置预算。新授权轮次使用新的账本/运行根，不改R3。执行器先pending目录预登记和计数，执行后保存失败/部分输出、完整SHA，再改为唯一封存名并施加ACL。初期ACL执行错误与修正记录公开，不据rc0假称已成功隔离。

## 4. 数据保全与模型边界

Flash通过不带tools的HTTPS文本完成调用，根本没有本地文件/shell/仿真能力；主控只把答复存入授权drafts，不执行其代码。受保护根的实际SDDL与拒写/拒删探测在evidence中。此措施不是独立用户SID的通用沙箱，也不能抵御管理员修改ACL；不能声称获得了不可更改的离线存储。

TPS26601真实最大保护延迟/脉冲热、热磁件、真实独立OVP和九管动态仍缺；参数前级结果只支持限定研究。所有24V-07/08/09/10、H01–H10和制造HOLD保留。
