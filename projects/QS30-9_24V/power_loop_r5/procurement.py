"""Fetch public mainland product excerpts and join exact SKU identities to the frozen BOM."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
R4 = HERE.parent / 'power_loop_r4'
LOCAL = {
    'B32774D4106K000': ('4367334', 'C3799662'),
    'STP9NK50Z': ('39600', 'C38617'),
    'LM5069MM-1/NOPB': ('494513', 'C486026'),
    'CRCW251249K9FKEG': ('241389', None),
    'MSS1583-154KED': ('8420123', 'C7427458'),
}
GLOBAL = {
    'LT3757AEMSE#PBF': ('C671464','Analog Devices','https://datasheet.lcsc.com/lcsc/2008311906_Analog-Devices-LT3757AEMSE-PBF_C671464.pdf','SKU_DATASHEET_LINK'),
    'LM5164DDAR': ('C477928','TI','https://www.lcsc.com/product-detail/DC-DC-Converters_Texas-Instruments-Texas-Instruments-LM5164DDAR_C477928.html','SKU_CATALOG'),
    'UCC27511DBVR': ('C191027','TI','https://www.lcsc.com/product-detail/C191027.html','SKU_CATALOG'),
    'TPS3700DDCR': ('C33002','TI','https://lcsc.com/product-detail/Analog-Comparators_Texas-Instruments-TPS3700DDCR_C33002.html','SKU_CATALOG'),
    'TPS3808G01DBVR': ('C19653','TI','https://www.lcsc.com/product-detail/C19653.html','SKU_CATALOG'),
    'TPS3808G50DBVR': ('C134123','TI','https://www.lcsc.com/product-detail/C134123.html','SKU_CATALOG'),
    'TPS26601RHFR': ('C1849471','TI','https://www.lcsc.com/fr/product-detail/C1849471.html','SKU_CATALOG'),
    'SN74HCS08DR': ('C2868021','TI','https://www.lcsc.com/product-detail/C2868021.html','SKU_CATALOG'),
    'SN74HCS74DR': ('C2862638','TI','https://jlcpcb.com/partdetail/TexasInstruments-SN74HCS74DR/C2862638','SKU_SMT_GLOBAL_CATALOG'),
    'NTCLE100E3103JB0': ('C141588','Vishay','https://www.lcsc.com/it/product-detail/NTC-Thermistors_Vishay-Intertech_C141588.html','SKU_CATALOG'),
    'VOS618A-3X001T': ('C511068','Vishay','https://www.lcsc.com/zh-CN/product-detail/C511068.html','SKU_CATALOG'),
}
MANUFACTURER = {
    'STPSC4H065D': 'STMicroelectronics', 'SN74HCS14DR': 'TI',
    'WSL2512R0620FEA': 'Vishay', 'IPB017N10N5LFATMA1': 'Infineon',
    'TPS7A1601DGNR': 'TI', '0451001.MRL':'Littelfuse',
    'EEUFR1J470':'Panasonic', 'MSS1246T-683MLB':'Coilcraft',
}
RATINGS = {
    'B32774D4106K000': ('±10%', '450 Vdc, 10 µF'),
    'STP9NK50Z': ('N/A','500 V, 7.2 A datasheet conditions'),
    'STPSC4H065D': ('N/A','650 V, 4 A datasheet conditions'),
    'CRCW251249K9FKEG': ('±1%','49.9 kΩ, 1 W, 500 V per datasheet limit'),
    'WSL2512R0620FEA': ('±1%','62 mΩ, 1 W'),
    'MSS1583-154KED': ('±10%','150 µH, cold Isat 3.1 A at stated drop, hot HOLD'),
    'NTCLE100E3103JB0': ('±5% R25','10 kΩ at 25 °C'),
    'LM5069MM-1/NOPB': ('N/A','9–80 V operating range'),
    'IPB017N10N5LFATMA1': ('N/A','100 V VDS, temperature-dependent SOA'),
}
LIFECYCLE = {'IPB017N10N5LFATMA1':'ACTIVE (Infineon)', 'SN74HCS74DR':'ACTIVE (TI)'}


def csv_rows(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def observe(item):
    mpn, (item_id, sku) = item
    url = f'https://item.szlcsc.com/{item_id}.html'
    record = dict(mpn=mpn, url=url, checked_at=utc_now())
    try:
        with urlopen(url, timeout=15) as response:
            raw = response.read()
            record.update(http_status=response.status, response_sha256=hashlib.sha256(raw).hexdigest())
        html = raw.decode('utf-8')
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        product = next(x for x in json.loads(ld[1])['@graph'] if x['@type']=='Product')
        props = json.loads(next_data[1])['props']['pageProps']
        web = props['webData']
        fields = web['productRecord']
        if (product['mpn'] != mpn or fields['productModel'] != mpn or
                product['sku'] != fields['productCode'] or sku and product['sku'] != sku):
            raise ValueError('Exact string or SKU mismatch')
        offer = product['offers']
        if offer['priceCurrency'] != 'CNY':
            raise ValueError('Unexpected currency')
        stock = fields.get('validStockNumber')
        price = offer.get('price')
        status = ('OUT_OF_STOCK' if stock == 0 else
                  'INDICATIVE_PRICE' if isinstance(price,(int,float)) and price > 0 else 'PRICE_UNKNOWN')
        record.update(sku=product['sku'], manufacturer=product['brand']['name'],
                      package=fields.get('encapsulationModel'), page_generated=props['pageGeneratedAt'],
                      displayed_unit_cny=price, moq=fields.get('minBuyNumber'),
                      sell_multiple='UNKNOWN', full_pack_qty=fields.get('minWholeNumber'),
                      full_pack_total_cny=fields.get('encaptionPrice'),
                      stock=stock, reported_total_stock=web.get('totalStockNumber'),
                      inventory_jsonld=offer.get('inventoryLevel'),
                      warehouse_gd=web.get('gdWarehouseStockNumber'),
                      warehouse_js=web.get('jsWarehouseStockNumber'),
                      smt_stock_field=web.get('smtStockNumber'),
                      tier_prices='UNKNOWN', tax='UNKNOWN',
                      smt_eligibility='UNKNOWN', library='UNKNOWN',
                      storefront_status=fields.get('productStockStatus', 'UNKNOWN'),
                      price_status=status)
    except (OSError, ValueError, KeyError, StopIteration, TypeError) as exc:
        record.update(price_status='PRICE_UNKNOWN', failure=str(exc))
    return record


def main(refresh):
    snapshot = HERE / 'evidence' / 'lcsc_public_snapshot.json'
    if refresh:
        with ThreadPoolExecutor(max_workers=4) as pool:
            evidence = list(pool.map(observe, LOCAL.items()))
        snapshot.write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    else:
        evidence = json.loads(snapshot.read_text(encoding='utf-8'))
    offers = {row['mpn']: row for row in evidence if row.get('sku')}
    live = json.loads((HERE / 'evidence' / 'vendor_live_catalog.json').read_text(encoding='utf-8'))
    for mpn, observed in live['mainland'].items():
        offer = offers[mpn]
        assert offer['sku'] == observed['sku']
        offer.update(raw_valid_stock=offer['stock'], raw_moq=offer['moq'],
                     stock=observed['stock'], moq=observed['moq'],
                     tier_prices=json.dumps(observed['tiers'], separators=(',', ':')),
                     visible_observed_at=live['observed_at'],
                     delivery=observed['delivery'], price_status=(
                         'ORDER_ONLY' if observed.get('listed_order_inventory') else
                         'OUT_OF_STOCK' if observed['stock'] == 0 else 'INDICATIVE_PRICE'))
        smt = live['jlc_smt'].get(observed['sku'])
        if smt:
            offer.update(smt_eligibility='DOMESTIC_CATALOG_ONLY', library=smt['library'])
    source = csv_rows(R4 / 'EVT01_BOM_REVIEW.csv')
    parts = {r['reference']:r for r in csv_rows(HERE / 'MIGRATION_LIBRARY_AUDIT.csv')}
    assert len(source) == len(parts) == 212
    exact_count = Counter(row['MPN'] for row in source if row['MPN_state']=='EXACT_CANDIDATE_NOT_RELEASED')
    by_mpn = Counter(row['MPN'] for row in source if row['MPN_state']=='EXACT_CANDIDATE_NOT_RELEASED'
                     and parts[row['ref']]['population']=='FIT')
    for mpn,(sku,brand,url,status) in GLOBAL.items():
        evidence.append(dict(mpn=mpn,sku=sku,manufacturer=brand,url=url,
                             price_status='PRICE_UNKNOWN',checked_at='2026-11-18',
                             failure=status+'; mainland price and stock unobserved'))
    for mpn in sorted(exact_count.keys() - offers.keys() - GLOBAL.keys()):
        evidence.append(dict(mpn=mpn,sku='SKU_UNMATCHED', price_status='PRICE_UNKNOWN',
                             manufacturer=MANUFACTURER.get(mpn,'UNKNOWN'),
                             failure='No verified exact source selected for R5',checked_at='2026-11-18'))
    evidence.append(dict(mpn='IPB017N10N5LFATMA1',sku='SKU_UNMATCHED',manufacturer='Infineon',
                         url='https://www.infineon.com/part/IPB017N10N5LF',
                         price_status='PRICE_UNKNOWN',checked_at='2026-11-18',
                         failure='Q101 engineering research only; excluded from frozen BOM'))
    rows = []
    for item in evidence:
        for nboards in (1, 5, 10):
            need = by_mpn[item['mpn']] * nboards
            moq, stock = item.get('moq'), item.get('stock')
            qty = max(need, moq) if need and isinstance(moq,int) else ''
            if not need:
                purchasable = 'NOT_IN_FITTED_BOM'
            elif qty and isinstance(stock, int):
                purchasable = 'INDICATIVE_STOCK_COVERS_QTY' if qty <= stock else 'INSUFFICIENT_AT_EXPOSED_STOCK'
            else:
                purchasable = 'UNCONFIRMED_AT_ORDER_QTY'
            tiers = live['mainland'].get(item['mpn'],{}).get('tiers',{})
            tier = max((int(n) for n in tiers if qty and int(n) <= qty), default=None)
            rows.append(dict(**item, boards=nboards, needed=need,
                             moq_minimum_purchase_qty=qty, inventory_assessment=purchasable,
                             indicative_tier_threshold=tier or '',
                             indicative_tier_unit_cny=tiers[str(tier)] if tier else 'PRICE_UNKNOWN',
                             checkout_quote_qty='', checkout_unit_cny='PRICE_UNKNOWN'))
    keys = list(dict.fromkeys(k for r in rows for k in r))
    write_csv(HERE / 'LCSC_PRICE_EVIDENCE.csv', [{k:r.get(k,'') for k in keys} for r in rows])
    quote_rows = {r['mpn']:r for r in evidence}
    master = []
    for row in source:
        ref, mpn = row['ref'], row['MPN']
        p = parts[ref]
        q = quote_rows.get(mpn,{})
        tol, rating = RATINGS.get(mpn,('UNKNOWN','UNKNOWN'))
        feature = row['MPN_state']=='PCB_FEATURE'
        quote_status = q.get('price_status','PRICE_UNKNOWN')
        sku = q.get('sku','SKU_UNMATCHED')
        master.append(dict(reference=ref, schematic_name=p['symbol'], manufacturer=q.get('manufacturer',MANUFACTURER.get(mpn,'UNKNOWN')),
                           mpn=mpn, lcsc_sku='NOT_MATERIAL' if feature else sku, value=row['value'],
                           tolerance=tol, ratings=rating, footprint=p['footprint'],
                           catalog_package=q.get('package','UNKNOWN'), population=p['population'],
                           qty_per_board=row['quantity'], fitted_mpn_demand_5boards=by_mpn[mpn]*5 or 'UNRESOLVED_OR_EXCLUDED',
                           moq=q.get('moq','UNKNOWN'), stock=q.get('stock','UNKNOWN'),
                           unit_cny_display=q.get('displayed_unit_cny','PRICE_UNKNOWN'),
                           tier_cny=q.get('tier_prices','UNKNOWN'), tax=q.get('tax','UNKNOWN'),
                           quote_capture=q.get('visible_observed_at',q.get('checked_at','')), url=q.get('url',''),
                           lifecycle=LIFECYCLE.get(mpn,'UNKNOWN'),
                           smt=q.get('smt_eligibility','GLOBAL_CATALOG_ONLY' if mpn=='SN74HCS74DR' else 'UNKNOWN'),
                           smt_library=q.get('library','UNKNOWN'), source_qualification=row['qualification'],
                           confirmation='NOT_MATERIAL' if feature else f'{row["MPN_state"]}/{quote_status}'))
    write_csv(HERE / 'LCSC_BOM_MASTER.csv', master)
    coverage = dict(drawing_rows=len(master), material_rows=sum(r['lcsc_sku']!='NOT_MATERIAL' for r in master),
                    distinct_exact_mpn=len(exact_count), exact_mpn_rows=sum(exact_count.values()),
                    mapped_mpn=len(offers.keys() | GLOBAL.keys()),
                    mapped_refs=sum(exact_count[m] for m in offers.keys() | GLOBAL.keys()),
                    mainland_offer_mpn=len(offers),
                    mainland_offer_refs=sum(exact_count[m] for m in offers),
                    indicative_tier_mpn=len(live['mainland']),
                    domestic_smt_catalog_mpn=len(live['jlc_smt']), checkout_quotes=0,
                    total='TOTAL_COST_UNKNOWN')
    (HERE / 'evidence' / 'cost_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n',encoding='utf-8')
    print(coverage)


if __name__ == '__main__':
    import sys
    main('--refresh' in sys.argv)
