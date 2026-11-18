# Round 4 决策

保留 LT3757A P1 为 EDA 研究候选，原理图 J4 保持断接。UCC28C43 与 24V 不进入此图纸。独立预偏置的 POR 上电先置 FAULT，手动 ARM 后才能启用，OVP 异步优先，辅助电源稳态超过候选门槛才允许 Boost。按实际资料修正 TPS26600 MODE=402k→RTN、CD40109BPWR 的 TSSOP、PB6/PB7 的 AF0 和 KiCad 库表语法。新增 C 原型与低压主机帧工具，通过实际 C 核心 3/6/9 位、协议恢复和故障测试。RS-485 物理层与 STM32 目标尚未台架验证。采纳独立审查关于错帧或漏 Commit 时的混合显示风险，维持组一致性 HOLD。

STM32C011F4P6 的 16KiB Flash、6KiB RAM 与 USART+SWD 足够。对比 ESP32-S3 无线、算力及成熟工具链优越，电流与成本、RF 与固件维护对 V1 不必要。CH32V003/CH32V00x 可进一步降本，要先确认准确封装、USART/SWD 或单线下载和固件维护成本。
