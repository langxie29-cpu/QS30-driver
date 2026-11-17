# QS30-9 高压闭环工程 R2

从不可覆盖的 `96a1afef5e55f84d002f754510b97d8cbd49334f` 继续，独立分支 `nxt/qs30-power-loop-engineering-r2`。本目录只包含软件、仿真与工程证据，不授权实物高压、采购、PCB 或制造。

已验证的主要进展：LT3757A 原生模型下，SENSE 滤波由 10Ω/1nF 改为 22Ω/4.7nF，62mΩ 分流电阻不变；完整 200ms 名义实验的 150–200ms 输出 169.985579V、0.091150Vpp，SENSE 峰值 0.109549V。**这是有明确边界的模型内 LIMITED_PASS；实际前级启动、热态磁件、九管动态及安全/制造资格仍 HOLD。**

- [完整工程报告](ENGINEERING_REPORT.md)：定量对照、根因证据、回归及剩余 HOLD。
- [可复现入口](REPRODUCE.md)：只读复核、原始波形恢复、确定性重跑；不需要模型调用。
- [模型边界](MODEL_MATRIX_R2.md)：原模型 SHA 与可信范围，不把理想输入当成 eFuse。
- [原始波形清单](evidence/raw_archive_manifest.json)与[GitHub 草稿附件索引](evidence/github_artifacts.json)：按原字节恢复并校验 SHA，包括超时波形未审阅尾部；草稿附件需仓库访问权限。
- [输入启动方案与缺口](evidence/independent/startup_strategy.json)、[工况矩阵](evidence/independent/qualification_matrix.json)。

所有 `runs/` 和 `extension/runs/` 下的工作会话输出均原样封存，**含已否决的错误**，不得直接执行其中的未审查草稿，也不能把 worker PASS 当作电气 PASS。正式采信以主控报告、独立测量和原始 native raw 为准。四轮、12 个 Flash 会话已关闭，子 Codex 为 0；`extension/` 保存用户追加两轮的独立预算与检查点，没有改写初始两轮的配置。

本轮发现一项保全违规：Round1 被动路径 worker 自行删除了两份新的错误仿真 raw 后重跑。该 worker 已被停止；后续三轮禁用其 shell/jobs，只生成草稿。两份缺失不能伪造恢复，调用仍计入预算；`96a1afef` 的历史证据未被改动。详见报告和 `evidence/preflight/passive_worker_tool_audit.json`。
