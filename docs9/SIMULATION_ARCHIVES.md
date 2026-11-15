# 仿真证据归档与恢复

2026-11-15 上传进度快照。源码、报告、原厂模型、仿真输入、结果和图表均随当前分支保存。`output/nxt_book/` 保存项目知识书稿及 PDF。工作区附件缓存、文档工具和无关英语笔记未纳入项目。

旧版 `sim/` 下的 `waves.txt` 采用相邻 `waves.txt.gz` 无损保存；本地原件不删除。逐份核验发现两份历史 gzip 解压为空，其原始波形另存为 `waves.raw-exact.txt.gz`，不覆盖历史 gzip；原始路径和 SHA-256 见 `SIMULATION_RAW_RECOVERY.json`。恢复这两份时应解压 `waves.raw-exact.txt.gz` 到同目录的 `waves.txt`。新 24V 工程 `projects/QS30-9_24V/` 保持原始证据文件。

三份 gzip 超过 GitHub 单文件 100 MiB 限制，按最多 48 MiB 拆为 `.part001` 等文件，未改变归档内容。每份归档及其分片的长度和 SHA-256 见 `SIMULATION_ARCHIVE_PARTS.json`。

克隆后在仓库根目录执行：

```powershell
python design9/restore_sim_archives.py
```

脚本验证每个分片及合并结果；已有归档也会核验。随后可用 Python `gzip` 解压所需的 `waves.txt.gz` 得到原始 `waves.txt`，供历史证据路径和校验清单使用。

本次为进度归档，保留历史 FAIL/HOLD、未完成审查和 S06C 续作内容，不代表电气验收通过。
