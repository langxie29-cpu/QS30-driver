# R14.5 复现与核查

工程入口为 [NXT-M3-R14.5.kicad_pro](eda/NXT-M3-R14.5.kicad_pro)，用 KiCad 10.0.8 打开。R14.4 输入固定为提交 f1d07975d1479ff30372078b562e66f7913cdb1c 上的已交付 PCB。以下命令从本目录执行，在新临时目录复现。

## 本地预检

R13 密封配置及权限沿用现有版本。以下预检均为本地调用，付费 Worker 调用 0 次。

```powershell
Push-Location ../r13
python -m unittest -v test_orchestrate.py
$node = 'D:/PROJECTS/DeepSeekHarness/runtime/node-v24.19.0-win-x64/node.exe'
$dsh = 'D:/PROJECTS/DeepSeekHarness/app/node_modules/@deepseek-ai/dsh/lib/bin.js'
python orchestrate.py --doctor --dsh $node $dsh
Pop-Location
```

## 重建外置管座候选

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$kicad = 'C:/Program Files/KiCad/10.0/bin'
$pcbpy = "$kicad/python.exe"
$cli = "$kicad/kicad-cli.exe"
$replay = Join-Path $env:TEMP ('nxt-r145-replay-' + [guid]::NewGuid().ToString('N'))
$env:NXT_R145_DEPS = Join-Path $env:TEMP 'nxt-r145-router-deps'
& $pcbpy -m pip install --target $env:NXT_R145_DEPS --no-deps shapely==2.1.2 scipy==1.16.3
$board = "$replay/eda/NXT-M3-R14.5.kicad_pcb"

function Invoke-RouteCheck {
    param([string] $Name, [switch] $Fill)
    $options = @('pcb','drc','--all-track-errors','--schematic-parity','--format','json')
    if ($Fill) { $options += @('--refill-zones','--save-board') }
    & $cli @options -o "$replay/$Name.json" $board
    if ($LASTEXITCODE -ne 0) { throw "KiCad DRC execution failed for $Name" }
}

& $pcbpy -u route_board.py q2 --out $replay
Invoke-RouteCheck g1
& $pcbpy -u remote_display.py place --out $replay
& $pcbpy -u remote_display.py cathodes --out $replay
Invoke-RouteCheck cathodes -Fill
& $pcbpy -u remote_display.py drivers --out $replay
Invoke-RouteCheck drivers -Fill
& $pcbpy -u remote_display.py controllers --out $replay
Invoke-RouteCheck controllers -Fill
& $pcbpy -u remote_display.py fanout --out $replay
Invoke-RouteCheck fanout -Fill
& $pcbpy -u settle_routes.py restore --out $replay
& $pcbpy -u settle_routes.py prune --out $replay
& $pcbpy -u route_board.py protect --out $replay
Invoke-RouteCheck protect -Fill
& $pcbpy -u route_board.py general --out $replay --drc evidence/routing-inputs/general.json
Invoke-RouteCheck general -Fill
& $pcbpy -u remote_display.py finish --out $replay
Invoke-RouteCheck finish -Fill
& $pcbpy -u route_board.py refine --out $replay --drc evidence/routing-inputs/refine.json
Invoke-RouteCheck refine -Fill
& $pcbpy -u settle_routes.py boundary --out $replay
Invoke-RouteCheck boundary -Fill
& $pcbpy -u settle_routes.py restore --out $replay
& $pcbpy -u settle_routes.py prune --out $replay
& $pcbpy -u settle_routes.py polish --out $replay
Invoke-RouteCheck final -Fill
& $pcbpy -u verify_board.py --out $replay
```

某脚本返回非零时，在该阶段查阅本地输出。两个整板寻路阶段使用随工程归档的原生开路端点种子，固定 KiCad 未连接最小生成树在同距时的取舍。修改布局后可改用本次生成的 protect.json 或 finish.json 重新求路。PCB 本体 SHA-256 记录在 [ROUTING_GATE_RESULTS.json](ROUTING_GATE_RESULTS.json)。

## 回归已交付 PCB

```powershell
& $pcbpy -u verify_board.py
git diff --exit-code f1d07975d1479ff30372078b562e66f7913cdb1c -- ../r14_4
git rev-parse HEAD
git ls-remote --exit-code origin refs/heads/nxt/nxt-m3-full-routing-r14-5
```

原生 ERC、DRC、all-track-errors、parity 和网表位于 [evidence/after](evidence/after)。比较输入位于 [evidence/before](evidence/before)。常规和 all-track 模式分别计数。过孔字段是经铜几何验证的最少换层过孔数。若某端点只能由 KiCad 的已填铜连通引擎证实而无法独立重建路径，该字段留空。
