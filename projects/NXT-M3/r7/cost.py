"""Use native BOM, exact-MPN sources and order-lot rounding without imputing unknowns."""
from collections import Counter
import csv
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
UNKNOWN = "UNKNOWN"
BOARD_COUNTS = (1,3,5,10)
EXTRA = [
    ("TNPW1206100KBEEA","TNP100KACCT-ND","DigiKey",44757,"https://www.digikey.com/en/products/detail/vishay-dale/TNPW1206100KBEEA/1608081",{1:".47000",10:".39200"}),
    ("B32774D4505K000","871-B32774D4505K000","Mouser",1818,"https://www.mouser.com/en/ProductDetail/TDK/B32774D4505K000",{1:"4.61",10:"3.31"}),
    ("HV5622PG-G","HV5622PG-G-ND","DigiKey",186,"https://www.digikey.com/en/products/detail/microchip-technology/HV5622PG-G/4902502",{1:"8.81",25:"7.33"}),
    ("HV5622PJ-G","HV5622PJ-G-ND","DigiKey",0,"https://www.digikey.com/en/products/detail/microchip-technology/HV5622PJ-G/4902556",{1:"8.32",25:"6.93"}),
    ("STP9NK50Z","497-3203-5-ND","DigiKey",734,"https://www.digikey.com/en/products/detail/stmicroelectronics/STP9NK50Z/654545",{1:"3.65",10:"2.377"}),
    ("STPSC4H065D","497-12802-5-ND","DigiKey",0,"https://www.digikey.com/en/products/detail/stmicroelectronics/STPSC4H065D/3770076",{1:"2.50"}),
    ("TPS552872RYQR","595-TPS552872RYQR","Mouser",10017,"https://www.mouser.com/en/ProductDetail/Texas-Instruments/TPS552872RYQR",{1:"5.49",10:"4.20"}),
    ("MSS1260-154KLD","994-MSS1260-154KLD","Mouser",135,"https://www.mouser.com/ProductDetail/Coilcraft/MSS1260-154KLD",{1:"2.17",10:"1.85"}),
    ("TMR 1-1212","49X9908","Newark",0,"https://www.newark.com/traco-power/tmr-1-1212/isolated-board-mount-dc-dc-converter/dp/49X9908",{1:"11.25",5:"11.21",10:"11.16"}),
    ("450PX4.7MEFC10X12.5","450PX4.7MEFC10X12.5-ND","DigiKey",0,"https://www.digikey.com/en/products/detail/rubycon/450PX4-7MEFC10X12-5/3563557",{1:".82",10:".513"}),
]


