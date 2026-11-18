# 复现索引

- 基线 [BASELINE.md](BASELINE.md)，本轮新内容限制在 projects/NXT-M3/r6。
- 原生 KiCad 10.0.8，打开 [NXT-M3.kicad_pro](NXT_M3_EDA/NXT-M3.kicad_pro)。原理图源 [NXT-M3.kicad_sch](NXT_M3_EDA/NXT-M3.kicad_sch)，层级文件在同一目录，域间用全局标号、电气导线和明确的 NC。建议改生成器再生成，或直接编辑 KiCad 源后同步生成依据。
- 在 R6 根目录中运行 `python NXT_M3_EDA/generate.py`。执行 `kicad-cli sch export netlist --format kicadxml -o evidence/native.xml NXT_M3_EDA/NXT-M3.kicad_sch`、`kicad-cli sch erc --format json --exit-code-violations -o evidence/erc.json NXT_M3_EDA/NXT-M3.kicad_sch`、`kicad-cli sch export pdf --output evidence/NXT-M3.pdf NXT_M3_EDA/NXT-M3.kicad_sch`。随后 `python NXT_M3_EDA/audit.py`，非默认路径用 `--footprints`。查看 [真实导出](evidence/native.xml) 和 [ERC](evidence/erc.json)。
- LTspice 24.0.12 Windows。设 `NXT_LTSPICE` 为可用 exe；`NXT_R4_MODELS` 指向含四个源模型的目录。R4 历史大模型许可和来源见 [R4 REPRODUCE](../../QS30-9_24V/power_loop_r4/REPRODUCE.md)。根据 [各次 preregister](LTSPICE_MODEL/runs/) 校验模型 SHA 并按目录模型名放置。电路模板和每次实际 `.cir` 都已保存。新运行示例 `python LTSPICE_MODEL/run.py warm_load --output .local/check_warm`，目的地必须不存在。用既有测量摘要，不主动重耗预算。源模型、工具程序和凭据不上载。
- 小 `.raw` 分卷在 Git；大分卷在 [GitHub 草稿档](evidence/large_raw_archive.json) 依权限可见。下载该清单中相应 case 的全部分卷，去除上传名称的 case 前缀，将 `boost.raw.partXX.gz` 与该 case 的 `result.json` 放一起。运行 `python LTSPICE_MODEL/restore.py CASE_DIR NEW.raw`，校验每卷 SHA、总长度与原始 SHA。主控保留本机原始件。 `python LTSPICE_MODEL/summarize.py --verify` 在有全部分卷的环境复核。
- 低压协议 `python FIRMWARE_PROTOTYPE/host_packet.py 123456789 --mask 7 --seq 41 --output example.bin`。任意标准 C11 构建器可跑 `nxt.c test.c`。本次签名过的 Espressif GCC 加 Unicorn RV32 实际运行，`python -m pip install unicorn==2.1.4 pyelftools==0.33`，再 `python verify_firmware.py --gcc GCC_EXE --clang CLANG_EXE`。STM32 源仅通过目标语义检查，复现 ARM 候选链接须用具有 ARM 后端的 clang/lld 或另一个官方 ARM 工具链。没有 MCU 烧录。
- 成本 `python procurement.py`（历史和本次固定公开快照）及 `python cost_model.py`（计划算式）。电源角点 `python power_corners.py`。审查收据 [目录](evidence/)，费用标为 UNKNOWN。制造、PCB、SMT、实物高压与采购依旧 HOLD。

- 已恢复/存在相关本地 raw 时，执行 python LTSPICE_MODEL/partial_windows.py，产生证据窗采样摘要。四个窗口用于描述收敛途径，原预注册门槛仍由各运行的 preregister.json 控制。
