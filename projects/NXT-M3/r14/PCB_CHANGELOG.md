# 原生 PCB 修改与审查

- Q1/R100/R200 从 R11 第一阴极通道挪到左缘可复核摆位。R100 与 R200 的 BASE_00 连线重做，R200 的 GND 接到 SW1 地铜。Q1 的 BASE_00、DRV_00、K1_0 和发射极返回仍需闭合。Q1 的两项外部 Q2 碰撞和一项 R100 碰撞消除，留下两项同封装 0.6552 mm。原生铜规则下未将该单元复制到另外 29 路。
- 新增 J5、J6、输入 RC、TVS、附件供电 DNP 和 Q35。两个连接器均有实体焊盘、丝印及部分线路。J6 的 STOP_LOOP 和 STOP_GATE 已走通，Q35 的 FAULT_N 仍开路。U8 的 ARMED 已接入原有同网分支，U9 到 U8 的 LATCH_CLR_N 仍开路。J5 四个接触信号均连到各自 TVS，GPIO/RC 路径仍有未连通项。
- R40 原生 DNP。PCB 外形、RF keepout 及安装孔坐标、形状与钻孔属性与 R11 一致。连接器落在低压服务侧。射频表现、机箱内空间、线束弯曲与外露金属实样仍需核对。
- 最终 KiCad 10.0.8 对候选报 260 项净距、365 项开路 / 169 个网络、0 原理图一致性问题。R11 同工具复跑 263 项净距、345 项开路 / 166 个网络、0 一致性问题。新增接口引入尚待完成的连接。按违规类型及关联对象 UUID 对比，新增违规 0 项，消除 Q1 邻近铜违规 3 项。
- 原生 ERC 0 error / 0 warning。沿用四个忽略类别。DRC 沿用五个忽略类别，未添加排除项。候选的规则文件内容与基线相同，项目设置除项目文件名外一致。

[PCB](eda/NXT-M3-R14.kicad_pcb) · [原生 DRC](evidence/drc/DRC.rpt) · [几何与铜差异](evidence/pcb/mechanical_and_copper.json) · [检查摘要](evidence/pcb/summary.json) · [布线路径及回滚](evidence/pcb/routing.json)
