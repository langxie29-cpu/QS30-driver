# R8 Gate 0 cutoff timing challenge

Return at most 260 English words, 5 numbered bullets, no repeated input. Independent engineering evidence only. Use no tools, no commands, no proposal to energize hardware or manufacture, and no G1 approval. Review one held 3.3 V/170 V candidate and explicitly label unsupported bounds.

1. Series resistor from logic output to base node, separate pull-down from that node to emitter. Use KCL at the node, not a series sum. Independently verify net base current for 3.0k/10k with ±1%, VOH=2.4 V, VBE=1.0 V, and compare to 0.33 mA. State how valid logic power and down-ramp assumptions affect that result.
2. MMDTA42 DS30438, 300 mW/417 C/W on a specified board, Tj max 150 C. Possible sustained half-on fault, isolated source, 195 V initially on 5.5 µF, 19.8k anode in series with fixed 19.8k resistive BJT analog, two 502980 ohm bleed branches. An independently run passive LTspice result is ~45.17 mJ in the analog over 1 s, 0.221788 s to 60V with that fault path, 1.63031 s for a disconnected reservoir with only both bleed branches. Explain the difference between deenergizing the converter upstream and breaking the stored-capacitor load path.
3. Test if increasing the tube anode resistor alone could satisfy the 85 C steady 155.875 mW thermal screen and the nominal 1.5 mA minimum at 170 V, 125 V tube sustain assumption. Give numbers. No credit for unprovided transient SOA.
4. Identify the most important electrical counterexample to using a module supply current threshold alone, and the minimum evidence to accept the cutoff/retained bleeder concept.
5. Given hot leakage and low-current full-temperature saturation are still unknown in the cited datasheet, state the nearest offline engineering gate with a measurable criterion; distinguish proof from model sensitivity.

