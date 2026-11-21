# 实体功能控制接口

J5 是独立六芯 JST GH 顶插接口，正式编号由冻结网表核对。J6 HV STOP 采用不同的两芯 JST PH 侧插接口，接触件与线束不能互插。每块 M3 使用同一原生 PCB 候选。 [JST GH](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf) · [JST PH](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)

| J5 针 | 信号 | U3 | 用途 |
|---|---|---|---|
| 1 | GND | 地 | 干接点回路 |
| 2 | BTN1 | GPIO10 / 18 | 功能键 |
| 3 | BTN2 | GPIO11 / 19 | 功能键 |
| 4 | AUX1 | GPIO12 / 20 | 备用 / 编码器 A |
| 5 | AUX2 | GPIO13 / 21 | 备用 / 编码器 B |
| 6 | 3V3_AUX | 经 R508 和 D14 | 首版未供电 |
| MP | GND | 地 | PCB 固定片 |

全部 41 个模块引脚在机器核对文件中记录。GPIO10–13 在 R11 均为明确 NC。原有 0/3/45/46 启动绑定位、UART0、USB 19/20、SPI/PSRAM 风险脚、时钟、看门狗和 ARM 等共用资源按原图保留。启动不能等候用户输入释放。 [GPIO 审计](evidence/pcb/summary.json) · [ESP32-S3-WROOM-1](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)

每路 TVS 接线侧到地，再经过 1 kΩ 串阻、10 kΩ 上拉与 10 nF。触点闭合时的活动电平约 0.300 V，释放的 RC 约 100 µs。软件建议按键 10–20 ms 去抖，编码器使用短窗口和正交非法状态过滤。J5 和 R508/D14 首版 DNP。若批准装附件供电，330 Ω 电阻把 3.6 V 上界的短路电流限制在 10.9 mA 以下，BAT54H 抑制从附件正向反灌。建议只评价 ≤1 mA 负载。针脚电压随负载、温度与料差变化，连接器名义是 3V3 域，实际最低电压待验证。禁止外供电接入此针脚，反接线束的故障验证包括负压、输出反灌及短接至相邻信号。 [TVS](https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf) · [BAT54H](https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf)

最小低压测试使用被动开关夹具。核对针脚、保持各键上电、测试单键和同时动作、输入失电/回灌、开短路、编码器正反向及抖动。接着按产品预期线长和外壳测接插件 ESD、错误插线及实际插拔净空。PCB 连通性与最终电缆方向以原生 DRC 和整机模型为准。
