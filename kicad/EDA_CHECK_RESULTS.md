# KiCad 10 原生检查结果（真实日志）

工具：`C:\Users\Admin（无密码）\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe`（KiCad 10.0.6）；日志：`kicad/logs/`

| 板 | 网表导出 | KiCad 网络/节点 | CSV 节点 | 名称一致 | 节点对应 | ERC rc | ERC 错误/警告 | DRC rc | DRC 错误/警告 |
|---|---|---|---|---|---|---|---|---|---|
| QS30-9_DISPLAY | rc=0 | 32/134 | 134 | 69/134 | 134 | rc=0 | 2/209 | rc=0 | 89/27 |
| QS30-9_MAIN | rc=0 | 45/500 | 500 | 137/500 | 500 | rc=0 | 2/943 | rc=0 | 697/148 |

## 状态分级

| 级别 | 状态 | 证据 |
|---|---|---|
| L1 已生成 | ✅ | kicad/projects/*（6 文件） |
| L2 语法解析 | ✅ | kiutils 1.4.8 回读成功 |
| L3 能在 KiCad 打开 | ✅ | 本表 netlist_rc=0（KiCad 10.0.6 真实加载并导出） |
| L4 原生 ERC | ✅ 已执行（见日志；存在错误/警告未修复） | kicad/logs/*.erc.rpt |
| L5 原生 DRC | ✅ 已执行（初布局，存在错误/警告未修复） | kicad/logs/*.drc.rpt |

## 未完成/风险

- ERC/DRC 日志中的错误**尚未修复**，PCB 仅为初布局（矩形近似焊盘、无布线）；
- 管座/HV 连接器/PQFP-44 封装尺寸仍为 PROVISIONAL，不能据此刻板；
- 名称一致率反映自动符号+标签映射是否正确；未一致项需逐项修（见日志）。
