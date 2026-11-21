## 结论
- 唯一明确中止：`b_pin_step_vref126` 在 `time=0.000390766 s`、`timestep=1.25e-19` 报 `TRAN: Timestep too small ... trouble with node b_sw#branch`，随后 `run simulation(s) aborted`。这是开关支路数值收敛失败，不等同硬件停振。
- `b_low` 摘录仅见时间推进至约 `1.77e-3 s`，无中止文本；不能据此判定其停摆。

## 电路锚点
- `VQ drain sw 0` 与 `X_Q sw gate source` 串联，`b_sw#branch` 即 VQ 的 0 V 电流支路；理想 0 V 源叠加开关边沿、仅 10 fF/节点 cshunt，易造成支路电流不连续。
- 绕组：SPICE 首节点为 dot。`LPOWER primary drain` 的 dot 在输入侧，`LSEC 0 secondary` 的 dot 在地；该相对极性在导通时使次级非 dot 端为负、二极管反偏，关断时为正、二极管导通，属 flyback 正确取向。摘录无原始点极性数据，不能证实与源不符。
- 基准：数据手册/模型为 1.26 V（1.24–1.28），上游 ASC 用 1.22 V；`vref126` 已用 1.26 V 仍在 0.391 ms 中止，故基准差异不是充分原因。分压 1.2Meg/8674 在 1.26 V 下约 175.6 V（1.22 V 下约 170.0 V），与上游 179.5–180 V 不符，设定值仍未验证。

## 最小修复/验证
- 保留 `LM3488_TRANS` 与 `IRFH7185` 模型；先复现同一 `t≈390.766 µs`/`b_sw#branch` 中止。
- 在 `X_Q` 漏源间加物理 RC 吸收或按板级寄生加漏极串联电感（不用行为开关替代硅）；数值诊断可试 `.options cshunt=1e-12` 或 `method=gear`，仅用于判断是否开关边沿数值刚度。
- 对照原变压器图核对点极性；对照 1.26 V 数据手册核对 FB 分压，未解决前不要用 1.22 V 定稿。

## 限制
- `b_low` 摘录无终止错误；无完整 deck、原始点极性、板级寄生/测量；不能把模型中止等同硬件故障。
