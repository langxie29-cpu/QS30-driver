# R14.3 复现与证据索引

2026-11-22。使用 Python 3.11、ngspice 47 console、KiCad 10.0.8 / pcbnew。运行目录为 `projects/NXT-M3/r14_3`。基线提交 `db3d7cc3420c255fe2cb0e270b602cce5384dd2f`。软件执行不需要任何实物硬件。

```powershell
$spice = 'D:/PROJECTS/dsharness/QS30-1/tools/ngspice47/Spice64/bin/ngspice_con.exe'
$kicad = 'C:/Program Files/KiCad/10.0'
python run_scan.py --ngspice $spice
python run_interlock.py --ngspice $spice
& "$kicad/bin/python.exe" -u build_candidate.py $kicad
python make_evidence.py
& "$kicad/bin/python.exe" -u ../r14_2/verify_r14_2.py --out "$env:TEMP/r143-regression/evidence"
git diff --exit-code db3d7cc3420c255fe2cb0e270b602cce5384dd2f -- ../r13 ../r14 ../r14_2
```

在其他安装位置替换两个变量。每个 `evidence/spice/<工况>` 或 `evidence/interlock/<工况>` 都包含 `case.json`、`circuit.cir`、`run.log` 和无损 gzip 包装的原生二进制 `waveform.raw.gz`。把网表复制到临时目录后运行 `ngspice -n -b circuit.cir` 可在同目录生成 RAW。以 `gzip.decompress` 解包后，ngspice `load waveform.raw` 可读原始数据。也可使用 `run_scan.read_raw(Path(...))` 取得行列。默认归档所有求解采样时刻。ngspice 日期头、KiCad 对象 UUID 和报告时间可能在复现时变化，请核对指标和连通，不比较动态元数据。仅重跑单案时使用独立输出目录，避免覆盖整表。

```powershell
python run_scan.py --ngspice $spice --only '^cut_linear_0.001$' --out "$env:TEMP/r143-single"
```

波形 `v(c1)`、`i(vc1)`、`v(qb1)`、`i(vb1)` 为 Q1 VCE、IC、VBE、IB，Q2/Q3 后缀依次替换。各支路功率向量由 B 源写成数值等于瓦数的电压。CSV 后缀 `_J` 为从本工况开始到观察终点的梯形积分。仿真只给出相应模型的实际逐针瞬态。源端为最大 30 mA 的单向供电代理，低逻辑为 10 µF 与指定电阻，停止后源代理为 0 V，U18 单独禁止代理留 4.4 V。C47 3.63 µF、ESR 默认 0.25 Ω，另有 2 Ω 敏感性。模型未包含升压变换动态或电弧物理。首个低于 60 V 的样点从源停命令计时。全部功率积分的差值门槛为 50 µJ 加输入、耗散、储能变化绝对值三者中最大者的 1%。对两个关键断供案例另作最大步长减半。此数值误差与真实器件和拓扑误差分开。 [误差结果](evidence/energy_audit.json) · [证据文件 SHA-256](evidence/package_sha256.json)

候选复制继承的项目规则，并仅在样片增加二极管前后 2.00 mm 距离筛查。候选和冻结板的原生 DRC 退出码 5 为有已登记违规，复现脚本按违规类型、连通和一致性验证。样片的 KiCad 工程不含完整高压激励器、负载或量测整机。与现板没有电气并接。 [候选规则](candidate/R14_3-protection-coupon.kicad_dru) · [候选审计](evidence/candidate/audit.json)

```powershell
Push-Location ../r13
python -m unittest -v test_orchestrate.py
$node = 'D:/PROJECTS/DeepSeekHarness/runtime/node-v24.19.0-win-x64/node.exe'
$dsh = 'D:/PROJECTS/DeepSeekHarness/app/node_modules/@deepseek-ai/dsh/lib/bin.js'
python orchestrate.py --doctor --dsh $node $dsh
Pop-Location
git rev-parse HEAD
git ls-remote --exit-code origin refs/heads/nxt/nxt-m3-thermal-protection-r14-3
```

使用 R13 已封存的工具禁用、模型、供应方与验收方式。付费 Worker 未启动，工程决策、归档和 Git 由 Codex 执行。 [基线协议](../r13/REPRODUCE.md)
