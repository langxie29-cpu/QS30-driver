# R13 复现与证据

执行目录为 `projects/NXT-M3/r13`。起点为远端 `nxt/nxt-m3-hv-cost-r12` 的 `40126f897bef6f849a68987f2daa0c1afd8a2c2d`。R13 独立分支 `nxt/nxt-m3-hv-release-r13`。从稀疏工作树复现时须检出同级 r8、r10、r11、r12 路径。

## 仿真与成本

按 `evidence/source_manifest.json` 中的 A/B/C URL 和修订检出到 `.local/A`、`.local/B` 和 `.local/C`。生成网表前核对 `sim/model_pins.json`。B 无再分发许可证明，A 和 C 的项目 MIT 许可独立于厂商模型。仿真原库保持在本机并由网表引用。原始供应商库、完整大 RAW、敏感配置和 Harness 本机完整会话不随 Git 分发。当前主机的精确原始路径记录于测量 JSON。

```powershell
python screen.py
python qualification.py --out .local/replay_matrix.csv
python assemble_bom.py
$k = 'C:/Program Files/KiCad/10.0/bin/python.exe'
& $k -u simulate.py --out .local/r13-round1 --timeout-s 100
& $k -u simulate.py --registry sim_followup.json --out .local/r13-round2 --timeout-s 60
```

固定 `ngspice-46` 来自 KiCad 10.0.8。D 复跑可将 `evidence/spice/d_replay/*/circuit.cir` 复制到新目录，用同级 R11 的 `sim/dll_run.py` 在 KiCad Python 中求解。日志、采样、原始存储路径、SHA-256、计数及时间窗在每个工况目录的 `measurement.json`。LTspice 24.0.12 的诊断用 `sim/lt_replay.py`、`sim/lt_replay_expr.py` 及 `sim/lt_b_compat.py` 在现场已有有效签名 EXE 执行，在 `evidence/spice/ltspice` 归档，不具资格。

## 原生 EDA 核对

从 R13 运行 `python ../r11/native_checks.py <绝对输出目录>`，该命令指向 R11 工程并产生 ERC/DRC/Machine JSON/XML。导出归档为 `evidence/eda_baseline`，对照 R11 原板用 KiCad 10.0.8 的 `pcb export gerbers`、`pcb export drill` 和 `sch export bom` 生成；期望仍存在工程开项。

## Harness

```powershell
python -m unittest -v test_orchestrate.py
python orchestrate.py
$node = 'D:/PROJECTS/DeepSeekHarness/runtime/node-v24.19.0-win-x64/node.exe'
$dsh = 'D:/PROJECTS/DeepSeekHarness/app/node_modules/@deepseek-ai/dsh/lib/bin.js'
python orchestrate.py --doctor --dsh $node $dsh
# 实跑需确认预算，消耗本机 DeepSeek 配置的额度
python orchestrate.py --live --accept-model-costs --external-decisions --run-id live-r13-replay --dsh $node $dsh
```

只读预检验证生效插件集合、模型、提供方及 API 路由，禁用命令、文件、web、子任务、代码执行和背景标题生成。平台凭据由 Harness 自己的配置读取。封存输入只提供登记的文件摘录。宿主写入 Worker 的 `result.json`、证据与 SHA-256，限超时与输出。受限 Worker 可以分析已登记产物，实跑求解与 KiCad 等确定性工具的产物由本地已登记脚本生成。恢复必须冻结 Git HEAD、配置、模型摘要、完整证据和身份，禁止自动重放未封存调用。原始 Worker 结果、逐项 audit 和本会话签署存于 `evidence/workers`。

实际 Worker 运行的冻结代码提交为 `ac71825fec39f5692956cd71dc26866f9bbd004c`。分支最终提交追加了完整归档。
