# 供应与真实核价

本轮以原生 BOM 对库存、MOQ、包装倍数和公开阶梯。立创全球站公开 SSR 字段通过 SKU 与 MPN 双匹配，保留读取时间和页面哈希。美元报价原币比对，国内历史 CNY 规划以引用保存。物流、含税、帐号地区及型号价格未闭合时填 UNKNOWN。 [LCSC 原始字段](evidence/lcsc_snapshot.json) · [立创数量档](LCSC_PRICE_EVIDENCE.csv) · [辅助渠道](SUPPLEMENTAL_PRICE_EVIDENCE.csv) · [逐数量下单口径](evidence/order_lines.csv)

- LCSC 的 STP9NK50Z 当前只有 2，三块须换渠道。本轮可见 DigiKey 公告库存，但商品页是缓存快照，必须在后续采购审批时重核实际库存与交期。STPSC4H065D、TMR 1-1212、HV5622PG-G 在已核渠道分别有缺货，现有 BOM 无法形成完整购物篮。
- TMR 1-1212 的 9–18 V 输入和稳压 12 V/83 mA 模块同时给 U5、U11、U12 供电。板上输入、输出负端都接 GND，隔离规格未构成模块内部安全隔离。TPS552872RYQR 可研究 12 V 经过低线和跨压两种状态，仍需轻载纹波、启动/掉电开断、反灌、地弹与布线。QFN、外围磁件和追加装配一起核算。LCSC 的 TMR $14.1178 是缺货参考，Newark 公告 $11.25 起并给交期，不能与替代 IC 单价差直接报节省。 [Traco](https://www.tracopower.com/products/tmr1.pdf) · [TI](https://www.ti.com/lit/ds/symlink/tps552872.pdf)
- HV5622PG-G 为已审针脚的三位静态基准。DigiKey 公告 PG $8.81，PJ $8.32 且所查页缺货，三块差额只有 $1.47 的器件参考值。PJ 为 44-PLCC，需独立 pin map、焊盘与装配，不能并用 PQFP 座。¥8.45 传闻无可验证的准入/到手条件，台账没有把它纳入报价。其他 32 路器件涉及极性、空白及有效耐压，尚未证明 PG 的绝对最低价。 [Microchip](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/20005854A.pdf)
- 电感 12×12 mm 候选 DCR 与饱和曲线不同。保留 MSS1583-154KED 对照，优先测绕组热态、L(I,T) 和实际波形磁芯耗散。更小 SiC 并无可购优势证据。STTH1R06U 600 V 量级价格有吸引力，需完成真实热态恢复和漏电/过冲审查。4.7 µF 电解的最低 3.76 µF、极性和高频有效 ESR 对启动贡献不同，不能沿用薄膜结果。负载电流与 100 kHz 脉冲 RMS 分开，寿命按热点及实际纹波频谱评估。 [器件矩阵](COMPONENT_SUBSTITUTION_MATRIX.csv)
- 裸板、SMT、THT、低压连接、外壳、外部电源、工装、返板和备件分项为 UNKNOWN。1/3 板的辉光管来自已有资产，5/10 完整装填分别还需 6/21 只。历史九只合计 ¥160 的购入记录与替换价值口径分开，现行替换值 UNKNOWN。全套成本按一种 PCB 设计计价。
