# R14.2 复现

基线分支 `nxt/nxt-m3-safety-layout-r14`，冻结提交 `5470020e10f5d6d98f6e21cc93951ca573e20965`。从 R14.2 checkout 的本目录执行。

```powershell
$kicadPy = 'C:/Program Files/KiCad/10.0/bin/python.exe'
& $kicadPy -u verify_r14_2.py
git diff 5470020e10f5d6d98f6e21cc93951ca573e20965 -- ../r14/eda
git ls-remote --exit-code origin refs/heads/nxt/nxt-m3-insulation-r14-2
git rev-parse HEAD
```

脚本读取同级 [R14 原生工程](../r14/eda/NXT-M3-R14.kicad_pro)，重跑原生 ERC、XML 网表导出和含 `--schematic-parity` 的 DRC，兼用 R14.1 的 pcbnew 铜图端点审计。退出码 5 是当前 DRC 有违规时的预期值。脚本比较基线报告的违规对象 UUID 集合、逐网开路计数、原理图针脚网络及端点计数。原生报告的时间、语言及同一网络中列举的飞线端点可随运行变化。保存的工程输入 SHA-256 包含 PCB、顶层原理图、项目设置和规则。 [命令与退出码](evidence/native_commands.json) · [铜连通及一致性结果](evidence/terminal_audit.json)

晶导几何基于 p. 3 的公制名义标线。脚本从 pcbnew 提取实板中心、圆角、铜/阻焊/锡膏层，重新计算 3 对距离，并用 KiCad 形状碰撞检查建议焊盘对现有引出线的影响。计算在内存中完成。另从 R14 保存的 ngspice RAW 提取同一时刻的 C–B、C–E、B–E 峰值，并按 R14 截止代理复制 195 V 工况。新增网表、日志及 RAW 在 [off_195](evidence/off_195/)。

可向 `--out` 传入本盘上的临时证据目录。两个 CSV 输出在证据目录的父目录。脚本在 Windows 下使用 KiCad 10.0.8 随附 Python、pcbnew 和 ngspice DLL。原厂图来源与所阅文件哈希见 [封装核查](MMBTA42_MANUFACTURER_FOOTPRINT_AUDIT.md)。输出目录不是制造资料。

只读 Harness 预检在同级 `r13` 执行，调用数为 0。R13 的 live 模式绑定其原分支、登记任务和显式成本确认。 [预检记录](evidence/worker_doctor.json)

```powershell
$node = 'D:/PROJECTS/DeepSeekHarness/runtime/node-v24.19.0-win-x64/node.exe'
$dsh = 'D:/PROJECTS/DeepSeekHarness/app/node_modules/@deepseek-ai/dsh/lib/bin.js'
Push-Location ../r13
python orchestrate.py --doctor --dsh $node $dsh
Pop-Location
```
