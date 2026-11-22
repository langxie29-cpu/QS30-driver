## 采购/BOM 边界审计（仅据节选）
- 范围：R13 BOM 可见 A（HV_STAGE）与 D（M3_NON_HV/CASH_ONLY）行；输入 BOM 省略中间行，不能证明全表完整。
- 单模块/三模块数量：A 行 Qty=3 可归一为 1/模块；D 的 TUBE-1..3 Qty=9（3/模块）、OLED-PANEL 与 FASTENERS-AND-WIRE Qty=3（1/模块）；CASH_ONLY 各 Qty=3，但未定义按模块还是整批。数量仅为边界，不产生价格。
- 报价缺口：A/D 可见行 Unit Price、Quote Date、MOQ 均空，Verification Status=UNQUOTED；无正式报价、数量档、交期、税/运、有效期。
- 报价观察：2026-11-22 仅有单件公开快照——C LT3757EMSE#PBF ¥62.77000@1（库存1,436）；B LM3488MM/NOPB ¥28.37000@1（2件），LM3488MMX/NOPB ¥24.15000@1（0件）；均非篮子/税/运报价。A UCC3803DTR 无已验证 CNY 档；¥14.93 关联 UCC3803D 且来源不全，不可采用。D LM5155DSSR 档位未开。
- 过时/受限：R14.5 改外置管座、删除 6×Ø3.5 mm 孔及禁布区、V1–V3 改 B.Cu 线束焊盘、33 端点；R13 BOM 的 6×Ø3.5 mm holes 机械描述已过时。C DA2032-ALB 被 Mouser 标受限，厂家列 DA2032-ALD；供应/引脚/报价未闭。
- MOQ/库存：MOQ-OVERBUY 为 TBD/UNQUOTED，未计算超采现金。TUBE 仅 R10 owned pool 提示，无可用数量/状态/估值；OLED R10 ¥9.78 仅历史；其他库存未核。
- 成本结论：单模块与三模块均只能界定数量/范围，不能给出材料或现金总成本；CASH_ONLY 服务（PCB、SMT、钢网、运税、手装、MOQ 超采）均需同批报价。R14.5 无成本证据且 MANUFACTURING_RELEASE=HOLD。
- 下一门证据：R14.5 对齐 BOM/AVL；逐 MPN 正式报价（日期、币种、数量档、MOQ、交期、税运、有效期、库存）；自有库存台账与可用量；单模块/三模块 rollup；服务同批报价与超采计算。
