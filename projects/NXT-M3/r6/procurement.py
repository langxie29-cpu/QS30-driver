"""R6 obtains public price metadata using R5's unchanged exact-identity parser."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import csv
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parents[1]/'QS30-9_24V'/'power_loop_r5'/'procurement.py'
spec = importlib.util.spec_from_file_location('r5_procurement', LEGACY)
r5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r5)
sys.path.insert(0,str(HERE/'NXT_M3_EDA'))
from design import parts

LOCAL = {
    'TPS26600RHFR':('2247816','C2155767'),
    'THVD1410DR':('2763260','C2671345'),
    'STP9NK50Z':('39600','C38617'),
    'MSS1583-154KED':('8420123','C7427458'),
    'UCC27511DBVR':('215443','C191027'),
}
CATALOG = {
    'C1206C101JCGACTU':('C2171157','https://www.lcsc.com/product-detail/C2171157.html'),
    'HV5622PG-G':('C220637','https://jlcpcb.com/partdetail/MicrochipTech-HV5622PGG/C220637'),
    'LT3757AEMSE#PBF':('C671464','https://datasheet.lcsc.com/lcsc/2008311906_Analog-Devices-LT3757AEMSE-PBF_C671464.pdf'),
    'TMR 1-1212':('C7401942','https://www.lcsc.com/product-detail/C7401942.html'),
    'STM32C011F4P6':('C5452432','https://www.lcsc.com/product-detail/C5452432.html'),
    'TPS3700DDCR':('C33002','https://www.lcsc.com/product-detail/C33002.html'),
    'UCC27511DBVR':('C191027','https://www.lcsc.com/product-detail/C191027.html'),
    'CD40109BPWR':('296-12163-1-ND','https://www.digikey.cn/zh/products/detail/texas-instruments/CD40109BPWR/412006'),
}

def write_csv(name, rows):
    with (HERE/name).open('w',encoding='utf-8',newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def main():
    archive = HERE/'evidence'/'domestic_prices.json'
    if '--fetch' in sys.argv:
        if archive.exists():
            raise SystemExit('Preserve the existing price snapshot')
        with ThreadPoolExecutor(max_workers=4) as pool:
            fetched = list(pool.map(r5.observe,LOCAL.items()))
        archive.write_text(json.dumps(fetched,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    domestic = {r['mpn']:r for r in json.loads(archive.read_text(encoding='utf-8'))}
    supplement = HERE/'evidence'/'anode_resistor_price.json'
    if '--fetch-anode' in sys.argv and not supplement.exists():
        resistor = r5.observe(('MFR02SF1002A10',('59791','C58746')))
        supplement.write_text(json.dumps(resistor,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if supplement.exists():
        entry = json.loads(supplement.read_text(encoding='utf-8'))
        domestic[entry['mpn']] = entry
    date = '2026-11-19'
    extra = {
        'STORE_QUOTE_HV5622':dict(mpn='HV5622PG-G', sku='USER_REFERENCE', url='User cited Taobao price',
                                  currency='CNY', unit_indication=58.82, status='UNVERIFIED', moq='UNKNOWN', stock='UNKNOWN'),
        'GLOBAL_QUOTE_STM32':dict(mpn='STM32C011F4P6',sku='C5452432',url=CATALOG['STM32C011F4P6'][1],
                                  currency='USD', unit_indication=1.3111, status='PUBLIC_CATALOG_1_PLUS',moq=1,stock=77)
    }
    catalog = []
    for mpn in sorted(set(CATALOG)|set(domestic)):
        live = domestic.get(mpn,{})
        sku, url = CATALOG.get(mpn,('UNKNOWN','UNKNOWN'))
        if live.get('sku'):
            sku, url = live['sku'],live['url']
        catalog.append(dict(mpn=mpn,sku=sku,currency='CNY',unit_indication=live.get('displayed_unit_cny','UNKNOWN'),
                            moq=live.get('moq','UNKNOWN'),stock=live.get('stock','UNKNOWN'),
                            observation_date=live.get('checked_at',date),url=url,
                            status=live.get('price_status','IDENTITY_ONLY'),
                            checkout_price='UNKNOWN',price_context='Public catalogue display; not a quantity-tier or checkout'))
    for row in extra.values():
        catalog.append(dict(row,observation_date=date,checkout_price='UNKNOWN',price_context='Additional channel reference'))
    write_csv('PRICE_EVIDENCE.csv',catalog)
    by_mpn = {r['mpn']:r for r in catalog if r['currency']=='CNY' and r['sku']!='USER_REFERENCE'}
    bom = []
    for part in parts:
        ref = part['ref']
        if ref.startswith('#'):
            continue
        mpn = part['mpn']
        fit = part['status']!='HOLD_DNP' and part['kind']!='HOLE'
        price = by_mpn.get(mpn,{})
        bom.append(dict(ref=ref,mpn=mpn,specification=part['value'],footprint=part['footprint'] or 'HOLD',
                        subsystem=part['group'],fit=fit,qty_1=int(fit),qty_3=3*int(fit),
                        qty_5=5*int(fit),qty_10=10*int(fit),
                        sku=price.get('sku','UNKNOWN'), visible_unit_cny=price.get('unit_indication','UNKNOWN'),
                        moq=price.get('moq','UNKNOWN'), stock=price.get('stock','UNKNOWN'),
                        source=price.get('url',part['source'] or 'UNKNOWN'),status=part['status']))
    for ref,mpn,value,qty in (('TUBES','QS30-1','Nanchang 3 pcs, inventory history',3),
                              ('HOUSING','TBD','Touch protection + mounting hardware',1),
                              ('HARNESS','TBD','Low voltage cables / mating terminals',1),
                              ('HOST','TBD','External source/controller shared per assembly',0)):
        bom.append(dict(ref=ref,mpn=mpn,specification=value,footprint='MECHANICAL',subsystem='INTEGRATION',
                        fit=True,qty_1=qty,qty_3=3*qty,qty_5=5*qty,qty_10=10*qty,
                        sku='UNKNOWN',visible_unit_cny='UNKNOWN',moq='UNKNOWN',stock='UNKNOWN',
                        source='UNKNOWN',status='HOLD'))
    write_csv('PRELIMINARY_BOM.csv',bom)
    filtered = [p for p in bom if p['mpn']!='TBD' and p['ref']!='HOST']
    write_csv('COMPONENT_SELECTION.csv',filtered)
    print(len(bom),'BOM rows',sum(p['visible_unit_cny']!='UNKNOWN' for p in bom),'rows with a public CNY price indication')

if __name__ == '__main__':
    main()
