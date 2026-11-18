"""Snapshot exact-MPN LCSC first-party catalogue tiers without cart or purchase."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SKUS = {
    "TPS26600RHFR":"C2155767", "THVD1410DR":"C2671345", "STP9NK50Z":"C38617",
    "MSS1583-154KED":"C7427458", "UCC27511DBVR":"C191027", "LT3757AEMSE#PBF":"C671464",
    "TMR 1-1212":"C7401942", "HV5622PG-G":"C220637", "TPS3700DDCR":"C33002",
    "STM32C011F4P6":"C5452432", "C1206C101JCGACTU":"C2171157", "MFR02SF1002A10":"C58746",
    "TPS40210DGQR":"C14728", "UCC28C43DR":"C111694", "STPSC2H065B-TR":"C2970070",
    "STTH1R06U":"C283526",
}


def walk(value):
    if isinstance(value, dict):
        yield value
        for sub in value.values():
            yield from walk(sub)
    elif isinstance(value, list):
        for sub in value:
            yield from walk(sub)


def get_product(item):
    mpn, sku = item
    url = f"https://www.lcsc.com/product-detail/{sku}.html"
    response_data = dict(mpn=mpn, sku=sku, url=url, checked_utc=datetime.now(timezone.utc).isoformat())
    try:
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=18) as response:
            raw = response.read()
            response_data["resolved_url"] = response.url
            response_data["page_sha256"] = hashlib.sha256(raw).hexdigest()
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',raw.decode(),re.S)
        if not match:
            raise ValueError("No public SSR snapshot")
        all_data = json.loads(match[1])["props"]["pageProps"]
        candidates = [obj for obj in walk(all_data) if obj.get("productCode")==sku
                      and obj.get("productModel","").strip().casefold()==mpn.casefold()]
        if not candidates:
            observed = {obj.get("productModel") for obj in walk(all_data)
                        if obj.get("productCode")==sku and obj.get("productModel")}
            raise ValueError("No exact product identity: " + repr(sorted(observed)))
        product = max(candidates,key=len)
        fields = ("productModel","productCode","stockNumber","totalStock","productStock","stockInfo","productStorage",
                  "shipStock","productPriceList","minBuyNumber","maxBuyNumber","split","minPacketNumber",
                  "productUnit","minPacketUnit","currency", "currencyCode", "isPreSale", "isReel")
        response_data["catalogue"] = {k:product[k] for k in fields if k in product}
        response_data["stock_fields"] = {k:v for k,v in product.items() if ("stock" in k.lower() or "invent" in k.lower()) and k not in fields}
    except (OSError, ValueError, KeyError) as error:
        response_data["error"] = str(error)
    return response_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch",action="store_true")
    args = parser.parse_args()
    src = ROOT / "evidence" / "lcsc_snapshot.json"
    if args.fetch:
        with ThreadPoolExecutor(max_workers=6) as pool:
            result = list(pool.map(get_product,SKUS.items()))
        with src.open("x",encoding="utf-8") as out:
            json.dump(result,out,indent=2,ensure_ascii=False)
    result = json.loads(src.read_text(encoding="utf-8"))
    rows = []
    for entry in result:
        p = entry.get("catalogue",{})
        stock_data = entry.get("stock_fields",{})
        stock = p.get("stockNumber", stock_data.get("productInventory", "UNKNOWN"))
        if isinstance(stock, dict):
            stock = stock.get("total", "UNKNOWN")
        tiers = p.get("productPriceList") or [{}]
        for tier in tiers:
            rows.append(dict(mpn=entry["mpn"],sku=entry["sku"],date_utc=entry["checked_utc"],url=entry["url"],
                             currency="USD" if tier.get("usdPrice") is not None else "UNKNOWN",
                             qty_tier=tier.get("ladder","UNKNOWN"), unit_price=tier.get("usdPrice","UNKNOWN"),
                             stock=stock,moq=p.get("minBuyNumber","UNKNOWN"),multiple=p.get("split","UNKNOWN"),
                             factory_pack=p.get("minPacketNumber","UNKNOWN"),freight="UNKNOWN",tax="UNKNOWN",
                             status=entry.get("error") or ("CATALOGUE_ONLY" if tier else "IDENTITY_ONLY")))
    with (ROOT/"LCSC_PRICE_EVIDENCE.csv").open("w",newline="",encoding="utf-8") as out:
        writer = csv.DictWriter(out,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for entry in result:
        print(entry["mpn"],entry.get("catalogue",{}).get("stockNumber"),
              entry.get("stock_fields"),entry.get("error"))
if __name__=="__main__":
    main()
