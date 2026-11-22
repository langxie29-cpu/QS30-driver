"""Build per-pair clearance qualifications from both raw native DRC reports."""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from build_board import HERE, BASE, STEM, SOURCE_STEM
from route_board import BoardRouter, LAYERS, copper
from verify_board_r146 import csv
from verify_board import classify, descriptor, drc_distances, drc_key


TI = {
    "U1": ("RPW0010A", "https://www.ti.com/lit/ds/symlink/tps25947.pdf"),
    "U11": ("RPW0010A", "https://www.ti.com/lit/ds/symlink/tps25947.pdf"),
    "U6": ("DGK0008A", "https://www.ti.com/lit/ds/symlink/tca9517a.pdf"),
    "U13": ("DGK0008A", "https://www.ti.com/lit/ds/symlink/tlv1701.pdf"),
    "U14": ("DGK0008A", "https://www.ti.com/lit/ds/symlink/tlv1701.pdf"),
}
MMBTA42 = "https://datasheet.lcsc.com/lcsc/2208091800_Shandong-Jingdao-Microelectronics-MMBTA42_C4749118.pdf"
FAB = "https://jlcpcb.com/capabilities/pcb-capabilities/"


def logic_nominal(ref, net):
    fixed = {"GND": (0., 0.), "3V3": (3.3, 3.3), "REF_1V25": (1.25, 1.25),
             "HV_OVP_S": (0., 170*13.3/(4*499+13.3)),
             "HV_RES_S": (0., 170*42.2/(4*453+42.2))}
    if net.startswith("unconnected-"):
        return None
    return fixed.get(net, (0., 5.25) if ref in ("U1", "U11") else (0., 3.3))


def logic_row(row, ref, nets):
    nominal = [logic_nominal(ref, net) for net in nets]
    difference = "UNKNOWN (NC floating)" if None in nominal else round(max(
        abs(nominal[0][0]-nominal[1][1]), abs(nominal[0][1]-nominal[1][0])), 3)
    if "HV_OVP_S" in nets:
        fault = "195 V bus: 1.291 V pin; one 499k short: 1.717 V pin; R64 open: 195 V open-circuit source through 1.996 MΩ; loaded and clamp excursions UNKNOWN"
    elif "HV_RES_S" in nets:
        fault = "195 V bus: 4.438 V pin; one 453k short: 5.873 V pin; R69 open: 195 V open-circuit source through 1.812 MΩ; loaded and clamp excursions UNKNOWN"
    elif ref in ("U1", "U11"):
        fault = "UNKNOWN; input fault, eFuse FET short, backfeed and bias-dependent pin behavior; 28 V device input absolute maximum is a part limit"
    elif ref == "U6":
        fault = "UNKNOWN; OLED-port short/backfeed, supply order, and external harness fault path"
    else:
        fault = "UNKNOWN; comparator supply collapse, reference fault, cross-channel coupling and common return open"
    changed = ref in ("U6", "U13", "U14")
    layout = ("Original generic 1.625 × 0.50 mm lands, 4.225 mm row span; new TI 1.40 × 0.45 mm, "
              "4.40 mm row span, 0.65 mm pitch and 0.05 mm corner radius") if changed else (
              "TI split-layout RPW0010A comparison with 0.6 mm side lands and 1.75 mm center lands; "
              "special land extensions and opens need dedicated stencil/DFM and pin-escape review")
    return dict(**row, Manufacturer_Package=TI[ref][0],
                Nominal_Max_Delta_V=difference, Nominal_Scope="Analog calculation or healthy supply envelope, not measured",
                Startup_Max_Delta_V="UNKNOWN", Shutdown_Max_Delta_V="UNKNOWN", Single_Fault_Bounds=fault,
                Land_Pattern=layout, Manufacturer_Drawing=TI[ref][1], Fab_Evidence_URL=FAB,
                Fab_Status="HOLD: lot, stackup, etch/registration, mask bridge, stencil and paste process unsigned",
                Assessment="REWORK" if changed else "HOLD",
                Followup="Rework implemented; assembled-voltage and DFM qualification open" if changed else
                         "Preserve original DRC; qualify voltage, copper and stencil before deciding an exception",
                Rule_Exception="NONE")


