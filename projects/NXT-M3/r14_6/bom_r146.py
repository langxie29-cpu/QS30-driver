"""Create BOM and the procurement scenarios from the final native XML netlist."""
import csv
from collections import defaultdict
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
DATE = "2026-11-22"
NEW_LOOKUPS = {"RC0603FR-073KL", "RC0603FR-0710KL", "ESP32-S3-WROOM-1-N8"}
FIELDS = ("Reference Value MPN Manufacturer Footprint Quantity DNP Supplier Supplier_PN MOQ "
          "Price_Tier Unit_Price_CNY Purchase_Qty Extended_Cost_CNY Evidence_URL Quote_Date "
          "Alternate Verification_Status").split()
DK = "https://www.digikey.cn/zh/products/detail/"
QUOTE = {
    "ES1G-13-F": ("ES1G-FDICT-ND", DK+"diodes-incorporated/ES1G-13-F/1099157", {1: "5.40", 10: "3.351"}),
    "STD13N60M2": ("497-13862-1-ND", DK+"stmicroelectronics/STD13N60M2/4250805", {1: "16.13", 10: "10.28"}),
    "TCA9517ADGKR": ("296-39220-1-ND", DK+"texas-instruments/TCA9517ADGKR/5143217", {1: "10.09", 10: "7.302"}),
    "TPS259474LRPWR": ("296-TPS259474LRPWRCT-ND", DK+"texas-instruments/TPS259474LRPWR/14123976",
                       {1: "17.43", 10: "12.821"}),
    "SN74HC595PWR": ("296-23258-1-ND", DK+"texas-instruments/SN74HC595PWR/1571275",
                    {1: "4.96", 10: "3.506", 25: "3.136"}),
    "RC0603FR-073KL": ("311-3.00KHRCT-ND", DK+"yageo/RC0603FR-073KL/727119",
                       {1: ".83", 10: ".207", 25: ".15560", 50: ".124", 100: ".10090"}),
    "RC0603FR-0710KL": ("311-10.0KHRCT-ND", DK+"yageo/RC0603FR-0710KL/726880",
                        {1: ".83", 10: ".207", 25: ".15560", 50: ".124", 100: ".10090"}),
    "ESP32-S3-WROOM-1-N8": ("5407-ESP32-S3-WROOM-1-N8CT-ND",
                           DK+"espressif-systems/ESP32-S3-WROOM-1-N8/15200089", {1: "46.81", 10: "40.498"}),
}
MAKERS = {
    "MMBTA42": "Shandong Jingdao Microelectronics", "STD13N60M2": "STMicroelectronics",
    "STUSB4500LQTR": "STMicroelectronics", "ESDA25L": "STMicroelectronics",
    "B32774M4335K000": "TDK", "C2220C101JDGACTU": "KEMET",
    "0467002.NR": "Littelfuse", "TL3342F160QG": "E-Switch", "MSS1278-223MLD": "Coilcraft",
    "WSL2512R0500FEA": "Vishay", "CRCW251210K0FKEG": "Vishay",
    "2N7002BK,215": "Nexperia", "BAT54H,115": "Nexperia", "USB4125-GF-A": "GCT",
    "ES1G-13-F": "Diodes Incorporated",
}
EXTRA_EVIDENCE = {
    "MMBTA42": ("LCSC", "C4749118", "https://item.szlcsc.com/5321818.html"),
    "C2220C101JDGACTU": ("Farnell", "3505448",
                        "https://no.farnell.com/kemet/c2220c101jdgactu/cap-100pf-1kv-mlcc-2220/dp/3505448"),
}


STOCK_NOTE = {
    "ESP32-S3-WROOM-1-N8": "Distributor snapshot displayed 0 in stock and expected replenishment; live inventory and lead time TBD",
    "RC0603FR-0710KL": "Distributor price observed; carton availability needs confirmation",
}
PCB_PAGE = "https://cart.jlcpcb.com/"
PCBA_PAGE = "https://jlcpcb.com/help/article/pcb-assembly-price"
SERVICE_BUDGET = {
    # Low/high CNY cash allowances; each range applies to the complete lot.
    1: ((90,240), (865,1250), (118,119), (35,90), (18,70), (80,260), (20,90), (0,180), (10,120)),
    3: ((90,240), (876,1300), (118,119), (105,270), (54,210), (180,620), (20,90), (0,400), (30,350)),
}
SERVICES = (
    ("PCB-FAB", "4-layer 130 x 80 mm PCB, budget lot of 5; actual MOQ TBD", PCB_PAGE),
    ("SMT", "Dual-side SMT setup, feeder, run and fixture, excludes stencil", PCBA_PAGE),
    ("STENCIL", "Two-sided stencil, one order", PCBA_PAGE),
    ("HAND-ASSY", "Hand soldering and assembly labor", PCBA_PAGE),
    ("HARNESS-HARDWARE", "Wire, sleeves, support, fasteners and clamps; sockets in BOM", ""),
    ("TEST", "Low-voltage checkout and inspection labor allowance", ""),
    ("FREIGHT", "Consolidated domestic freight allowance", ""),
    ("TAX", "Incremental tax reserve, excluding VAT already in published CT prices", ""),
    ("UNQUOTED-SPARES", "Allowance for handling loss and pack increments on unquoted SKUs", ""),
)

