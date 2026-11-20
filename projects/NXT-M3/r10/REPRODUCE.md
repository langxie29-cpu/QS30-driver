# R10 复现

入口路径为 `D:/PROJECTS/dsharness/QS30-1/.worktrees/NXT-R10/projects/NXT-M3/r10`。在该目录运行 `python verify_r10.py`。脚本重新生成本轮 CAD、网表、报告和摆位，会覆盖本轮生成的工程草案。对 KiCad 中的手工修改先另存，或将它们回写到生成脚本后再复现。

默认工具为 `C:/Program Files/KiCad/10.0/bin` 中的 KiCad 10.0.8 CLI、Python pcbnew 绑定和 ngspice‑46 DLL，以及系统 Python。可用 `KICAD_BIN` 与 `KICAD10_FOOTPRINT_DIR` 指定其他安装位置。CAD 文件通过项目本地符号表和封装表引用项目封装。其他封装使用 KiCad 10 标准库。所有子页需要与根页在同一项目目录。

| 检查 | 命令或程序 | 退出码及证据 |
| --- | --- | --- |
| 工具版本 | `kicad-cli version` | 0，[commands.json](evidence/commands.json) |
| 原生工程生成 | `python build_schematic.py` | 0，[根页](eda/NXT-M3-R10.kicad_sch) 与 14 个子页 |
| KiCad 解析和 ERC | `kicad-cli sch erc --exit-code-violations -o evidence/ERC.rpt eda/NXT-M3-R10.kicad_sch` | 0，[ERC.rpt](evidence/ERC.rpt) |
| 网表和连接审计 | `kicad-cli sch export netlist --format kicadxml -o evidence/native_netlist.xml eda/NXT-M3-R10.kicad_sch` 与脚本中的 `audit_cathodes()` | 0，[native_netlist.xml](evidence/native_netlist.xml)、[summary.json](evidence/summary.json) |
| 原生 BOM 与 PDF | `kicad-cli sch export bom` 和 `kicad-cli sch export pdf`；完整参数见命令日志 | 0，[native_bom.csv](evidence/native_bom.csv)、[原理图 PDF](evidence/NXT-M3-R10.pdf) |
| 封装/焊盘同步 | `<KiCad Bin>/python.exe build_pcb.py` | 0，[footprint_sync.csv](evidence/footprint_sync.csv)。逐器件核对实际封装、pad、路径与原生 XML 网络并保存 PCB。 |
| PCB DRC + 原理图一致性 | `kicad-cli pcb drc --schematic-parity --format json --exit-code-violations -o evidence/DRC.json eda/NXT-M3-R10.kicad_pcb` | **5，存在违规**。[DRC.json](evidence/DRC.json)、[summary.json](evidence/summary.json) |
| 机械包络 | `python mechanical_layout.py` | 0，[mechanical_clearances.csv](evidence/mechanical_clearances.csv)、[mechanical_layout.svg](mechanical_layout.svg) |
| 低阶原生瞬态 | `<KiCad Bin>/python.exe run_residual_spice.py` | 0，[ngspice.log](evidence/ngspice.log) 与 [residual_energy.cir](residual_energy.cir) |
| R9 基线成本重算 | `python revise_cost.py` | 0，[BOM_R10_COST.csv](BOM_R10_COST.csv)，引用 [R9 原表](../r9/BOM_COST_MODEL.csv) |
| R9 协议回归 | 在 R9 目录运行 `python -m unittest -q test_low_voltage_display` | 0，[commands.json](evidence/commands.json)；仍为主机模型 |

Windows 沙盒中 KiCad CLI 报 HKCU 注册表权限警告，其导出和报告以实际文件及退出码核对。ngspice 加载时报告缺省 `spinit` 未找到，仿真脚本显式验证六个结果。原生 ERC 默认忽略项完整保留在报告尾部，没有添加违规豁免。KiCad CLI 已解析项目并原生绘图，本轮未进行交互 GUI 检查。

## Git 基线

原始本地仓库 `D:/PROJECTS/dsharness/QS30-1`，远端 `https://github.com/langxie29-cpu/QS30-driver.git`。通过 `git worktree list`、`git log --all`、`git rev-parse f74f626^` 和路径读取确认：

- R9 `nxt/nxt-m3-wifi-oled-r9` 的基线为 `f74f626d798407439c17ac635eb7946727dec628`。
- 其直接父提交为 `b264d74dce5b799ecd13286fa3c2880b1b7135d2`，是本地分立阴极 R8。读取了 R8 的管路映射、逻辑/双管旧候选、G0D 残压网表和制造阻塞，R9 的电源候选、成本模型、测试日志和保护资格状态。旧架构的 R7 原生 EDA 只作为文件结构及历史管脚参考。
- R9 项目目录缺少本版原生原理图、PCB 与新闭环仿真，R8 分立目录也以工程验证和仿真证据为主。因此 R10 新建原生工程。
- 直接从源仓库执行 `git worktree add -b nxt/nxt-m3-schematic-pcb-r10 ... f74f626` 返回 255，源 `.git/refs` 无写权限。R10 使用自己的 Git 元数据，在 `.worktrees/NXT-R10` 做独立稀疏检出和同名分支，通过只读 Git alternates 引用本地基线对象。该分支的增量文件和提交对象写入独立仓库。R8、R9 及原工作树不受影响。
