# R2 复现与证据恢复

本轮模型预算已关闭：累计四轮、12 个 Flash 会话、子 Codex 0。复核不需要再调用付费模型。禁止为复核自动执行 `local_live.py --live`。

## 1. 只读数据与算法复核

本机数值解释器：`D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe`（含 numpy/matplotlib）。一般系统 Python 不一定有 numpy。以下 `<PY>` 指该解释器，工作目录为本分支仓库根。

```powershell
<PY> -m unittest discover -s projects/QS30-9_24V/power_loop_r2 -p test_*.py -v
python -m unittest discover -s projects/QS30-9_24V/power_loop_r1 -p test_*.py -v
```

新检查验证：UTF16/UTF8 double/mixed 原生格式、非均匀时间积分、拒绝 NaN/截断/倒序、归档原字节与未刷完尾部恢复、损坏与越界拒绝。都是软件检查，不是电气 PASS。

## 2. 原始 raw 与大型附件

本机未压缩 raw 保留在每例原始目录；小网表、原生日志、预登记、命令和独立结果进入 Git。完整 native raw 以 GitHub **草稿发布附件**封存，避免把多 GB 波形塞入源码历史；需要仓库权限下载，草稿没有发布为产品版本。附件地址及服务端 SHA256 在 `evidence/github_artifacts.json`；原始路径、长度、SHA 与分片顺序在 `evidence/raw_archive_manifest.json`。

容器 `QS30RAW1`：保留原始头部、所有物理完整记录和原始未完整尾部；按固定块对 IEEE754 **位**做相邻记录 XOR 和字节平面重排，再 gzip。没有浮点计算、舍入、重采样或删点。`raw_archive.py` 完整描述解码。恢复原字节 SHA 必须与清单一致；超时 raw 的声明点数、额外记录与尾字节也原样保留，不能强行称为完整终点。

分片下载后放回清单所列 `.local/raw_archives/`（或由下载脚本放置），然后：

```powershell
<PY> projects/QS30-9_24V/power_loop_r2/download_evidence.py --list
<PY> projects/QS30-9_24V/power_loop_r2/download_evidence.py --case filter22R_4p7n_threads1_200ms
<PY> projects/QS30-9_24V/power_loop_r2/raw_archive.py --verify-manifest projects/QS30-9_24V/power_loop_r2/evidence/raw_archive_manifest.json
<PY> projects/QS30-9_24V/power_loop_r2/raw_archive.py --verify-manifest projects/QS30-9_24V/power_loop_r2/evidence/raw_archive_manifest.json --restore-root D:/QS30_R2_RESTORED
```

省略 `--case` 会下载全部现存案例；示例只下载名义200ms，因此完整清单校验前需先下载其他分片。下载脚本使用本机已有 GitHub 凭据访问草稿附件，不记录凭据，也不向附件重定向地址转发授权头。

恢复目标已存在时拒绝覆盖。两份被 Round1 worker 删除的新 raw 无法恢复，明确记录缺口；绝不通过合成波形或重跑冒充原件。R1 原始基线不在此缺口内，按 R1 自己的归档清单恢复。

## 3. 波形独立测量

`lab.native(path)` 只读取普通顺序、未压缩的真实 LT double/mixed binary，严格检查字节长度、单调时间和有限值。`lab.stats` 对插值边界作梯形时间积分，峰峰值为真实保存样本及边界极值，不用自适应样本算术平均。

- 主名义夹具：`evidence/principal/filter22R_4p7n_threads1_200ms/`。
- 核心结果：同目录 `independent_metrics.json`、`startup_entry_supplement.json`；预定义 60–100/100–150/150–200ms 全窗口。
- 真实控制器 OUT 周期：`pulse_analysis.py <raw> <new_output.json> --start .055 --end .060`，不复用栅极振铃多次交越。
- 新回归：`run_regression.py` 的 `measure` 可读取已恢复的完整 raw；不要无意启动它的仿真主入口。
- `render_results.py` 的图仅展示真实 raw 的 min/max 包络或局部完整波形；验收计算仍使用全保存样本。历史 raw 需先由 R1 恢复并设置/更正 `lab.R1_LOCAL`。

## 4. 原生仿真重跑（不含模型调用或实物操作）

引擎为 LTspice **24.0.12.0**，不是目录名所称 26。exe SHA 为 `17f5efb978c0df2e164328b7352801fdc1ed0225827e41669bd9da25893fe96d`。每例 `preregister.json` 含原始模型 SHA、准确 `.tran/.options`、执行上限、假设、主要变量、固定电气门槛及输出路径；`command.json` 和 native log 给出实际执行。后续运行经验证采用 `.options threads=1`，没有放宽 `reltol=.001 abstol=1n vntol=1u`。错误的 `numthreads` 选项解析失败也保留，不能用它重跑。

原模型由登记的原厂源或本机 `QS30-1/projects/QS30-9_24V/sim/s06c_current_cell_v3/ST_AUX12_1ns/` 获取，先核对四个完整 SHA。把网表和匹配的库复制到**新的**实验目录，按其命令执行 `LTspice.exe -b circuit.cir` 并先登记；不要覆盖任何旧案例。程序 rc0、可读 raw 和达到终点分别检查，之后才检查电气指标。

最低单元的 89.17V/1.4A 初态和强制 20ns 门沿只用于隔离器件瞬态；绝不能用它冒充 0V 冷启动。所有真正启动/回归网表均保留 COUT=0、真实控制器、原生 SS/VC，无固定 PWM 或理想 HV 源。

## 5. 历史与工具边界

本机全部 R1 必读输入在 `evidence/preflight/baseline_review.json` 登记；最终重新核对在 `final_baseline_verification.json`。四轮工作会话的原始 prompt、输出、文件审计与当前 Codex 决策保留在 `runs/`、`extension/runs/`。初始配置不因追加预算而改写。原会话内容含错误，正式结论只取独立 raw 测量与主控报告。

没有真实 eFuse/AUX、热态 L(I,T)、确切 COUT 全温模型或真实九管负载时，相应资格继续 HOLD。软件绿色、归档 SHA 一致和服务端上传摘要一致均不能关闭 24V-07/08/09/10 或制造 HOLD。
