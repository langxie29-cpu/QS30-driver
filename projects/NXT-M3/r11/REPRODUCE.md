# R11 复现

从本目录运行命令。KiCad 10.0.8 默认位于 `C:/Program Files/KiCad/10.0/bin`，可用 `KICAD_BIN` 指定。包含 pcbnew、NumPy、ngspice DLL 及 XSPICE 模块的 KiCad Python 用于板级复核和 RAW 解析。

```powershell
python native_checks.py evidence/r5
python audit_pins.py evidence/r5/native_netlist.xml
& 'C:/Program Files/KiCad/10.0/bin/python.exe' audit_board.py evidence/r5
python sim/run.py vendor
python sim/run.py proxy
python sim/run.py fault
python sim/run.py protection
python sim/run.py layout
& 'C:/Program Files/KiCad/10.0/bin/python.exe' sim/process_waveform.py
python qualification.py
```

可加 `--case nominal` 或 `--suffix _rerun`。厂商下载须符合 `sim/run.py` 中的 SHA-256，可用 `--vendor-zip` 指向同一原包。需要精确重跑历史工况时，在原网表副本上执行 `<KiCad python> -u sim/dll_run.py <copy>/circuit.cir`。TI 三次运行用原库、删除未兼容 COMP 局部初值的库、以及零输入 DC 初值三类证据。归档测量与当前重跑的时间戳及恰同散列依赖模拟器和平台。脚本会写各工况输出，使用独立副本或后缀保护原存档。

布线路径算法由 `route.py`、`refine_routes.py`、`pour_lv.py` 实现。只在独立草稿或阶段快照上执行。R3 的起点为 R1 无铜板，R4 的起点为 R3 已存板。原生版图是交付基线，分区报告及最终原生 DRC 可独立复核。
