# S06B 精确来源和资格矩阵

2026-11-15。文件哈希见同目录manifest；下载原始元数据见 `../../sources/sprint06b/manifest.json`、`interface_sources.json` 和各source.json。精确MPN仍继承S05/S06；本表只记录本轮增量。

|精确对象|原厂来源与本地证据|本轮范围|仍不具备的资格|
|---|---|---|---|
|STP9NK50Z|[ST模型](https://www.st.com.cn/resource/en/spice_model/stp9nk50z_spice.zip)、[PDF](https://www.st.com.cn/resource/en/datasheet/stp9nk50z.pdf)；`sources/sprint06b/ST_model_cn/`、`ST_pdf_cn/`|原字节25°C模型，D/G/S端口适配；静态单元可执行；独立与联接瞬态失败|瞬态步长、Miller/Coss、热态、损耗/SOA|
|US1G-E3/61T|[Vishay模型](https://www.vishay.com/docs/88194/us1g.txt)；`sources/sprint06b/Vishay_US1G/`|原厂US1G电气模型用于该系列订货码；VF及反偏DC单元|反向恢复、温度/公差；模型不区分包装后缀|
|Diodes US1G|[Diodes模型](https://www.diodes.com/spice/download/722/US1G.spice.txt)；`sources/sprint06b/Diodes_US1G/`|仅保留取得记录|不同厂，不替代Vishay；未执行为候选资格|
|UCC28C43DR|[TI SLUM521](https://www.ti.com/lit/zip/slum521)；沿用`sources/sprint06/`原模型|独立与实际端口负载诊断可执行；联接失败|真实负载/跨模式/全温和闭环|
|UCC27511DBVR|[TI SLUM488](https://www.ti.com/lit/zip/slum488)；沿用S06原件及括号修正副本|1ns三次重放可执行；跨引擎联接失败|崩溃根因、联接及真实栅回路|
|MSS1583-154KED|[Coilcraft PDF](https://www.coilcraft.com/getmedia/fbfe8ea7-f5d8-4484-859e-2285f427326d/mss1583.pdf)；`MSS1583_current/`|DCR/25°C饱和来源复核；100°C铜电阻仅近似|热态L(I)、频率/磁损、实物温升，未替换或放行|
|TPS26601RHFR|[TI反接接口报告](https://www.ti.com/lit/an/slva934a/slva934a.pdf)；`TPS2660_fault_handling/`；加密模型仍在S06|识别并撤回RTN跨域直连/FLT直接上拉资格|动态/SOA、隔离接口、掉电/反接序列|
|VOS618A-7T|[Vishay PDF](https://www.vishay.com/docs/83465/vos618a.pdf)；`VOS618A/`|SHDN信号域隔离具体连接与25°C静态分配候选|热态CTR/漏电、关断最大延迟；非快速限流器|
|TPS389001DSET|[TI PDF](https://www.ti.com/lit/ds/symlink/tps3890.pdf)；沿用S06|明确18µs典型条件及掉电反例|快速跌落、半供电与最大断言延迟|
|ESP32-S3-WROOM-1/1U|[Espressif PDF](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)；`ESP32_S3_WROOM/`|供电能力≥0.5A要求；不是实际启动轨迹|具体存储变体/ROM下载/枚举/挂起实耗|
|FT231XS-R|[FTDI PDF网页](https://www.ftdichip.com/wp-content/uploads/2025/06/DS_FT231X.pdf)；`FT231X/source.json`记录本地403|仅离线UART编程拓扑备选，PWREN#配置后许可思路|本地归档、完整引脚、桥电流/电源开关/时序/反灌；尚未采用|

路径简写均相对于项目根目录。没有将任何新候选导入原生图或制造BOM。
