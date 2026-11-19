# R8 离线研究与运行记录

|波次|实际消除的工程不确定性|结果|
|---|---|---|
|1 · Gate 0 原配置/资料|3.3 V 逻辑可通信与 3.3 V 能否提供饱和基极电流分开验证。10 kΩ 达不到集电极电流目标所需的基极电流；上游 EN 确认为锁存输入，/OE 实为接地。|继续在 G0 内复算较小串阻/下拉和带载 LVC。|
|2 · Gate 0 参数重审|把两项筛选联合求交，排除 4.7 kΩ/22 kΩ 组合并取得 3.0 kΩ/10 kΩ 研究点。发现半导通管故障超热限，单靠 /OE 不能覆盖。|**HOLD / G0 REWORK**。G1、正式 EDA 和 5 V 闭环未进入。|

[按任务封存的证据与决定](evidence/runs/offline-discrete-g0/) · [预注册初始参数](acceptance.json) · [参数复测](acceptance_rework.json)

前 R8 编排器提交为 `448b791a3ba32559892fb84c2a6749a5a28c1773`，其旧工作流参考 `6be8cbbf4729dacae8aced5981f9d5f32703f27b`，本轮继续复用文件审计、任务依赖、输出预算、证据与恢复逻辑，加入分立 G0/G1/G2 的强制准入。

用户已允许使用 `deepseek-v4-flash`。隔离 `headless` 的配置 dump 和 help 成功，生效 provider 为 `deepseek-official`。实际运行身份、受控 worker host 与计费条件须分别成立。独立 DeepSeek 与 Codex CLI 请求数均为 0，CLI token 为 0，当前会话 token、费用均 UNKNOWN。原 Harness 配置目录链接问题通过隔离启动只读取证；原设置与其他工作树未修改。 [模型取证](evidence/harness_identity.json) · [干运行](evidence/dry_run.json)
