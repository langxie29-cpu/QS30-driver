# 复现与证据恢复

本轮模型预算已结束：两轮、六个DeepSeek Flash session、子Codex0。**复核证据不需要再次调用任何付费模型。** 当前候选ELECTRICAL_FAIL，不改变HOLD。

## 只读复核

1. `python -m unittest discover -s projects/QS30-9_24V/power_loop_r1 -p test_*.py -v`：22个离线工具/协议/算法检查，绝非22项电气PASS。
2. `python projects/QS30-9_24V/power_loop_r1/verify_archive.py`：按worker封存manifest核对每个小文件及原始波形分片的精确重构SHA256。
   本机另可运行`verify_historical_inputs.py`，对原QS30-1工作区的3034份既有输入（约9.84GB、124份raw）与首轮登记SHA做只读核对；远端没有这些旧未提交raw时，不能冒充可在空环境完成该项。
3. 每份`.archive.json`及总`evidence/worker_run_20261117T051440Z/archive_manifest.json`都提供原文件路径、长度、SHA和gzip分片顺序。将`archive.parts`按顺序拼接后gzip解压，原字节SHA必须等于`sha256`。不归一换行、不插值改写原raw。原始未压缩文件仍保留在本机原路径。
4. 需要提取的完整启动记录位于manifest中 `evidence/candidate_diagnostic/nominal_24V_gear_resource600/circuit.raw`；恢复到该目录后用数值环境运行`full_candidate_review.py nominal_24V_gear_resource600`、`settled_window_review.py`和`cycle_review_deglitched.py`。派生分析会写新结果，应先备份已有派生JSON；原raw不变。

数值环境：本机`D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe`含numpy和matplotlib；一般Python3.11.15负责调度/stdlib。代码不安装新环境，不读API凭据来测量波形。

## 模型与原生工具

本机LTspice绝对路径、签名、版本、exe SHA见`evidence/preflight`；实际24.0.12.0，不是目录名声称的26版。NGspice47路径和SHA同处。原库/安装包/程序不在本轮Git证据中重分发；用登记的原厂来源或本机已有安装取得，并先匹配SHA。

- ADI原包：`lib.zip`中的`lib/sub/LT3757A.sub`，SHA `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634`。原参考图从`examples.zip`的`examples/Applications/LT3757A.asc`提取。Python zipfile提取必须字节相同。
- ST/US1G/SS14原模型：本机既有`QS30-1/projects/QS30-9_24V/sim/s06c_current_cell_v3/ST_AUX12_1ns/{st.lib,diode.lib,ss14.lib,controller.sub}`。原厂来源/哈希和适用范围见MODEL_MATRIX及每例preregister。把这些原件复制到恢复/重建的案例目录；不自行改模型语法、TT或温度范围。
- `candidate_diagnostic.py`中OLD/LT默认本机路径，另一个环境须明确更正路径并保存执行元数据，不将缺程序报成器件失败。

## 非付费的实际仿真重跑

已存在的案例目录不能覆盖：各脚本使用`exist_ok=False`。复制脚本并给新实验目录/预登记，或按现有命令在新目录中运行保存的网表。真实高压硬件不在这些命令范围。

启动模型：`LTspice.exe -b <case>/circuit.cir`，二进制无压缩，`numdgt=15 plotwinsize=0`。完整原案例是Gear、200ns maxstep、60ms终点、600s执行上限，实际完成286.657s；两个旧120s超时例保留。不要凭超时把不完整raw当完整成功；原始部分raw的头部点数与末尾未刷新的字节可不同，`partial_candidate_review.py`明确披露未审阅尾部字节。

参考图：`LTspice.exe -netlist <original.asc> -I<extracted lib/sym>`，然后`-b -ascii <generated.net> -I<extracted lib/sub>`，`-I`最后、与路径无空格。本机原生-netlist产生四个ACP936 `A6 CC`微单位后缀；修正只在另存派生网表中四处改ASCII `u`，不改原图/原模型。`native_reference_encoding_fix.py`保存前后SHA和数量断言。stock ASC直接-b的60s超时及错误单位88µV波形均保留，不能伪称原厂参考无修改字节回放通过。

被动路径复现：读取`evidence/passive_path/fast_1us`、`slow_1ms`及各`_25ns`的原网表；控制器禁止开关，COUT=0。50ns/25ns、1µs/1ms输入沿形成2×2矩阵。它不是170V启动资格。

## 未来再次运行Harness（本次不执行）

`local_live.py`用独立忽略目录处理迁移前启动器路径、模块fallback和deepseek-flash选择；原全局设置保持。当前模型请求header记录为deepseek-official/deepseek-flash，当前Codex本地会话为openai/gpt-6.1-sol。

如另获新的实验预算，必须新run目录并记录范围。首次两轮的目录已经HOLD：`--resume`不会添加第三轮。Codex内调用`--external-decisions`为必需；worker session数不等于API请求数/Token费用，不能将max_worker_calls误作货币上限。当前主控不再为本轮启动任何模型任务。
