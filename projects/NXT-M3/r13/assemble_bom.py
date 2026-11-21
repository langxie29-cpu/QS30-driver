"""Mechanical BOM extraction for the CNY evidence ledger."""
from collections import Counter
import csv
from decimal import Decimal
import io
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent
STAGING = ROOT / ".local/cost_staging"
OBS_DATE = "2026-11-22"
POWER_SHEETS = {"/HV_boost/","/Gate_bias/"}
SHARED_SHEETS = {"/HV_cutoff/","/Analog_protection/","/HV_bleeders/","/Hardware_inhibit/"}
SOURCE = {
    "A":"https://github.com/drkmsmithjr/NixiePowerSupply/tree/14d6dbdf172b5c5d0535d9fe728d953f2daf0fe2/KC_NixieSupply5vTo170vMini",
    "B":"https://github.com/esynr3z/nixie-ps/blob/9df409c9770b6c32111396fc9dea318ff907d41d/doc/nixie-ps_bom_A.csv",
    "C":"https://github.com/tonyp7/170v-nixie-power-supply/blob/964ccdc3b0d4e89d736d35d66256226c13dcc4d0/bom/bom.csv",
    "D":"https://github.com/langxie29-cpu/QS30-driver/tree/40126f897bef6f849a68987f2daa0c1afd8a2c2d/projects/NXT-M3/r11",
}
PUBLIC_ONE = {
    ("B","U1"):("LM3488MM/NOPB","28.37",
        "https://www.digikey.cn/zh/products/base-product/texas-instruments/296/LM3488/11732",
        "Observed stock 2. /NOPB active successor to reference LM3488MM; equivalent packaging and pinout verify before release."),
    ("C","U1"):("LT3757EMSE#PBF","62.77",
        "https://www.digikey.cn/zh/products/filter/%E7%94%B5%E6%BA%90%E7%AE%A1%E7%90%86-pmic/dc-dc-%E5%BC%80%E5%85%B3%E6%8E%A7%E5%88%B6%E5%99%A8/715?s=N4IgjCBcoLQBxVAYygMwIYBsDOBTANCAPZQDaIArAAwUiFhgBMA7HeAGwSFw0AsbcCrXrNhIHo0YgAugF95QA",
        "1-piece price observed; tier and checkout cash open."),
}
FIELDS = ["Candidate","Scope","Reference","MPN","Manufacturer","Quantity","Unit Price","Currency",
          "Source URL","Quote Date","MOQ","Alternate","Verification Status","Risk","Value","Footprint","Source Reference"]


def part(ref, mpn, manufacturer, value, foot, source, scope, qty=1, risk=""):
    return {"Scope":scope,"Reference":ref,"MPN":mpn or "TBD","Manufacturer":manufacturer or "TBD",
            "Quantity":qty,"Unit Price":"","Currency":"CNY","Source URL":source,"Quote Date":"",
            "MOQ":"","Alternate":"","Verification Status":"UNQUOTED","Risk":risk or
            "Verify exact MPN, thermal/voltage ratings, sourcing and layout.",
            "Value":value,"Footprint":foot,"Source Reference":ref}


def xml_records(file, route):
    root = ElementTree.parse(file)
    for x in root.findall("./components/comp"):
        ref = x.get("ref")
        fields = {field.get("name"):field.text for field in x.findall("./fields/field")}
        sheet = x.find("sheetpath").get("names")
        value = x.findtext("value")
        footprint = x.findtext("footprint")
        if route == "D":
            scope = ("HV_STAGE" if sheet in POWER_SHEETS else "HV_SAFETY" if sheet in SHARED_SHEETS
                     or ref in {"U1","F1","D4","J1","U26"} or ref.startswith("R30")
                     else "M3_NON_HV")
        else:
            scope = "HV_STAGE"
        risk = f"Review {sheet.strip('/') or 'upstream'}; schematic reference, stock unverified."
        url = x.findtext("datasheet") or SOURCE[route]
        row = part(ref,fields.get("MPN"),fields.get("Manufacturer") or fields.get("MAN"),
                   value,footprint,url if url.startswith("https://") else SOURCE[route],scope,risk=risk)
        if x.find("property[@name='dnp']") is not None or value in {"N.U.","DNP"}:
            if route == "D" and scope in {"HV_STAGE","HV_SAFETY"}:
                row.update(**{"Verification Status":"UNQUOTED_REQUIRED_FUNCTION", "Risk":risk+" Native DNP. Cost basis includes its replacement function and does not authorize population."})
            else:
                row.update(Quantity=0, **{"Verification Status":"DNP", "Risk":risk+" Native DNP."})
        yield row


def csv_records(route):
    if route == "B":
        upstream = ROOT/".local/B/doc/nixie-ps_bom_A.csv"
        contents = upstream.read_text(encoding="utf-8-sig",errors="replace")
        for item in csv.DictReader(io.StringIO(contents)):
            n = item.get("Quantity Per PCB")
            if not n or not n.isdecimal():
                continue
            ref,value = item["References"],item["Value"]
            mpn, maker = {
                "U1":("LM3488MM","Texas Instruments"),
                "Q1":("IRFH7185TRPBF","Infineon"),
                "D2":("SMBJ70CA","Littelfuse candidate"),
                "D1":("E1G","LRC candidate"),
                "T1":("Custom EFD15 10:145","TBD winder"),
                "RV1":("PVZ3A152","Murata"),
            }.get(ref,("",""))
            risk = "Custom winding, leakage, saturation, insulation, lot and labor quote open." if ref=="T1" else ""
            yield part(ref,mpn,maker,value,item["Footprint"],SOURCE[route],"HV_STAGE",int(n),risk)
    else:
        upstream = ROOT/".local/C/bom/bom.csv"
        for item in csv.DictReader(io.StringIO(upstream.read_text(encoding="utf-8-sig",errors="replace"))):
            yield part(item["Ref Desc"],item["Manufacturer Part Number"],item["Manufacturer"],
                       item["Description"],item["Package"],SOURCE[route],"HV_STAGE",int(item["Quantity"]),
                       "Regional stock and ALD equivalence open." if item["Ref Desc"]=="L1" else "")