def read(path):
    with path.open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (ROOT/name).open("w",encoding="utf-8",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def quotes():
    candidates = [dict(row,seller="LCSC") for row in read(ROOT/"LCSC_PRICE_EVIDENCE.csv")]
    candidates += [
        dict(mpn=mpn,sku=sku,seller=seller,date_utc="2026-11-19 Asia/Shanghai",
             url=url,currency="USD",qty_tier=str(threshold),unit_price=unit,stock=str(stock),moq="1",multiple="1",
             factory_pack=UNKNOWN,freight=UNKNOWN,tax=UNKNOWN,status="PUBLIC_PAGE_CACHED_RECHECK")
        for mpn,sku,seller,stock,url,tiers in EXTRA for threshold,unit in tiers.items()
    ]
    candidates.append(dict(mpn="STTH1R06U",sku="C283526",seller="LCSC",date_utc="2026-11-19 Asia/Shanghai",
                           url="https://www.lcsc.com/de/product-detail/C283526.html",currency="USD",qty_tier="5",
                           unit_price=".1331",stock="9360",moq="5",multiple="5",factory_pack="2500",
                           freight=UNKNOWN,tax=UNKNOWN,status="PUBLIC_PAGE_CACHED_RECHECK"))
    return candidates


def order(book, mpn, units, seller=None, require_stock=True):
    choices = []
    for quote in book:
        if quote["mpn"]!=mpn or (seller and quote["seller"]!=seller) or quote["currency"]!="USD":
            continue
        if any(not quote[key].isdigit() for key in ("qty_tier","moq","multiple","stock")):
            continue
        step = int(quote["multiple"])
        count = (max(units,int(quote["moq"]))+step-1)//step*step
        if count < int(quote["qty_tier"]) or (require_stock and int(quote["stock"]) < count):
            continue
        choices.append((Decimal(quote["unit_price"])*count,count,quote))
    return min(choices,key=lambda row:row[0]) if choices else (None,None,None)


def native_bom():
    target = ET.parse(ROOT/"evidence/native.xml")
    native = {c.attrib["ref"]:c for c in target.findall("./components/comp")}
    csv_rows = read(ROOT/"evidence/native_bom.csv")
    assert set(native)=={row["ref"] for row in csv_rows}
    for row in csv_rows:
        c = native[row["ref"]]
        assert row["mpn"] == c.findtext("./fields/field[@name='MPN']")
        assert row["value"] == c.findtext("value")
        assert row["footprint"] == (c.findtext("footprint") or "")
        row["fitted_per_board"] = int(not row["dnp"] and not row["ref"].startswith("H"))
        for n in BOARD_COUNTS:
            row[f"qty_{n}"] = n*row["fitted_per_board"]
    return csv_rows


def main():
    prices = quotes()
    write("SUPPLEMENTAL_PRICE_EVIDENCE.csv",[row for row in prices if row["status"]=="PUBLIC_PAGE_CACHED_RECHECK"])
    bom = native_bom()
    write("FINAL_BOM.csv",bom)
    base = read(ROOT.parent/"r6/PRELIMINARY_BOM.csv")
    snapshots = []
    totals = []
    topology = []
    for n in BOARD_COUNTS:
        for version in ("R6","R7"):
            if version=="R6":
                group = Counter()
                for line in base:
                    if line["subsystem"] != "INTEGRATION":
                        group[line["mpn"]] += int(line[f"qty_{n}"])
            else:
                group = Counter()
                for line in bom:
                    group[line["mpn"]] += line[f"qty_{n}"]
            known, quoted_pns, unknown_lines = Decimal(0), 0, 0
            for mpn, needed in sorted(group.items()):
                if needed == 0:
                    continue
                value, qty, quote = order(prices,mpn,needed)
                if value is None:
                    unknown_lines += needed
                else:
                    known += value
                    quoted_pns += 1
                snapshots.append(dict(design=version,boards=n,mpn=mpn,required=needed,order_qty=qty or UNKNOWN,
                                      USD_public_subtotal=value if value is not None else UNKNOWN,
                                      stock=quote["stock"] if quote else UNKNOWN,sku=quote["sku"] if quote else UNKNOWN,
                                      date=quote["date_utc"] if quote else UNKNOWN,seller=quote["seller"] if quote else UNKNOWN,
                                      url=quote["url"] if quote else UNKNOWN,
                                      basis="TBD items represent multiple unpriced refs" if mpn=="TBD" else "pre-tax, pre-freight"))
            for category,basis in {
                "board_material_known_subset":f"{quoted_pns} distinct exact MPNs deliverable at published stock, assembly and freight excluded",
                "full_BOM":"unpriced fitted instances (including board connectors and sockets) prevent full valuation",
                "PCB":"one shared design. Actual outline, layers, order charges unknown",
                "SMT":"one stencil/setup scope. Actual fixture, setup, feeder and assembly unknown",
                "THT":"J connectors, sockets, U3, Q1, D20, C20, six anode resistors",
                "connectors":"board connectors already inside BOM. External mating/connectivity costs unknown",
                "mechanical_protection":"touch protection and housing not sized",
                "external_power":"separate approved supply and power harness per module or low-voltage distribution",
                "test_fixture":"incremental tooling, low-voltage and gated HV fixture",
                "rebuild":"one PCB design, first-build re-spin cost unknown",
                "spares":"project quantity and availability unknown",
                "freight_tax":"destination, multi-vendor minimum and tax unknown",
                "tube_assets":f"{min(n*3,9)} owned tubes; {max(n*3-9,0)} extra tubes for populated assemblies; replacement value UNKNOWN",
                "first_set":"materials, quoted setup and incremental development not completed",
                "repeat_set":"materials, board fabrication, assembly and protection not completed",
                "one_time_NRE":"incremental engineering and validation only",
            }.items():
                value = str(known) if category=="board_material_known_subset" else (
                    "0_ASSET_CASH" if category=="tube_assets" and n<=3 else UNKNOWN)
                totals.append(dict(design=version,boards=n,category=category,USD=value,
                                   unknown_fitted_instances=unknown_lines if category=="full_BOM" else "NA",basis=basis))
        original,_,_ = order(prices,"LT3757AEMSE#PBF",n,"LCSC")
        driver,_,_ = order(prices,"UCC27511DBVR",n,"LCSC")
        for name,mpn,remove_driver,state in [
            ("P1","LT3757AEMSE#PBF",False,"REFERENCE"),
            ("P2_TPS40210_external","TPS40210DGQR",False,"CHEAPER_ONLY"),
            ("P2_TPS40210_direct","TPS40210DGQR",True,"CHEAPER_ONLY"),
            ("P2_UCC28C43","UCC28C43DR",False,"CHEAPER_ONLY"),
            ("P3_24V","LT3757AEMSE#PBF",False,"SCREEN_ONLY"),
        ]:
            controller,_,_ = order(prices,mpn,n,"LCSC")
            current = controller if remove_driver else controller+driver
            topology.append(dict(design=name,boards=n,comparison=state,controller=mpn,
                                 controller_and_driver_USD=current,subset_saving_vs_P1_USD=original+driver-current,
                                 full_board_BOM=UNKNOWN,pcb_smt_tht_freight_NRE=UNKNOWN,
                                 three_module_first_and_repeat_total=UNKNOWN))
        totals.append(dict(design="R7_MINUS_R6",boards=n,category="full_comparable_board_delta",
                           USD=UNKNOWN,unknown_fitted_instances="NA",basis="No verified same-scope all-in totals"))
    write("evidence/order_lines.csv",snapshots)
    write("BEFORE_AFTER_COST.csv",totals)
    write("POWER_TOPOLOGY_COST_COMPARISON.csv",topology)


if __name__=="__main__":
    main()
