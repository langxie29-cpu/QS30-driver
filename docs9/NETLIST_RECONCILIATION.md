# REV.A9.1 原生网表收敛记录

真实工具 KiCad 10.0.6；日期2026-10-18；制造/高压调试HOLD。输入哈希、全部argv/输出/返回码见 [rev_a9_1_20261018/results.json](../kicad/logs/rev_a9_1_20261018/results.json) 和 commands.log。旧根目录报告/网表不覆盖；b6a9082关键文件逐字节备份及SHA256在kicad/logs/b6a9082_evidence/。

## 实测数量

| 板 | 修前预期/原生有效网 | 修前名称一致/节点 | 修后预期/有效网 | 独立NC网 | 原生总网/总节点 | 修后已连接节点一致 | 合并/拆分/PCB已连接焊盘差异 |
|---|---|---|---|---|---|---|---|
| QS30-9_DISPLAY | 52/32 | 69/134 | 53/53 | 17 | 70/175 | 158/158 | 0/0/0 |
| QS30-9_MAIN | 131/45 | 137/500 | 132/132 | 38 | 170/570 | 532/532 | 0/0/0 |

NC是原生KiCad为显式no_connect引脚导出的unconnected-*单节点网，不是有效通道。DISPLAY17、MAIN38项均与完整引脚库存一致，逐项隔离。有效网络53/132的变化来自真实新增转换/偏置、门控未用输入和主板地桥。旧134/500节点全部存在仍发生18组合并、428条名称不符；同节点数量不能证明电气正确。

根因是生成器固定26mm行距且未按长符号分配高度，导线可重叠跨入另一符号；另有端点不在网格。此次修复布局生成算法，所有有效网络成员按集合比较，0合并、0拆分、0缺失、0意外连接；不通过改CSV名称迎合原生错误网络。原生multiple_net_names由19变0、off-grid由799变0。

逐输出核对90项、每个阴极恰好(驱动脚,管座脚)两端点；9条独立阳极支路；6未用输出；36个连接器配对；DIN/CLK/LE/BL/串行回线、5种电源地组及唯一地桥均有机器审计。右模块是已核对DISPLAY等价模板，不是额外原生项目。参见QS30_PIN_MAPPING、INTERCONNECT_PINOUT及F01–F12审计。

PCB与原理图统一Reference、DesignRef与symbol path；已连接焊盘网络逐引脚相等，**这不消除几何上的铜短接**。本轮开启--schematic-parity；其55个net_conflict都是原理图显式NC名与PCB无net焊盘的差异，单列A91-N04，不忽略；其余PCB短路/间距/未布线见问题清单。

## 原生ERC/DRC（JSON实际条目，不数报告标题字符串）

| 板 | 修前ERC错误/警告 | 本轮ERC错误/警告 | 修前DRC错误/警告 | 本轮DRC错误/警告 |
|---|---|---|---|---|
| QS30-9_DISPLAY | 0/207 | 3/58 | 86/26 | 109/50 |
| QS30-9_MAIN | 0/941 | 4/302 | 694/147 | 868/193 |

两板sexpr/XML导出均rc=0；ERC与DRC（report/json各执行）均rc=5，明确FAIL。以前ERC/DRC rc=0只表示命令正常结束，未启用违规退出；旧脚本用error/错误/violation全文匹配还误计标题。此次未修改任何规则严重度、未增加排除或跳过检查；默认KiCad ignored_checks清单亦保留。

## 实际执行与可重跑方式

```text
git status --short
git log -6 --oneline
git switch -c rev-a9-1-electrical-freeze
python design9/reconcile9.py --run before_a9_1_complete  # rc=1：证实基线网络错误
python design9/freeze9.py                           # rc=0
python design9/kicad_gen.py                         # rc=0
python design9/kicad_check.py --run rev_a9_1_20261018 --publish  # rc=0：拓扑收敛，不是ERC/DRC通过
python design9/validate_freeze9.py --run rev_a9_1_20261018       # rc=0：12/12结构核对
python design9/report_freeze9.py --run rev_a9_1_20261018
```

原生命令模板（每板均实际执行sexpr、XML、ERC report/json、DRC report/json，确切绝对路径与rc见commands.log）：

```text
kicad-cli sch export netlist --format kicadsexpr -o <new-run>/<board>.net <board>.kicad_sch
kicad-cli sch export netlist --format kicadxml -o <new-run>/<board>.xml <board>.kicad_sch
kicad-cli sch erc --format report|json --severity-all --exit-code-violations -o <new-run>/<board>.erc.rpt|json <board>.kicad_sch
kicad-cli pcb drc --schematic-parity --format report|json --severity-all --exit-code-violations -o <new-run>/<board>.drc.rpt|json <board>.kicad_pcb
```

证据过程：before_a9_1首次捕获在Python读取kiutils properties时异常（非KiCad错误），已保留6份DISPLAY原生输出；before_a9_1_complete修复后完整捕获。after_a9_1和after_a9_1_final是中间版本，均保留；最终以本文件run为准。目录已存在时脚本拒绝覆盖。新运行使用新的--run名称，不可重复覆盖本run。未生成Gerber/钻孔等制造文件，未下单，未运行SPICE。
