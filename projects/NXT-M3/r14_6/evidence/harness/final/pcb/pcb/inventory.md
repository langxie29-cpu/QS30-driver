# 证据核查清单

- **DRC 最终值**：`native.after.clearance=79`；`drc_groups_after` 为 60+16+3=79；`drc_other=0`；`after_all_tracks` 与 `after` 相同。
- **开路统计**：`native.after.unconnected=65`；`UNCONNECTED_NETS.csv` after 列合计 65；before 列合计 84，与 `native.before.unconnected=84` 一致；总变化 -19。
- **寄存器开路**：`SER2=1`、`SER3=1`、`SR_CLK_BUS=1`、`HC_CLEAR_N=1`，合计 4；与 CSV 对应网表 after 值一致。
- **Parity**：`native.after.parity=0`；仅为报告字段，摘录中无独立 parity 工件。
- **哈希/复现**：`delivered`、`first_build`、`independent_rebuild` 均为 `dfcaf086...f807`，`identical=true`，且等于 `board_sha256`；`build_exit_code=0`、`replay_exit_code=0`；KiCad `10.0.8` 一致。
- **限制**：仍有 79 个 clearance 分组和 65 个未连接；`rule_sha256`、阴极 30/30、端点 180/180、保护计数未独立复核。
- **结论**：证据内部一致；PASS 仅表示有界复核完成，不表示 DRC 清零或布线完成。
