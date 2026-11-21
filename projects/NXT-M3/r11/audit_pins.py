"""Verify the preserved logical pin map against a fresh KiCad XML export."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def pins(file):
    return {(node.get("ref"), int(node.get("pin"))): net.get("name")
            for net in ET.parse(file).findall("./nets/net") for node in net.findall("node")}


reference = pins(HERE / "evidence/r0/netlist.xml")
current = pins(Path(sys.argv[1]))
assert current == reference, "R11 pin-level netlist changed"
for bit in range(30):
    tube, digit = divmod(bit, 10)
    bank, output = divmod(bit, 8)
    drive, base, cathode = f"DRV_{bit:02}", f"BASE_{bit:02}", f"K{tube+1}_{digit}"
    assert current[(f"U{20+bank}", (15,1,2,3,4,5,6,7)[output])] == drive
    assert [current[(f"Q{bit+1}", pin)] for pin in (1,2,3)] == [base, "GND", cathode]
    assert [current[(f"R{100+bit}", pin)] for pin in (1,2)] == [drive, base]
    assert [current[(f"R{200+bit}", pin)] for pin in (1,2)] == [base, "GND"]
    assert current[(f"V{tube+1}", (3,13,12,11,10,9,7,6,5,4)[digit])] == cathode
for bank in range(4):
    assert current[(f"U{20+bank}", 13)] == "HC_OE_N"
    if bank:
        assert current[(f"U{19+bank}", 9)] == current[(f"U{20+bank}", 14)] == f"SER{bank}"
for pin in (6, 7):
    assert current[("U23", pin)].startswith("unconnected-")
print(json.dumps({"pin_net_entries": len(current), "changed": 0, "cathode_paths": 30,
                  "spare_outputs_nc": 2, "logical_socket_pins_only": True}))
