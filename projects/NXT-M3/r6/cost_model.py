"""CNY planning scenarios. Ranges encode assumptions and may not be purchased."""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

# A and B entries are for nine digits. C and D entries are for one three-digit board.
# Existing tubes, optional tooling and manufacturing are accounted for separately.
DRIVER = 58.82
TUBE = (48,72)      # Replacement allowance per 3; historical 160/9 tubes.
SOCKET = (12,36)    # Candidate holder allowance per 3.
MODELS = {
    'A_24V_R4_R5_CENTRAL': dict(units=1, digits_groups=3, main=(160,360), aux=(50,100),
        safety=(105,220), digital=(55,100), connectors=(55,130), pcb_area=.0232,
        designs=2, joints=(480,600), housing=(85,210), hours=(2.5,5)),
    'B_SIMPLIFIED_CENTRAL': dict(units=1, digits_groups=3, main=(110,190), aux=(50,90),
        safety=(55,115), digital=(35,75), connectors=(35,85), pcb_area=.0162,
        designs=1, joints=(320,430), housing=(70,180), hours=(1.5,3.5)),
    'C_12V_M3': dict(units=3, digits_groups=1, main=(86,149), aux=(50,90),
        safety=(32,65), digital=(24,53), connectors=(14,30), pcb_area=.008075,
        designs=1, joints=(300,350), housing=(30,75), hours=(.7,1.5)),
    'D_24V_M3': dict(units=3, digits_groups=1, main=(80,145), aux=(45,90),
        safety=(36,70), digital=(24,53), connectors=(14,30), pcb_area=.008075,
        designs=1, joints=(300,350), housing=(30,75), hours=(.7,1.5)),
}

def row(model, item, qty, low, high, scope):
    return dict(model=model, item=item, physical_units=qty, low_cny=round(low,2),
                high_cny=round(high,2), basis=scope, order_quote='UNKNOWN')

def collect():
    for name, m in MODELS.items():
        groups = m['digits_groups']
        unit = m['units']
        category = ('main','aux','safety','digital','connectors')
        inc = tuple(sum(m[k][i] for k in category)+groups*(DRIVER+SOCKET[i]+TUBE[i]) for i in range(2))
        cash = tuple(inc[i]-groups*TUBE[i] for i in range(2))
        for k in category:
            yield row(name,k,1,*m[k],'Per board or central nine-digit set, engineering allowance')
        yield row(name,'display_driver_reference',1,groups*DRIVER,groups*DRIVER,'User Taobao reference only')
        yield row(name,'socket_allowance',1,*(groups*x for x in SOCKET),'Per populated board/set')
        yield row(name,'tube_replacement_allowance',1,*(groups*x for x in TUBE),'Historic inventory anchor; new stock unknown')
        yield row(name,'materials_replacement',1,*inc,'Per populated board or central set, protection electronics included')
        yield row(name,'materials_existing_tubes_cash',1,*cash,'Per populated board or central set, tube assets already owned')
        yield row(name,'materials_nine_digits',unit,*(x*unit for x in inc),'Equal nine-digit scope; all components, sockets and tubes')
        yield row(name,'housing_harness_nine_digits',unit,*(x*unit for x in m['housing']),'Touch enclosure, mounting and low-voltage harness allowance')
        for quantity in (5,10):
            board_low, board_high = (quantity*m['pcb_area']*rate for rate in (410,460))
            jmin,jmax = m['joints']
            smt_low = 50*m['designs']+.01*jmin*quantity
            smt_high = 50*m['designs']+.01*jmax*quantity
            labor_low, labor_high = (quantity*m['hours'][i]*rate for i,rate in enumerate((50,100)))
            yield row(name,'pcb_area_reference',quantity,board_low,board_high,'410/460 CNY per m²; excludes minimum, setup, tax and quote')
            yield row(name,'smt_base_reference',quantity,smt_low,smt_high,'Domestic public example rate; excludes extended, THT, fixtures and transport')
            yield row(name,'manual_labor_imputed',quantity,labor_low,labor_high,'Estimated hours valued 50–100 CNY/hour; cash only when paid')
            yield row(name,'manual_consumables',quantity,4*quantity,12*quantity,'Paste, solder, cleaning and rework consumables')
            yield row(name,'respins_and_spares',quantity,100+.15*quantity*cash[0],250+.25*quantity*cash[1],
                      'One board-revision reserve plus 15–25% material allowance')
            include = (quantity*(cash[0]+m['housing'][0]+4)+board_low+100+.15*quantity*cash[0],
                       quantity*(cash[1]+m['housing'][1]+12)+board_high+250+.25*quantity*cash[1])
            yield row(name,'self_build_planning_cash_partial',quantity,*include,
                      'Existing tubes; boards, housing and spares included; pricing/availability unsettled; excludes source/shared host, tax/shipping, verified labor')
            yield row(name,'SMT_planning_cash_partial',quantity,include[0]+smt_low-4*quantity,
                      include[1]+smt_high-12*quantity,
                      'Existing tubes; SMT-base estimate; excludes THT/extended/fixture, external source, shipping and tax')
        yield row(name,'reusable_tooling_if_needed',1,150,450,
                  'SWD dongle + low-voltage interface and fixtures; HV lab equipment and prior assets excluded')

if __name__ == '__main__':
    rows=list(collect())
    with (HERE/'COST_COMPARISON.csv').open('w',newline='',encoding='utf-8') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for item in rows:
        if item['item'] in ('materials_replacement','materials_nine_digits','self_build_planning_cash_partial'):
            print(item['model'],item['item'],item['physical_units'],item['low_cny'],item['high_cny'])