def maker(mpn):
    for prefix, name in (("TPS", "Texas Instruments"), ("TPD", "Texas Instruments"),
                         ("SN74", "Texas Instruments"), ("TCA", "Texas Instruments"),
                         ("TLV", "Texas Instruments"), ("REF33", "Texas Instruments"),
                         ("UCC", "Texas Instruments"), ("LM5155", "Texas Instruments"),
                         ("RC0603", "Yageo"), ("SRN", "Bourns"), ("ESP32", "Espressif"),
                         ("BM06B", "JST"), ("S2B-PH", "JST")):
        if mpn.startswith(prefix):
            return name
    return MAKERS.get(mpn, "")


def get_components(source):
    for c in ET.parse(source).findall("components/comp"):
        fields = {f.attrib["name"]: f.text or "" for f in c.findall("fields/field")}
        raw = fields.get("MPN", "")
        mpn = raw.split(" / ", 1)[0]
        if mpn in {"SS14", "SMBJ6.0CA"}:
            state = "GENERIC_PART_MANUFACTURER_TBD"
        elif not mpn:
            state = "MPN_TBD"
        elif mpn == "GZC13-F":
            state = "MODEL_ONLY_SOCKET_LOT_UNVERIFIED"
        else:
            state = "IDENTIFIED_UNQUOTED"
        dnp = c.find("property[@name='dnp']") is not None or fields.get("Status") == "HOLD_DNP"
        row = dict(Reference=c.get("ref"), Value=c.findtext("value", ""), MPN=mpn,
                   Manufacturer=maker(mpn), Footprint=c.findtext("footprint", ""),
                   Quantity=1, DNP="YES" if dnp else "NO", Evidence_URL=c.findtext("datasheet", ""),
                   Verification_Status=state, Alternate="")
        if mpn in EXTRA_EVIDENCE:
            row["Supplier"], row["Supplier_PN"], row["Evidence_URL"] = EXTRA_EVIDENCE[mpn]
        if mpn in QUOTE:
            pn, url, tiers = QUOTE[mpn]
            row.update(Supplier="DigiKey CT", Supplier_PN=pn, MOQ=1, Price_Tier="1+",
                       Unit_Price_CNY=tiers[1], Evidence_URL=url,
                       Quote_Date="2026-11-23" if mpn in NEW_LOOKUPS else DATE,
                       Verification_Status="PUBLIC_PAGE_SNAPSHOT_CNY")
        if row["Reference"].startswith("MH"):
            row["Verification_Status"] = "BOARD_HOLE_ONLY_HARDWARE_IN_MECHANICAL"
        row["Purchase_Qty"] = 0 if dnp or row["Reference"].startswith("MH") else ""
        row["Extended_Cost_CNY"] = 0 if row["Purchase_Qty"] == 0 else ""
        yield row


def sort_ref(row):
    match = re.fullmatch(r"([A-Z]+)([0-9]+)", row["Reference"])
    return (match[1], int(match[2])) if match else (row["Reference"], 0)


def bracket(row):
    ref, value, footprint = (row[k] for k in ("Reference", "Value", "Footprint"))
    if row["MPN"] == "MMBTA42":
        return ".10", ".45"
    if ref.startswith("R"):
        return (".30", "3.50") if "2512" in footprint or "HV" in value else (".03", ".25")
    if ref.startswith("C"):
        return ("6", "30") if ref == "C47" else (".07", "1.20")
    if ref.startswith("V"):
        return "5", "20"
    if ref.startswith(("U", "J", "SW", "L")):
        return ("21", "40") if ref == "U3" else ("1", "14")
    return ".15", "4.00"


