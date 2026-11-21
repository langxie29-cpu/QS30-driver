"""Apply R11 project naming and provisional netclass assignments to an R10 copy."""
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PROJECT = HERE / "eda" / "NXT-M3-R11.kicad_pro"
POWER = {"5V_RAW", "5V_FUSED", "5V_PROT", "5V_HV", "HV_ISOLATE_IN", "LV_SW"}
SAFETY = {"ARMED", "ARM_STROBE", "FAULT_N", "BIAS_OK", "DRIVE_OK", "PWM_PERMIT",
          "HC_OE_N", "HC_CLEAR_N", "RESIDUAL_OK", "HV_READY", "LATCH_CLR_N", "MCU_EN",
          "HV_ISENSE", "CS_FILT", "OCP_REF", "HV_UVLO", "HV_CS", "REF_1V25", "WDI"}


def classify(net):
    if net in POWER or net in {"3V3", "OLED_3V3", "GND", "GATE_BIAS"}:
        return "LOW_VOLTAGE_POWER"
    if net in {"SW_HV", "SNUB"}:
        return "POWER_SWITCH_NODE"
    if re.fullmatch(r"K[123]_[0-9]", net):
        return "HIGH_VOLTAGE_CATHODE"
    if net == "HV_BUS" or net.startswith(("ALIM_", "ANODE_", "BLEED_")):
        return "HIGH_VOLTAGE_BUS"
    if net.startswith(("HV_FB", "HV_OVP_S", "HV_RES_S")):
        return "HV_FEEDBACK"
    if net in SAFETY:
        return "SAFETY_CONTROL"
    return "DIGITAL_SIGNAL"


def main():
    for sch in PROJECT.parent.glob("*.kicad_sch"):
        before = sch.read_text(encoding="utf-8")
        after = before.replace("NXT-M3-R10", "NXT-M3-R11").replace("R10 engineering HOLD", "R11 engineering HOLD")
        after = after.replace("GATE_0 = REWORK     ENGINEERING_RELEASE = HOLD     R40 OPEN DNP",
                              "R11     GATE_0 = REWORK     ENGINEERING_RELEASE = HOLD     R40 OPEN DNP")
        if after != before:
            sch.write_text(after, encoding="utf-8", newline="\n")
    names = sorted(n.get("name") for n in ET.parse(HERE / "evidence/r0/netlist.xml").findall("./nets/net")
                   if not n.get("name").startswith("unconnected-"))
    default = {"name": "Default", "clearance": .2, "track_width": .2, "via_diameter": .6,
               "via_drill": .3, "microvia_diameter": .3, "microvia_drill": .1,
               "diff_pair_width": .2, "diff_pair_gap": .25, "diff_pair_via_gap": .25,
               "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
               "wire_width": 6, "bus_width": 12, "line_style": 0}
    dimensions = {"LOW_VOLTAGE_POWER": (.2, .50), "DIGITAL_SIGNAL": (.2, .20),
                  "HIGH_VOLTAGE_BUS": (2., .40), "HIGH_VOLTAGE_CATHODE": (2., .25),
                  "HV_FEEDBACK": (.2, .20), "POWER_SWITCH_NODE": (3.2, .50),
                  "SAFETY_CONTROL": (.2, .25)}
    classes = [default] + [dict(default, name=name, clearance=gap, track_width=width, priority=i)
                          for i, (name, (gap, width)) in enumerate(dimensions.items())]
    project = json.loads(PROJECT.read_text(encoding="utf-8"))
    project["meta"]["filename"] = PROJECT.name
    project["net_settings"] = {
        "meta": {"version": 4}, "classes": classes, "net_colors": {},
        "netclass_assignments": {},
        "netclass_patterns": [{"pattern": net, "netclass": classify(net)} for net in names]}
    PROJECT.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
