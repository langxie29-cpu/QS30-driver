# R8 Gate 0 device evidence challenge

Perform one independent, source-bounded engineering review. Treat all conclusions as worker claims. Use only the quoted primary evidence and fixed product scope below. No tools, file operations, purchases, energized testing, manufacture or design approvals. Report in concise Markdown with four named sections: verifiable facts, contradictions, smallest rework requirements, remaining unknowns. Mark every guarantee as a test-conditioned statement. Give arithmetic with units. Cite only URLs below. Do not invent vendor guarantees, dates, SPICE runs, stock or costs.

Fixed product: nine QS30-1, 30 static cathodes per same-architecture STM32C011/RS-485 independent module. 170 V nominal, 195 V fault screen. Each tube has intact 20 kΩ reference anode limiting (19.8 kΩ at 1% low). Three-board topology and independent hardware HV inhibit retained.

Diodes DS30438 Rev 5-2 pp1–3 (https://www.diodes.com/datasheet/download/MMDTA42.pdf): MMDTA42-7-F dual NPN in SOT26. VCEO/VCBO 300 V, VEBO 6 V. 300 mW and 417 C/W on defined board; maximum Tj 150 C. Table at 25 C, short pulses: hFE minima 25 at 1 mA, 40 at 10/30 mA, VCE 10 V. Max VCE(sat) 0.5 V and VBE(sat) 0.9 V at IC20 mA/IB2 mA. ICBO max 100 nA at VCB200 V, IE=0; Ccb max 3 pF at VCB20 V. Figure 2 is typical saturation at forced beta 10. No specified dual-die linear SOA or hot ICBO guarantee in this table.

TI SN74HC595PWR (https://www.ti.com/lit/ds/symlink/sn74hc595.pdf) has unloaded VOH table at 2/4.5/6 V and heavy-load data at 4.5/6 V. TI SN74LVC595APWR SCASE93A §5.5 (https://www.ti.com/lit/ds/symlink/sn74lvc595a.pdf) has at VCC3.0 V and IOH −12 mA VOH ≥2.4 V; at VCC0 Ioff 10 µA, powered IOZ 15 µA under listed conditions. /OE is high-Z gated; /SRCLR clears shift stage; separate RCLK needed.

Existing screens: HC 10k+22k, ideal VOH 3.3 V and assumed VBE 0.9 V -> nominal net IB 0.199 mA. LVC 3k+10k 1%, case VOH 2.4 V VBE assumed 1.0 V -> min net IB approx 0.361 mA. Previous 22k pull-down plus 15 µA IOZ and 0.1 µA ICBO exceeded 0.30 V research screen. 10k pulldown gives 0.2525 V with 15 µA IOZ plus assumed 10 µA ICBO, without PCB leakage. At 195 V and one shorted tube anode, 19.8 kΩ intact gives a worst linear load-line peak 480 mW at ~97.5 V and 4.92 mA.

Challenge whether the new circuit is still a credible research candidate. Check sat/thermal asymmetries, hot false ignition, supply ramp/backfeed between logic and HV, and distinguish datasheet claim from analytic envelope. Identify what a low-voltage fixture can genuinely validate. Give any useful numerical counterexample. Do not infer authorization or promotion to G1.