def nearest(before, after, eid):
    first, second = (after.by_id[i] for i in eid)
    distances = [copper(first, layer).distance(copper(second, layer)) for layer in LAYERS
                 if first.IsOnLayer(layer) and second.IsOnLayer(layer)]
    return "" if not distances else round(min(distances), 6)


def qualify():
    evidence = HERE / "evidence"
    before = BoardRouter(BASE / "eda" / f"{SOURCE_STEM}.kicad_pcb")
    after = BoardRouter(HERE / "eda" / f"{STEM}.kicad_pcb")
    load = lambda state: json.loads((evidence/state/"DRC-all-tracks.json").read_text(encoding="utf-8"))
    initial, updated = load("before"), load("after")
    parts = [{c.get("ref"): c for c in ET.parse(evidence/state/"netlist.xml").findall("components/comp")}
             for state in ("before", "after")]
    new = {drc_key(e): e for e in updated["violations"]}
    rows = {key: [] for key in ("lv_same_package", "mmbta42_candidate_exception",
                                "switch_package", "hv_internal_external")}
    for entry in initial["violations"]:
        key = drc_key(entry)
        required, actual = drc_distances(entry)
        as_labels = [descriptor(before, i) for i in key[1]]
        cat = classify([label[:3] for label in as_labels], required)
        if cat not in rows:
            raise RuntimeError(cat)
        (ref, pin_a, net_a, la, _), (ref_b, pin_b, net_b, lb, _) = as_labels
        component = parts[0][ref]
        updated_part = parts[1][ref]
        mpn = lambda c: c.findtext("fields/field[@name='MPN']", "").split(" / ")[0]
        row = dict(Reference_A=ref, Pin_A=pin_a, Net_A=net_a, Reference_B=ref_b, Pin_B=pin_b, Net_B=net_b,
                   MPN_Before=mpn(component), MPN_After=mpn(updated_part), Layers_Before=f"{la}/{lb}",
                   Footprint_Before=component.findtext("footprint"), Footprint_After=updated_part.findtext("footprint"),
                   Native_Minimum_mm=required, Native_Before_mm=actual, Final_Pad_Gap_mm=nearest(before, after,key[1]),
                   Final_Pair_In_DRC="YES" if key in new else "NO",
                   UUID_A=key[1][0], UUID_B=key[1][1])
        if cat == "lv_same_package":
            row = logic_row(row, ref, (net_a, net_b))
        elif cat == "mmbta42_candidate_exception":
            row.update(Jingdao_Pinout="1=B; 2=E; 3=C", Nominal_Off_Screen_V=170, Abnormal_Off_Screen_V=195,
                       Startup_Shutdown_Float_and_Fault_Max="UNKNOWN",
                       Lead_Air_Clearance="UNKNOWN: mounted min including placement/lead and solder tolerance",
                       Mold_and_Board_Creepage="UNKNOWN: path, package and laminate CTI, pollution and environment",
                       Land_Pattern="Jingdao p3: 0.90 × 0.80 mm pads; x rows 2.00 mm; opposing B/E y ±0.95 mm",
                       Source_URL=MMBTA42, Assessment="HOLD", Rule_Exception="NONE")
        elif cat == "switch_package":
            part_state = {"C48": "REWORK: KEMET 2220 DNP", "D3": "HOLD: SMA package",
                          "Q32": "HOLD: DPAK package"}
            row.update(Repeated_Peak_V="UNKNOWN", Assessment=part_state[ref], Rule_Exception="NONE")
        else:
            row.update(Assessment="COPPER_SCREEN_CLOSED_BY_RELAYOUT", Rule_Exception="NONE")
        rows[cat].append(row)

    assert [len(group) for group in rows.values()] == [34, 60, 4, 5]
    for kind, name in (("lv_same_package", "LV_IC_CLEARANCE_QUALIFICATION.csv"),
                       ("mmbta42_candidate_exception", "MMBTA42_INSULATION.csv"),
                       ("switch_package", "SWITCH_PACKAGE_CLEARANCE.csv"),
                       ("hv_internal_external", "HV_EXTERNAL_CLEARANCE.csv")):
        csv(HERE / name, sorted(rows[kind], key=lambda r: (r["Reference_A"],r["Pin_A"],r["Reference_B"],r["Pin_B"])))
    print({name: dict(Counter(row["Assessment"] for row in values)) for name, values in rows.items()})


if __name__ == "__main__":
    qualify()