def open_items():
    yield part("PCB-FR4-INCREMENT","","PCB fab","HV incremental PCB cost or HV daughterboard","","","HV_SAFETY",
               risk="Use paired main-board quotes, or quote whole daughterboard. Fit and stackup open.")
    yield part("PCB-FR4-REMAINDER","","PCB fab","Remaining shared PCB material","","","M3_NON_HV",
               risk="Exactly one whole PCB total with HV share.")
    yield part("HV-BRANCH-SENSE-1..3","","","Three sustained branch faults","","","HV_SAFETY",3,
               "Topology and cost open. Preserve all independent fault objectives.")
    yield part("TOUCH-GUARD","","","Touch barrier and hardware","","","HV_SAFETY",
               risk="Enclosure, spacers and mechanical constraints unverified.")
    yield part("TUBE-1..3","QS30-1","","Nixie tubes","","","M3_NON_HV",3,
               "Owned pool in R10; all-material basis includes replacement value, cash basis may exclude usable inventory.")
    yield part("OLED-PANEL","","","0.91 inch yellow OLED","","","M3_NON_HV",
               risk="User's physical SKU and unit cost open; R10 historical ¥9.78.")
    yield part("FASTENERS-AND-WIRE","","","Socket handoff harness, fasteners and tube mounting","","","M3_NON_HV",
               risk="Working outline, 6×Ø3.5 mm holes and lead map need physical verification.")
    for key in ("PCB-FAB-SERVICE","SMT","STENCIL","FREIGHT-TAX","MANUAL-ASSEMBLY","MOQ-OVERBUY"):
        yield part(key,"","","Prototype cash cost","","","CASH_ONLY",
                   risk="Requires same-lot quote. Bare material PCB is already tracked above.")


def route_items(route):
    base = list(xml_records(ROOT/"evidence/eda_baseline/native_netlist.xml","D"))
    if route == "D":
        yield from base
    else:
        replacements = (xml_records(ROOT/".local/A/KC_NixieSupply5vTo170vMini/"
                                    "NixieSupply5vto170vDCMBoostMini.xml","A") if route=="A"
                        else csv_records(route))
        for item in replacements:
            reference = item["Reference"]
            external_only = (route=="A" and reference in {"J1","J2","J3","J4","J5","J6","P1","Q26"}) or (route=="B" and reference=="J1 J2")
            if external_only:
                item.update(Quantity=0, **{"Verification Status":"REFERENCE_ONLY","Risk":"Upstream standalone connector or test driver. Integrated cost includes any added interface under INTEGRATION-DELTA."})
            yield item
        for item in base:
            if item["Scope"] != "HV_STAGE":
                yield item | {"Reference":"R11:"+item["Reference"]}
    yield from open_items()
    if route != "D":
        yield part("INTEGRATION-DELTA","","","Adapted feedback, clamp/OCP as applicable, verified connector if separate","","","HV_SAFETY",
                   risk="Replace with integrated design references once selected. Core power BOM above is upstream.")


def write_csv(path, fields, records):
    with path.open("w",encoding="utf-8",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main():
    STAGING.mkdir(exist_ok=True)
    comparison = []
    for count in (1,3,10):
        rows = []
        for route in "ABCD":
            routed = []
            for basis in route_items(route):
                item = dict(basis,Candidate=route)
                item["Quantity"] *= count
                key = route,item["Reference"]
                if key in PUBLIC_ONE and count == 1:
                    mpn,price,url,risk = PUBLIC_ONE[key]
                    item.update(MPN=mpn, **{"Unit Price":price, "Source URL":url, "Quote Date":OBS_DATE,
                        "MOQ":1,"Risk":risk,"Verification Status":"PUBLIC_SINGLE_PRICE"})
                elif key in PUBLIC_ONE:
                    item.update(**{"Source URL":PUBLIC_ONE[key][2],
                        "Risk":"Order-size stock, price and checkout unverified. See 1PC observation."})
                routed.append(item)
            rows.extend(routed)
            included = [item for item in routed if item["Quantity"] > 0 and item["Scope"] != "CASH_ONLY"]
            counts = Counter(item["Scope"] for item in included if not item["Unit Price"])
            subtotal = sum(Decimal(item["Unit Price"])*item["Quantity"]
                           for item in included if item["Unit Price"])
            comparison.append({"Candidate":route,"Lot":count,
                               "HV public price subset per module CNY":str(subtotal/count) if subtotal else "",
                               "Unquoted HV line items":counts["HV_STAGE"]+counts["HV_SAFETY"],
                               "Unquoted M3 material line items":sum(counts.values()),
                               "HV_COST_CNY":"UNVERIFIED","M3_COST_CNY":"UNVERIFIED",
                               "EVT_CASH_CNY":"UNQUOTED","R11 saving CNY":"UNVERIFIED",
                               "HV-60":"EXCEEDS_PUBLIC_SINGLE_PART" if (route,count)==("C",1) else "UNPROVEN",
                               "M3-60":"UNPROVEN"})
        write_csv(STAGING/f"BOM_R13_{count}PC.csv",FIELDS,rows)
    write_csv(STAGING/"COST_COMPARISON.csv",list(comparison[0]),comparison)


if __name__ == "__main__":
    main()
