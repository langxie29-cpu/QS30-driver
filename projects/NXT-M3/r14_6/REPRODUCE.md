# R14.6 原生复现

起点为 `c6d06aa91fb576c8d9e9445ddb89328288922457` 的 R14.5 工程。下列命令从 `projects/NXT-M3/r14_6` 运行。使用 KiCad 10.0.8 自带的 Python 与 CLI。R14.5、R14.4、R14.1 路由辅助代码、R13 Harness 保持在同仓库原路径。

```powershell
$tool = 'C:/Program Files/KiCad/10.0/bin'
$edaPython = "$tool/python.exe"
$env:NXT_R145_DEPS = Join-Path $env:TEMP 'nxt-r145-router-deps'
& $edaPython -m pip install --target $env:NXT_R145_DEPS --no-deps shapely==2.1.2 scipy==1.16.3
$independent = Join-Path $env:TEMP ('nxt-r146-replay-' + [guid]::NewGuid().ToString('N'))
& $edaPython -u build_board.py --out $independent
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }

$final = 'NXT-M3-R14.6.kicad_pcb'
$gitBoard = (Get-FileHash -Algorithm SHA256 "eda/$final").Hash
$otherBoard = (Get-FileHash -Algorithm SHA256 "$independent/eda/$final").Hash
if ($gitBoard -ne $otherBoard) { throw 'Independent rebuild did not match' }

& $edaPython -u verify_board_r146.py
& $edaPython -u qualify_clearances.py
python bom_r146.py
& $edaPython -u replay_proxies.py
```

每个布局阶段以真实保存的 KiCad PCB 运行 DRC、全走线模式和原理图一致性检查。布局阶段使用 `--refill-zones --save-board`。最终回归以交付文件直接重新打开，再分别导出标准 DRC、all-track DRC、ERC 及 XML。原生 DRC 命令退出 5 代表发现违规，报告照实归档。构建脚本会拒绝新增违规、原理图不一致或未连接净增加。审计会拒绝丢失原有焊盘铜分组。 [阶段回归](evidence/stages) · [原生复跑命令](evidence/native_commands.json) · [SHA-256 比对](evidence/reproducibility.json)

R13 密封配置的本地检视和单元测试见 [Harness 预检](evidence/harness/preflight)。实际 Worker 审查为 DeepSeek 官方 `deepseek-v4-flash` 上的 text-only 任务。复跑含模型费用，按需选择角色。每次输出使用新的目录。

```powershell
$workerRun = Join-Path $env:TEMP ('nxt-r146-harness-' + [guid]::NewGuid().ToString('N'))
python review_harness.py --stage final --role pcb --out $workerRun --accept-model-costs
```

独立实验目录中的 ngspice-46 复跑优先保留原始线路。三份带 `.control/quit` 的归档夹具由本地 DLL runner 接管运行控制，记录原始与复跑 SHA-256。节点、器件和电气参数保持原样。 [仿真日志](evidence/simulation)
