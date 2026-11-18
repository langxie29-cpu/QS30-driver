# 原厂资料核验入口

日期2026-11-18。所有下载成功/失败、URL、SHA见source_register*.json；下载成功不等同电气资格。PDF/模型原件不随Git分发。下列仅列实际已取得的资料。

|资料|原厂入口|SHA256|
|---|---|---|
|C3D04065A_alt|[C3D04065A_alt](https://assets.wolfspeed.com/uploads/2023/11/Wolfspeed_C3D04065A_data_sheet.pdf)|35e1d2fb53f44dc8909300549ddd391ef9143588282a573e44258dfdea04b6cf|
|LM5069|[LM5069](https://www.ti.com.cn/cn/lit/ds/symlink/lm5069.pdf)|d60d8106a6e8113900ff8b9576dd959942fa7169742baf0beeb30684d4d64681|
|LM5164|[LM5164](https://www.ti.com.cn/cn/lit/ds/symlink/lm5164.pdf)|863a4e9bf023f018c57e5ce7cb6a7697e78a7e489c3fdb750bf83dfe6dcd579f|
|MSS1583|[MSS1583](https://www.coilcraft.com/getmedia/fbfe8ea7-f5d8-4484-859e-2285f427326d/mss1583.pdf)|dba193babcbf95881cc8995479ca6e99bb7ad9a431f2d6e8ce8a893cf2802d3f|
|NTC_retry|[NTC_retry](https://www.vishay.com/docs/29049/ntcle100.pdf?R4=1)|f9d6153738198dc705ed681c3b55e70a6571f8fee13a4ed7b2b41e49973cb9c9|
|REF34|[REF34](https://www.ti.com.cn/cn/lit/ds/symlink/ref34.pdf)|bc3198207e01332033895f6450e4c6504166da274f3adfb5a350f430d14492fb|
|SN74HCS02|[SN74HCS02](https://www.ti.com.cn/cn/lit/ds/symlink/sn74hcs02.pdf)|671658ecff74a0182c89fee6b50d855705e07ec0e05a54881aa44fe13daa87a4|
|SN74HCS08|[SN74HCS08](https://www.ti.com.cn/cn/lit/ds/symlink/sn74hcs08.pdf)|a6bd1cb6e9538318a361a8c309bbc8302763070f9f1d68beb5c8431644d2c893|
|SN74HCS14|[SN74HCS14](https://www.ti.com.cn/cn/lit/ds/symlink/sn74hcs14.pdf)|992e650f776ed20af6e19fde3ac7f7b83c1c4f9e3ba7f6af9687562b1a5eee69|
|SN74HCS74|[SN74HCS74](https://www.ti.com.cn/cn/lit/ds/symlink/sn74hcs74.pdf)|2de4fe537d630fadebea78908e7aed2dbec75cfb21254b38b75046086c1353bc|
|STPSC4H065|[STPSC4H065](https://www.st.com.cn/resource/en/datasheet/stpsc4h065.pdf)|559c799c3dae7539534ba98ec89b8b340bff7194b9c42af8d3a4be780f4c7fdb|
|TDK_B32774_retry|[TDK_B32774_retry](https://www.tdk-electronics.tdk.com/inf/20/20/db/fc_2009/MKP_B32774_778.pdf)|b8a44719820daedb6b30cd5c6d87ec443da1050d6538578c13b14d38c2de0802|
|TLV1704|[TLV1704](https://www.ti.com.cn/cn/lit/ds/symlink/tlv1704.pdf)|8739e728c99f32803300a9c6beb90c4e98406d23791378715ccda059f03655bb|
|TPS3808|[TPS3808](https://www.ti.com.cn/cn/lit/ds/symlink/tps3808.pdf)|57e5f36071693b7a3e0713f199b076c472b052e417cf660e6a23a47bb6da84c7|
|TPS7A16|[TPS7A16](https://www.ti.com.cn/cn/lit/ds/symlink/tps7a16.pdf)|180ec3f485b2772b09be0cfdc81deb13b94a9d558707d7e7a94886d475896ce8|
|UCC27511|[UCC27511](https://www.ti.com.cn/cn/lit/ds/symlink/ucc27511.pdf)|ed6d733abadc425756715ffcf20d9260fa02e5ddbf11581dd2a57a65f90517cf|
|VOS618A|[VOS618A](https://www.vishay.com/docs/83465/vos618a.pdf)|61d948c9edadff66dad1bfc49f8ae17f2258b25ee15af8509d0361e218a9971a|

## 关键审查依据

LM5069：电气特性MIN/TYP/MAX与测试条件，非仅典型波形；LM5164/UCC27511/TPS7A1601/TPS3700/TPS3808/HCS74/14/08：物理针脚和电源范围。TDK B32774D：准确450V10µF条目、105°C降额、70°C10kHz纹波/典型ESR/ESL与机械表。Coilcraft MSS1583：25°C降感定义、DCR与温升电流，未给出本项目完整热态故障资格。
原R3已冻结的ADI LT3757A RevH、ST STP9NK50Z、TPS26601/Vishay US1G/SS14来源及逐针资料继续使用，不伪称本轮重新下载全部。详见R3 MODEL_CREDIBILITY、R1 CONTROLLER_REVIEW及源登记。ST原始宏模型头明确仅25°C，不能给热态SOA资格。
SiC仅深入STPSC4H065D与C3D04065A；较早C3D02060F/STPSC2H065D经生命周期筛掉，未进入四候选深挖。ST原厂v13库完整原字节SHA见ST_model_acquisition*.json与每次preregister。ST模型没有BV/雪崩，不以其低反压数值推断实体雪崩安全。
当前供应商快照单独见verified_cap_supplier.json。厂家产品页403、初始TLS、错误大小写URL404均保留；失败不能改写为已核实。
