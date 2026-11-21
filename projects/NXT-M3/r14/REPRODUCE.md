# 复现 R14 与 R14.1

## R14.1 当前候选

直接打开 [NXT-M3-R14.kicad_pro](eda/NXT-M3-R14.kicad_pro)。在本目录运行以下命令复查已提交的 PCB、原理图、铜连通与低压代理。KiCad CLI 对仍有净距违规的候选返回 5。

```powershell
$p = 'C:/Program Files/KiCad/10.0/bin/python.exe'
& $p -u verify_r14_1.py r14_1_verify.tmp/baseline.kicad_pcb
& $p -u stop_r14_1.py
```

原生规则使用与基线相同的约束设置。[R14.1 工程结论](R14_1_COMPLETION.md) 中的端点审计基于实际 KiCad 连通图，不以同网名代替同一铜连接。布线复作工具 `close_r14_1.py` 从冻结 R14 的 EDA 归档载入，使用 `landslatch4`、`finish`、`blank`、`returns`、`prune`、`cutoff` 的顺序在独立临时目录实施。其外层 / 内层几何筛查和候选回滚以后续 KiCad 原生验证为准。候选板保存的对象 UUID 是本次证据的主键。 [布线证据](evidence/r14_1/routing/)

## R14 历史交付复作

以下历史生成指令应在原提交 `d203259673981fc9dc7dcc8ede4780305f21c041` 的独立工作树运行。

在本目录用 KiCad 10.0.8 打开 [NXT-M3-R14.kicad_pro](eda/NXT-M3-R14.kicad_pro)。原理图、局部符号/封装库、项目参数和 PCB 均在 eda。符号的标准封装名称依赖 KiCad 10 自带库。工程生成脚本使用同仓库 R10/R11 的工具，查看 EDA 文件无需执行脚本。

```powershell
$bin = 'C:/Program Files/KiCad/10.0/bin'
$k = "$bin/kicad-cli.exe"
$p = "$bin/python.exe"
& $k sch export netlist --format kicadxml -o evidence/baseline/netlist.xml ../r11/eda/NXT-M3-R11.kicad_sch
python integrate_schematic.py
& $k sch export netlist --format kicadxml -o evidence/pcb/netlist.xml eda/NXT-M3-R14.kicad_sch
& $p -u integrate_pcb.py
& $p -u native_evidence.py
& $p -u simulate_faults.py
```

`integrate_pcb.py` 从冻结 R11 加载 PCB 并筛选放置，随后用 KiCad 复查、回滚触发违规的候选布线。KiCad 自动分配新的 PCB 对象 UUID 和原始报告时间。逐次复算应比较网络、几何、违规与开路统计。原生 CLI 的 5 表示仍有违规。普通 DRC 与原生 parity 一起运行，已保存 R11 同参数复跑以及候选重铺铜时的检查。生成候选过程中回滚的轨迹与未找到路径的端点在 [布线记录](evidence/pcb/routing.json)。

仿真复用 R11 ngspice DLL 驱动，每个工况目录包含实际网表、原始二进制波形及求解日志。所有电压、电流、能量和时间均为模型数值，保护仿真采用理想锁存/切断及离散故障刺激。R11/R13 历史结果可从相邻目录独立追溯。

DeepSeek 沿用 R13 `orchestrate.py --doctor` 的封存文本只读预检。配置允许六轮、十八个 Worker 槽。本轮 0 次付费 Worker 调用，实时账户额度未验证。主要证据由本机 KiCad、ngspice 和 Codex 独立核验。 [预检证据](evidence/workers/doctor.json)
