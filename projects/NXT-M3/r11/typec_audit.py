"""Independently verify the Type-C digital gates and legacy pin-net preservation."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE/"evidence/typec/final"


def by_pin(source):
    return {(node.get("ref"),node.get("pin")):net.get("name")
            for net in ET.parse(source).findall("./nets/net") for node in net.findall("node")}


def main():
    baseline=by_pin(HERE/"evidence/r5/native_netlist.xml")
    actual=by_pin(OUT/"native_netlist.xml")
    old={key:net for key,net in baseline.items() if key[0]!="J1"}
    change={key:(net,actual.get(key)) for key,net in old.items() if actual.get(key)!=net}
    assert not change,change
    expected = {
        "J1":{"A9":"5V_RAW","B9":"5V_RAW","A12":"GND","B12":"GND","SH":"GND","A5":"USBC_CC1","B5":"USBC_CC2"},
        "U26":{"1":"USBC_CC1","2":"USBC_CC1","4":"USBC_CC2","5":"USBC_CC2","16":"USBC_VALID_N",
               "18":"USBC_VS","20":"USBC_3A_N","21":"USBC_1V2","22":"GND","23":"USBC_2V7",
               "24":"5V_RAW","25":"GND"},
        "Q33":{"1":"USBC_VALID_N","2":"GND","3":"FRONT_EN"},
        "Q34":{"1":"USBC_3A_N","2":"GND","3":"FRONT_EN"},
        "F1":{"1":"5V_RAW","2":"5V_FUSED"},
        "U1":{"1":"FRONT_EN","5":"5V_FUSED","6":"5V_PROT"},
        "R40":{"1":"5V_PROT","2":"HV_ISOLATE_IN"},
    }
    for ref,pins in expected.items():
        assert all(actual[(ref,pin)]==net for pin,net in pins.items()),ref
    result={"unchanged_pre_eco_pin_entries_excluding_j1":len(old),"typec_pin_checks":sum(map(len,expected.values())),
            "matched":True,"expected":expected}
    (OUT/"typec_pin_audit.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["unchanged_pre_eco_pin_entries_excluding_j1"],"unchanged pin-net entries; Type-C checks passed.")


if __name__=="__main__":
    main()
