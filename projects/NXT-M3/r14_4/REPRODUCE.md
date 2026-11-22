# R14.4 P01 复现

从 `projects/NXT-M3/r14_4` 执行。使用 KiCad 10.0.8 原生 Windows Python/pcbnew 和 CLI。需要同级 `r14` 与 `r14_3`，以及 KiCad 标准符号库和封装库。集成的晶导封装随工程提供，打开 `eda/NXT-M3-R14.4.kicad_pro` 即可使用项目专用库。三路样片留在原路径。

## 重建 PCB 候选

在临时目录复现 Q1 闸门和完整候选。build 脚本从冻结整板导入，按固定坐标和网络重新放置与布线。完整候选重填 F.Cu 接地铜皮，保存修订板，原生 JSON 应为 122 clearance、325 unconnected、0 parity。具有剩余违规时，KiCad CLI 返回 5。

```powershell
$kicadBin = 'C:/Program Files/KiCad/10.0/bin'
$r144Replay = Join-Path $env:TEMP 'nxt-m3-r144-replay'
& "$kicadBin/python.exe" -u build_p01.py --q1-only --out "$r144Replay/q1/eda"
& "$kicadBin/python.exe" -u build_p01.py --out "$r144Replay/full/eda"
& "$kicadBin/kicad-cli.exe" pcb drc --schematic-parity --refill-zones --save-board --severity-all --exit-code-violations --format json -o "$r144Replay/full/DRC.json" "$r144Replay/full/eda/NXT-M3-R14.4.kicad_pcb"
```

## 回归已交付路径

```powershell
& "$kicadBin/python.exe" -u verify_p01.py
```

脚本对冻结整板、三路原样片、R14.4 各运行 ERC、DRC 和 schematic–PCB parity，导出同路径网表并核对 958 个可比较的 PCB 铜端点。预期三组净距为 253/18/122，开路为 337/0/325。Q1 端点为 6/6，Q2 为 5/6。记录通过 `evidence/summary.json`、`evidence/native_commands.json` 和三组原生 JSON、RPT、XML 验证。两版整板还使用 `--all-track-errors` 比对对象。规则解析探针在临时目录把 R14.4 规则应用到同一冻结板，复验相同几何的控制区边界匹配和开关规则优先顺序。可用 `--skip-cli` 重建审计表并使用已归档的原生报告。

`P01_DRC_BEFORE_AFTER.csv` 依赖 KiCad 对象 UUID。原生 DRC 报告语言、条目顺序、时间戳，以及未连接最短生成树的具体端点选取可能随运行变化。开路比较使用网络计数与真实 pad 铜连通分组。几何表用原生铜多边形作同层段距离，弧面误差每个轮廓不超过约 0.0001 mm。焊盘对精确名义距离按矩形或圆角矩形计算。

在 PCB 编辑器中运行 DRC，在 D3.1/D3.2 与 Q28.2/Q28.3 的违例右键菜单选择 Clearance Resolution（间距解析）。对话框的电气最小间距分别为 3.20 mm、2.00 mm。 [实际记录](evidence/editor_clearance_resolution.md)

## Git 核查

```powershell
git rev-parse HEAD
git diff --exit-code 3f9531a456b8a0195363034341071bc9ffd264d1 -- ../r13 ../r14 ../r14_2 ../r14_3
git ls-remote --exit-code origin refs/heads/nxt/nxt-m3-p01-clearance-r14-4
```

以上为离线工程验证工作流。R13 已封存 Harness 模型和配置原样保留。所有工作由宿主 KiCad、Git 和 Codex 执行，付费调用 0。
