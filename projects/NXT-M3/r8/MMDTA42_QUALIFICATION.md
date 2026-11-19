# MMDTA42-7-F 器件资格

**分立开关仍是候选。当前 G0-A 为 REWORK。** 资料为 Diodes Incorporated DS30438 Rev. 5-2。确切订购料号 MMDTA42-7-F，K3M 标记，SOT-26，卷盘 3000 件，MSL 1。器件含两路独立 NPN，设计仍需逐封装检查引脚与贴装方向。 [原厂数据表](https://www.diodes.com/datasheet/download/MMDTA42.pdf) · [原厂封装](https://www.diodes.com/package/view/368.info)

|参数|原厂条件|R8 适用性|
|---|---|---|
|VCEO / VCBO / VEBO|300 / 300 / 6 V。V(BR)CEO 在 IB=0、IC=1 mA，V(BR)CBO 在 IE=0、IC=100 µA|170 V 工作和 195 V 故障筛选在额定值之下。开关过冲、邻脚电压域和装配污染裕量未验证。|
|IC、Pd、θJA|500 mA 受饱和和温升约束。300 mW、417 °C/W 基于 1×0.85×0.062 英寸 FR-4 原厂试板。TJ/Tstg −55 至 +150 °C|按整包 300 mW 保守分配。85 °C 时约 156 mW。缺独立线性区 DC/脉冲 SOA 曲线及双裸片互热系数。|
|hFE|最小 25@1 mA，40@10/30 mA，VCE=10 V、25 °C，短脉冲|适于估算正向放大区。用于 1.5–3.3 mA 全温饱和资格的证据不足。|
|VCE(sat)、VBE(sat)|最大 0.5 V 和 0.9 V，IC=20 mA、IB=2 mA、25 °C，短脉冲。图 2 为强迫 β=10 的曲线|R8 用 β≤10 筛选。低电流、温度和长时 VCE(sat) 仍须验证。|
|关断漏电|ICBO≤100 nA @ VCB=200 V、IE=0、25 °C。IEBO≤100 nA 列于关断表。CCB≤3 pF @ VCB=20 V、1 MHz|热态基极连接状态的 ICE、鬼影、快速 HV 上升的耦合待确认，10 µA 仅为灵敏度上界之一。|

封装端子图按顶视得到 Q1 E/B/C=1/2/6，Q2 E/B/C=4/5/3。原厂图端子未直接印脚号，现给出可复核的草案。0.95 mm 脚距与数字编号映射应在原厂 CAD、贴装方向和封装审核时关闭，尤其是第 3、6 脚的交叉。SOT-26 可减少 15 个封装/板，但双管公用封装的热、故障和返修相互关联。 [图与机械规格](https://www.diodes.com/datasheet/download/MMDTA42.pdf) · [映射](30_CHANNEL_PIN_MAPPING.csv)

原始 10 kΩ/22 kΩ 在理想 VOH=3.3 V、假设 VBE=0.9 V 时只有 0.199 mA 基极电流，要求 3 mA/10=0.300 mA。计入 1% 电阻角后降到 0.196 mA。较小电阻的结果见独立复算。即使管电流名义为 3 mA，3.3 mA 仍保留为 175 V/薄阻差附近的上界研究点。 [基极复算](evidence/runs/offline-discrete-g0/round_02/base_drive_rework/metrics.json)

额定功耗不能覆盖所有故障。195 V 与 19.8 kΩ 串联，假设管内部短接而 BJT 半导通。负载线的峰点是 VCE=97.5 V、IC=4.92 mA、P=480 mW，已超过 25 °C 指定试板值，85 °C 更严。此状态是设计反例，需独立硬件限能。C–E 失效短路时，封装本身可能低耗散但阴极持续接通，必须从阳极侧移除能量。 [故障矩阵](HV_DRIVER_SAFETY_REVIEW.md)

2026-11-19 核对国内渠道 LCSC C443639，准确料号有目录并给价，库存字段为 **0**。DigiKey 美国页面切带及公开库存提供跨境候选证据。国内可交付的库存、到手价格和批次均保持 UNKNOWN。 [LCSC](https://www.lcsc.com/product-detail/C443639.html) · [DigiKey](https://www.digikey.com/en/products/detail/diodes-incorporated/MMDTA42-7-F/1935163) · [快照](evidence/lcsc_public.json)
