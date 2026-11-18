# 复现与工程入口

1. 打开 [NXT-M3.kicad_pro](NXT_M3_R7_EDA/NXT-M3.kicad_pro)，或用 KiCad 10.0.8 从原理图导出 XML 和 BOM。 [根图](NXT_M3_R7_EDA/NXT-M3.kicad_sch)
2. 从 R7 目录运行以下命令。KiCad CLI 在 Windows 可从安装目录直接调用。

~~~text
python NXT_M3_R7_EDA/generate.py
kicad-cli sch export netlist --format kicadxml -o evidence/native.xml NXT_M3_R7_EDA/NXT-M3.kicad_sch
kicad-cli sch erc --format json --exit-code-violations -o evidence/erc.json NXT_M3_R7_EDA/NXT-M3.kicad_sch
kicad-cli sch export bom -o evidence/native_bom.csv --fields Reference,Value,Footprint,MPN,Status,DNP,QUANTITY --labels ref,value,footprint,mpn,status,dnp,quantity NXT_M3_R7_EDA/NXT-M3.kicad_sch
python NXT_M3_R7_EDA/audit.py
python budgets.py
python procurement.py
python cost.py
python final_audit.py
~~~

3. 原生 LTspice 引擎、四份 R6 原厂模型从 [R6 复现](../r6/REPRODUCE.md) 获取。设 NXT_LTSPICE 和 NXT_R4_MODELS，在 R7 目录运行以下命令。比对日志、注册窗口、输入哈希和原始波形摘要。

~~~text
python UNIFIED_POWER_MODEL/run.py evidence/runs/exact/circuit.cir path/to/new_dir --timeout 260 --purpose "R6 exact reproduction"
~~~

4. 先运行 UNIFIED_POWER_MODEL/fetch_ti.py 下载 TI 原始模型，使用源哈希复查传输。再运行 UNIFIED_POWER_MODEL/translate_ti.py，将相应 --lib 指向临时路径原厂或适配文件，用每份 [运行收据](evidence/runs/) 的哈希识别。TPS26600 的 PSpice 加密包留待相应工具。适配包括 ABM 表达语法、内部子电路名、字节标记、厂商表括号与 UCC28C43 单位增益支路命名，不重写控制规律和额定参数。
5. UNIFIED_POWER_MODEL/collect.py 从执行主机临时目录生成验收摘要。小型证据提供原始压缩波形，较大波形用 SHA 和指标复验，原始文件在执行机。程序退出、波形有效与电气资格独立审查。对转换中间版用已封存的执行 deck 和该次库 SHA，当前生成器输出最终候选。
6. 低压协议使用 [R6 默认固件](../r6/FIRMWARE_PROTOTYPE/)，重新执行的程序及结果在 [软件回归](evidence/firmware_check.txt)。
