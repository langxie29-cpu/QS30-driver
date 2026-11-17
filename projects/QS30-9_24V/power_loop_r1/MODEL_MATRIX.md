# QS30-9 模型兼容性与可信度审查

2026-11-17，Codex独立审查。下表的LIMITED_PASS只覆盖明确夹具，不作型号、热态或硬件资格。原模型均保留原字节；SHA完整值见worker model_index、独立preregister及封存manifest。

|器件/模型|可追溯原件|本地引擎与实证|可信范围/结论|
|---|---|---|---|
|LT3757AIMSE#PBF / LT3757A.sub|ADI签名LTspice24.0.12.0的lib.zip，SHA256 `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634`|原生LTspice；原厂12→24V参考的单位编码修正派生网表完成1.5ms，均值23.960860V、峰24.390367V|**LIMITED_PASS：原生控制器与低压参考可执行**。模型编码/不透明，不能审查内部实现或外推硅片角点；不是170V验证|
|LT3757A原厂参考图|examples.zip内原图SHA `867ea5d1f8f90aa56f4dacfadfa4108bfddf0e619c06941bb711d890dba40cb6`|直接-b ASC超时；原生-netlist成功，但四个µ后缀被ACP936写成A6CC，未修正网表只输出88µV；四处改ASCIIu后24V工作|初始错误属**EXECUTION_FAIL/编码**，拒绝worker关于原厂电路/控制器失效的结论。原图/失败网表/波形不覆盖。修正派生网表不得标成字节未改原件|
|UCC28C43DR / TI加密PSpice|slum033库SHA `546fab4c7b9208394122f7f4e886496d15e2811af37b4e32cb9edff2eddeaadd`|没有Cadence PSpice；不能用LT/NG读取加密库|**INCONCLUSIVE**：原生环境缺失；只对该库/该引擎配对可称MODEL_FAIL，不据此说芯片失败|
|UCC28C43 / TI TINA|slum178启动库SHA `7b00c5326308d7203d75fa0e77870ed0dd2482305199f88eff67682827d9526a`|没有TINA-TI；加密|**INCONCLUSIVE**，未原生回放|
|UCC28C43未加密PSpice|TI slum521，SHA `ab3cd5bb484570e3e719d7f1d1a5dcf9e0ef48161a9d00eaa84d34dcf5ec26b8`|NGspice47兼容模式的派生夹具；不是原生PSpice。初次导出脚本fourier函数/变量错误，日志仍显示200255点、9ms终点|不能由VALUE语法文字判断“必需改29处”，也不能由rc0认定波形合格。最终采信范围须以worker归档后的原raw独立检查为准|
|STP9NK50Z|ST原厂level3库SHA `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4`|旧LT独立器件/强制CS单元有限通过；本轮原字节参与被动充电与真实控制器启动|**25°C典型模型限定**。内部LG/LS/LD已存在，不能重复添加后误认为实测寄生。历史高频/采样收敛失败仍有效；不获热态资格|
|US1G-E3/61T|Vishay us1g.txt SHA `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3`|原字节LT可执行；含TT=123.315ns及CJO等结电容参数|不是“只有IS/N、无动态”的模型。TT不等于trr；旧50.353ns夹具与实际原厂trr条件/全温吻合仍未通过。不能直接断言准确Qrr|
|SS14负栅钳位|历史SS14原库，登记哈希并逐例校验|独立夹具内可执行|第三方/随包来源与准确厂商、动态、温度适用性未完全资格化；**INCONCLUSIVE**，只作钳位研究模型|
|MSS1583-154KED|S06已替代旧MSS1260；150µH±10%、DCR max159mΩ、25°C/10%降感3.1A|本轮150µH、显式Rser=.16Ω的线性近似；无原厂热态L(I,T)/磁损SPICE|**INCONCLUSIVE**。不是完整磁件模型。快输入被动充电预测超过3.1A，超出线性可信范围。不得把旧MSS1260参数登记为现用器件|
|SiHP8N50D-GE3|原厂Rev.B模型已在历史库|旧Qg拟合窗未通过，100°C亦有求解失败|不采纳为修复ST问题的快捷替代，不放宽旧12nC下界|

软件与原库许可文件保持本地。GitHub交付生成的研究网表、运行日志、波形、参数、hash及提取方法；不打包模拟器安装包、可执行文件或整套原厂库。原模型在忽略目录及本机既有source中原样保留。

原厂入口：[ADI LT3757A](https://www.analog.com/en/products/lt3757.html)、[ADI数据手册](https://www.analog.com/media/en/technical-documentation/data-sheets/LT3757-3757A.pdf)、[TI UCC28C43](https://www.ti.com/product/UCC28C43)、[TI未加密包](https://www.ti.com/lit/zip/slum521)、[Vishay US1G模型](https://www.vishay.com/docs/88194/us1g.txt)、[Coilcraft MSS1583](https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/mss/mss1583/)。这些链接说明来源；性能采信仍按本地登记版本及实际波形。
