# Round 4/5｜Agent C 独立安全审查

审查员未参与A/B/D初稿。只写本review目录，修正由原作者完成。无物理实验、原生ERC或制造释放。独立测试判据见PREREGISTER.md。

## 实际反例闭环

`test_adversarial.py`首次实际执行4个测试，2 PASS/2 FAIL，日志`round4_initial.txt`。RUN中无故障按RESET仍维持所有输出；RESET持续高时可接受新START与请求，均违反REQ01。D修正为先执行故障优先与合格清锁，再在健康复位保持期间强制OFF、清新请求及人工边沿资格。C独立用**同一四个判据**复测4 PASS/0 FAIL，日志`round5_retest.txt`。仅关闭规格模型缺陷；真实异步竞争和掉电边沿仍HOLD。

## 逐项发现与结论

|ID/严重性|证据|修正/复测|状态|
|---|---|---|---|
|C01/P0|verification/safety_model.py原tick忽略健康态reset；独立4例中2失败|D修复；C同四例全通过|FIXED_LOGIC_ONLY|
|C02/P0|架构要求窗口心跳；B U470=TPS3431SDRBR只有超时检测|B追加WATCHDOG_WINDOW HOLD；不得降低到普通watchdog要求|HOLD_HARDWARE|
|C03/P0|U460 CLR/HARD_FAULT_CLEAR_N、U461 RUN_CLEAR_N及START/RESET资格为未实现接口|B追加ASYNC_ARBITRATION HOLD；PRE高/CLR低只能支持静态优先，清零释放与CLK竞争未证|HOLD_HARDWARE|
|C04/P0|RTN100/101与USB地不同；CSV中FLT保持HOLD隔离网络|未见本轮把FLT直接上拉3V3的旧错误；真实FLT/IMON及PG半供电边界仍缺|HOLD_ELECTRICAL|
|C05/P0|U430独立OVP上臂任一开路会读成低；双残压共地仍共因|文档明确独立检测不等于自身诊断通过；需要证明测试/共地断路覆盖|HOLD_SINGLE_FAULT|
|C06/P0|eFuse卡通仍有L/D到输出被动路径，MOS短路不能由gate禁止清除|架构、B说明和D拓扑低压单元保留此限制；关断命令不能当隔离测量|HOLD_PHYSICAL|
|C07/P0|四支200k中只剩主板支路，最大C和+1%R，195→60约5.075s|D低压缩放单元记录5s工程指标FAIL；不延长指标|FAIL_BLEED_REQUIREMENT|
|C08/P0|BL、COMP钳位、真退磁、持续OC、PG转换仍列unimplemented_blocks|CSV为部分逐脚表，不能作为可投板电路；真实模型/时延/储能仍HOLD|HOLD_COMPLETENESS|
|C09/P1|BOM全部立创ID未核实，无源项多只有数值；无原生工程/ERC|B强调非完整采购BOM；E保留封装/间距/迁移前置条件|HOLD_MANUFACTURING|

TPS3431依据独立阅读原厂 [SNVSB66A §5/§7](https://www.ti.com/lit/ds/symlink/tps3431.pdf)：WDI下降沿在超时前服务，没有已实现的最小服务间隔监视。因此当前候选不能证明拒绝过快心跳。程序死机但硬件定时器继续输出的情况也仍需独立挑战/服务策略。

## 覆盖审查

DRV许可不包含DRV_OK，避免自启动死锁；支路许可不等待PRECHARGE_OK，避免预充死锁。PG断电开漏释放不能视为健康，A/B均声明有效偏置资格；对应接口未实现，所以没有电气PASS。复位模型包含residual_valid及branch_off_confirmed，支路卡通充到24V即使低于60V也不可清锁。

FAULTS参数是“已被检测的故障”假设；双故障枚举不能证明物理双短路覆盖。power/thermal/heartbeat等资格被压缩为布尔输入，标准测试不能证明实际分压断线、温度曲线、MCU任务健康或时延。输出电容仍有能量；关PWM/24V不表示残压安全。未知/未供电残压必须阻止复位，不能由USB逻辑供电推断模拟监测已有效。

D的实际器件SPICE只覆盖驱动宏模型/线性负载；低压检测及泄放单元只覆盖各自模型边界。执行失败/无完整波形不能算电气通过。原始spice_r1结果存在执行FAIL未分配electrical类别的记录缺口，已由D追加分类审计，不覆盖原文件。

## 当前审查放行范围

在本轮可执行范围内，独立反例的两个新增严重逻辑缺陷已修复并复测。仍存在明确的硬件设计完整性及单故障HOLD；因此不能宣称“安全系统已经完成验证”。允许继续设计物理无Boost链的低压验证板；释放制造前补齐实际边沿/锁存/窗口监控/PG链、真实封装与低压ERC。完整QS30主板不放行。24V-07/08/完整09及制造HOLD维持。