def calculate(bom):
    groups = defaultdict(list)
    for row in bom:
        key = (row["MPN"], row["Manufacturer"]) if row["MPN"] else (row["Value"], row["Footprint"])
        groups[(key, row["DNP"])].append(row)
    rows = []
    stats = {}
    for modules in (1, 3):
        for group in groups.values():
            representative = group[0]
            enabled = representative["DNP"] == "NO" and not representative["Reference"].startswith("MH")
            demand = len(group) * modules if enabled else 0
            quote = QUOTE.get(representative["MPN"])
            ref = " ".join(r["Reference"] for r in group)
            row = dict(Scenario_Modules=modules, Reference=ref, Value=representative["Value"],
                       MPN=representative["MPN"], Manufacturer=representative["Manufacturer"],
                       Required_Qty=demand, DNP=representative["DNP"], Supplier=representative.get("Supplier", ""),
                       Supplier_PN=representative.get("Supplier_PN", ""), MOQ=representative.get("MOQ", ""),
                       Evidence_URL=representative.get("Evidence_URL", ""),
                       Quote_Date=representative.get("Quote_Date", ""), Source_Class=representative["Verification_Status"],
                       Stock_Note=STOCK_NOTE.get(representative["MPN"], ""))
            if quote and demand:
                # Engineering spares assumption. Each orderable stocked MPN gets at least one spare.
                spares = math.ceil(demand * 0.05)
                order = max(1, demand + spares)
                tier = max(x for x in quote[2] if x <= order)
                price = Decimal(quote[2][tier])
                row.update(Spare_Qty=spares, Price_Tier=tier, Unit_Price_CNY=price, Purchase_Qty=order,
                           Material_CNY=price*demand, Extended_Cost_CNY=price*order,
                           Estimated_Material_Low_CNY=price*demand, Estimated_Material_High_CNY=price*demand)
                if modules == 1:
                    for entry in group:
                        entry["Price_Tier"] = f"{tier}+"
                        entry["Unit_Price_CNY"] = price
                        # Keep cash on one row for the grouped order and avoid counting it twice.
                        entry["Purchase_Qty"] = order if entry is representative else 0
                        entry["Extended_Cost_CNY"] = price*order if entry is representative else 0
            elif demand:
                low, high = map(Decimal, bracket(representative))
                row.update(Estimated_Material_Low_CNY=low*demand, Estimated_Material_High_CNY=high*demand)
            rows.append(row)
        current = [r for r in rows if r["Scenario_Modules"] == modules]
        enabled = [r for r in current if r["Required_Qty"]]
        priced = [r for r in enabled if r.get("Purchase_Qty")]
        stats[modules] = {
            "active_groups": len(enabled), "priced_groups": len(priced),
            "active_refs": sum(r["Required_Qty"] for r in enabled),
            "priced_refs": sum(r["Required_Qty"] for r in priced),
            "public_material_subtotal_CNY": sum(r["Material_CNY"] for r in priced),
            "public_cash_subtotal_CNY": sum(r["Extended_Cost_CNY"] for r in priced),
            "material_estimate_low_CNY": sum(r["Estimated_Material_Low_CNY"] for r in enabled),
            "material_estimate_high_CNY": sum(r["Estimated_Material_High_CNY"] for r in enabled),
        }
        budgets = SERVICE_BUDGET[modules]
        for (ref, value, url), (low, high) in zip(SERVICES, budgets, strict=True):
            rows.append(dict(Scenario_Modules=modules, Reference=ref, Value=value,
                             Purchase_Qty=5 if ref == "PCB-FAB" else "",
                             Evidence_URL=url, Source_Class="ENGINEERING_ESTIMATE_UNQUOTED",
                             Estimated_AddOn_Cash_Low_CNY=low, Estimated_AddOn_Cash_High_CNY=high))
        summary = stats[modules]
        public_price_spare_allowance = summary["public_cash_subtotal_CNY"] - summary["public_material_subtotal_CNY"]
        summary.update(
            confirmed_checkout_quote_CNY=None, confirmed_checkout_active_groups=0,
            pcb_scenario_quantity=5, pcb_verified_moq=None,
            estimated_evt_cash_low_CNY=summary["material_estimate_low_CNY"] + public_price_spare_allowance
            + sum(low for low, _ in budgets),
            estimated_evt_cash_high_CNY=summary["material_estimate_high_CNY"] + public_price_spare_allowance
            + sum(high for _, high in budgets))
        rows.append(dict(Scenario_Modules=modules, Reference="QS30-1-STOCK", Value="QS30-1 display tubes",
                         Required_Qty=3*modules, Purchase_Qty=0, Extended_Cost_CNY=0,
                         DNP="NO", Source_Class="OWNED_INVENTORY_CONDITION_AND_YIELD_TBD"))
    return rows, stats


def write(path, entries, fields):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(entries)


if __name__ == "__main__":
    source = HERE/"evidence/after/netlist.xml"
    bom = sorted(get_components(source), key=sort_ref)
    assert len({r["Reference"] for r in bom}) == len(bom)
    procurement, totals = calculate(bom)
    write(HERE/"BOM_R14_6.csv", bom, FIELDS)
    headers = list(dict.fromkeys(key for row in procurement for key in row))
    write(HERE/"PROCUREMENT_R14_6.csv", procurement, headers)
    totals["native_bom"] = dict(refs=len(bom), dnp=sum(r["DNP"] == "YES" for r in bom),
                                missing_mpn=sum(not r["MPN"] for r in bom))
    (HERE/"evidence/procurement-totals.json").write_text(json.dumps(totals, default=str, indent=2)+"\n",
                                                      encoding="utf-8")
