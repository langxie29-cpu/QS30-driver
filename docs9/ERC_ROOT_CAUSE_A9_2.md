# REV.A9.2 完整ERC根因与7项错误

两板基线完整报告见 `kicad/logs/a9_2_before/*.erc.rpt/.json`，最终完整报告见 `a9_2_final/`。每条违规ID、根因与原生对象全文见 `a9_2_evidence/all_native_items.csv`；7项机器清单见 `erc_seven.json`。没有批量排除警告。

7项触发规则全部为 `power_pin_not_driven`。它们是符号供电建模缺失，不是证明这些网络断线的证据；实际电源工作能力及高压保护需另行验证。坐标来自基线.rpt引脚坐标；JSON的ERC坐标数值与.rpt比例异常，因此不把JSON坐标直接当mm。最终符号中心坐标另存JSON。

| 唯一ID | 板/基线原生引用/物理功能引用.脚 | 引脚/网 | 基线引脚坐标mm | 真实根因及修复声明 | 最终复查 |
|---|---|---|---|---|---|
| A92-ERC-01 | DISPLAY U1/U_DS_L.1 | VCC/DRV_VDD | 93.98,617.22 | 输入边界J_MOD_L_LV.3来自MAIN Q2.D的受控12V；该端定义供电输出端口 | 原规则消失 |
| A92-ERC-02 | DISPLAY U1/U_DS_L.8 | VSS/GND | 93.98,635.00 | J_MOD_L_LV.2为LV返回，连接MAIN GND；该边界声明供电返回源 | 原规则消失 |
| A92-ERC-03 | DISPLAY U1/U_DS_L.16 | VDD/3V3 | 109.22,635.00 | J_MOD_L_LV.1来自MAIN L1.2的3V3；该边界声明供电源 | 原规则消失 |
| A92-ERC-04 | MAIN U3/U11.4 | GND/GND | 93.98,3014.98 | J1.2为输入电源返回；声明为供电边界 | 原规则消失 |
| A92-ERC-05 | MAIN U3/U11.8 | VCC/3V3 | 109.22,3014.98 | U1.LX→L1.1→L1.2→3V3，源位于L1.2；给被动电感后的供电端声明 | 原规则消失 |
| A92-ERC-06 | MAIN U7/U23.8 | VCC/EXT12 | 109.22,3119.12 | J1.1→F1→D1.A/K→EXT12；源位于D1.K，声明被动防反二极管后供电端 | 原规则消失 |
| A92-ERC-07 | MAIN U14/U_C.30 | VDD/DRV_VDD | 109.22,3327.40 | EXT12→Q2.S/D→DRV_VDD；源位于Q2.3，声明受控电源端 | 原规则消失 |

实现为 `kicad_gen.py:pin_type()` 中**仅上述7个(ref,pin)**的 `power_out`供电端口声明，作用等价在这些已追溯边界放PWR_FLAG。这是ERC建模修复，不是把二极管、电感、FET的物理器件类型改成稳压器。没有给OVP/CS/5V基准节点加任意标志，也没有将输入改为passive压制检查。DISPLAY三供电边界还由F08逐针核对上游同名网；MAIN 3V3的真实性取决于仍需料号/电源验证的U1，而不是由声明保证。

对未完成赋型的U20、MCU、电源等，仍保留A92-H08，尤其有源基准冲突原本不会被passive符号报出。本轮已从真实网表独立查出并修复该冲突；**0个ERC error不能代替模拟电路审查**。后续应建立准确器件符号、电源端口/独立PWR_FLAG分离的正式库，逐脚重审，不能用本次作用域很窄的端口约定推广到任意网络。

| 板 | 基线error/warning | 最终error/warning | 最终CLI rc |
|---|---|---|---|
| DISPLAY | 3 / 58 | 0 / 58 | 5 |
| MAIN | 4 / 302 | 0 / 306 | 5 |
| 合计 | 7 / 360 | 0 / 364 | 原生全严重度检查仍FAIL |

剩余182项 `footprint_link_issues` +182项 `lib_symbol_issues`，分别是QS30封装/符号外部库未配置；新增两只净器件带来4条警告增加（R39删除、新增3只下拉，净增2件）。嵌入符号能被原生加载不代表外部库已冻结，故未关闭。没有用真实封装尚未确认的库来虚构“链接已验证”。

实际命令（完整绝对路径、stdout/stderr、逐命令rc见各run/commands.log）：

```powershell
python design9/kicad_check.py --run a9_2_before
python design9/freeze9.py
python design9/kicad_gen.py
python design9/kicad_check.py --run a9_2_after
# BAT54S实际2/3脚修正后再次生成并检查
python design9/freeze9.py
python design9/kicad_gen.py
python design9/kicad_check.py --run a9_2_final
python design9/validate_freeze9.py --run a9_2_final
python design9/safety_audit9.py
```

各capture包装脚本rc=0表示网表成员与CSV/PCB属性一致；不是ERC/DRC通过。每板原生sexpr/XML导出rc=0；原生ERC/DRC的report/json均rc=5，因显式使用`--severity-all --exit-code-violations`。F01–F12为90阴极、9阳极、接口/地/位序独立检查，12项PASS，不覆盖仍FAIL的高压模拟功能。
