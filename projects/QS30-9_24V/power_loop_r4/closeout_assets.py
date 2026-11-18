"""Review artifacts from actual source data; no fabrication exports."""
from r4lib import *
import csv,xml.etree.ElementTree as ET,itertools,math
def main():
 # Preserve obsolete editable leaf outside the current project; original snapshots remain.
 old=HERE/'EVT01/SAFETY_3.kicad_sch'
 if old.exists():
  dest=HERE/'evidence/superseded_editable_draft';dest.mkdir(exist_ok=True);old.rename(dest/old.name)
  dump(dest/'reason.json',dict(utc=utc(),reason='After removing redundant V5 decap, safety group fits two pages. Root references SAFETY_1/2 only. Prior unreferenced leaf preserved here, not deleted.'))
 sources=[]
 for p in sorted((HERE/'evidence').glob('source_register*.json')):
  x=json.loads(p.read_text());sources.extend(x if isinstance(x,list)else[x])
 urls={r['name']:r for r in sources if r.get('status')=='DOWNLOADED'}
 text=['# 原厂资料核验入口','', '日期2026-11-18。所有下载成功/失败、URL、SHA见source_register*.json；下载成功不等同电气资格。PDF/模型原件不随Git分发。下列仅列实际已取得的资料。','', '|资料|原厂入口|SHA256|','|---|---|---|']
 for name,r in sorted(urls.items()):text.append(f'|{name}|[{name}]({r["url"]})|{r.get("sha256","见登记")}|')
 text+=['','## 关键审查依据','',
 'LM5069：电气特性MIN/TYP/MAX与测试条件，非仅典型波形；LM5164/UCC27511/TPS7A1601/TPS3700/TPS3808/HCS74/14/08：物理针脚和电源范围。TDK B32774D：准确450V10µF条目、105°C降额、70°C10kHz纹波/典型ESR/ESL与机械表。Coilcraft MSS1583：25°C降感定义、DCR与温升电流，未给出本项目完整热态故障资格。',
 '原R3已冻结的ADI LT3757A RevH、ST STP9NK50Z、TPS26601/Vishay US1G/SS14来源及逐针资料继续使用，不伪称本轮重新下载全部。详见R3 MODEL_CREDIBILITY、R1 CONTROLLER_REVIEW及源登记。ST原始宏模型头明确仅25°C，不能给热态SOA资格。',
 'SiC仅深入STPSC4H065D与C3D04065A；较早C3D02060F/STPSC2H065D经生命周期筛掉，未进入四候选深挖。ST原厂v13库完整原字节SHA见ST_model_acquisition*.json与每次preregister。ST模型没有BV/雪崩，不以其低反压数值推断实体雪崩安全。',
 '当前供应商快照单独见verified_cap_supplier.json。厂家产品页403、初始TLS、错误大小写URL404均保留；失败不能改写为已核实。']
 (HERE/'SOURCE_REVIEW.md').write_text('\n'.join(text)+'\n',encoding='utf8')
 d=json.loads((HERE/'EVT01/design_source.json').read_text());critical={'LT3757A','TPS26601','LM5069','LM5164','TPS7A1601','UCC27511','TPS3700','TPS3808','HCS74','HCS14','HCS08','VOS618A','Q','NPN','PNP','D'}
 rows=[]
 for p in d['parts']:
  if p['kind']not in critical:continue
  rows.append(dict(ref=p['ref'],MPN=p['mpn'],kind=p['kind'],physical_pin_functions=';'.join(n+':'+d['types'][p['kind']][n][0]+'='+str(net)for n,net in p['pins'].items()),footprint=p['footprint']or'HOLD',review='Principal physical mapping review; macro-order distinct from package',qualification='HOLD'if'HOLD'in p['status']else'CANDIDATE',scope='Manufacturer pin function and actual native/XML mapping, not independent physical hardware test'))
 with(HERE/'EVT01/manufacturer_pin_review.csv').open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 # Supplement NTC resistor-loading corners omitted from the first nominal-load draft.
 temperatures=[]
 for r25,b,v5,rt,vth,load in itertools.product([9500,10500],[3977*.9925,3977*1.0075],[4.85,5.15],[12000*.99,12000*1.01],[.396,.404],[100900*.99,100900*1.01]):
  parallel=rt*vth/(v5-vth);rntc=1/(1/parallel-1/load);temperatures.append(1/(1/298.15+math.log(rntc/r25)/b)-273.15)
 dump(HERE/'evidence/NTC_loading_corners.json',dict(utc=utc(),trip_C=[min(temperatures),max(temperatures)],first_calculation_used_nominal_load_ohm=100900,full_load_tolerance='.99..1.01 * (90.9k+10k)',V5_assumption='4.85..5.15V analysis bound, not yet realrailguarantee',hotspot_lag_and_cable='UNKNOWN; no thermalqualification'))
 vis=json.loads((HERE/'evidence/visual_review/render_receipt.json').read_text());vis['principal_visual_review']=dict(utc=utc(),observed=['All14pagescontactsheet','FullsizeSAFETY_1','FullsizePOWER_1','FullsizeFRONTEND_1'],findings='Rendered native labels/pins readable, no observed clipping in inspected pages; Q101 DNP visible. Diagram is pin-inventory arrangement, not optimized circuit-flow drawing. Otherpages contact-sheet overview only; this is not exhaustive independent EDA signoff.',GUI='Not observed; first-run privacy/update prompt not acted upon',status='LIMITED_VISUAL_REVIEW/HOLD');dump(HERE/'evidence/visual_review/render_receipt.json',vis)
 svg='''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760"><rect width="1200" height="760" fill="#f3f5f7"/><style>text{font-family:Arial,sans-serif;font-size:19px;fill:#162535}.small{font-size:15px}.box{stroke:#395a72;stroke-width:2}</style><text x="30" y="38" style="font-size:27px">NXT-PWR-EVT01 / R4 — PCB ZONING ONLY / HOLD</text><text x="30" y="70">No board outline, dimensions, insulation clearance or manufacturing rules established.</text><rect x="30" y="110" width="1140" height="570" rx="20" fill="none" stroke="#9a4b30" stroke-width="4" stroke-dasharray="12 8"/><text x="55" y="140">Touch-protection enclosure boundary candidate; all HV interfaces inside enclosure</text><rect class="box" x="60" y="180" width="240" height="180" fill="#e2edf8"/><text x="80" y="213">24V input / fuse / U100</text><text class="small" x="80" y="245">Input bulk and surge return</text><text class="small" x="80" y="273">RTN100 isolated from PGND</text><text class="small" x="80" y="301">Bias branch before U100</text><rect class="box" x="340" y="180" width="280" height="180" fill="#fff2cb"/><text x="360" y="213">Final cut / L / Q / SiC</text><text class="small" x="360" y="245">Q101 and current setting HOLD</text><text class="small" x="360" y="273">Minimize power commutation loop</text><text class="small" x="360" y="301">No fitted L_FEED bulk capacitor</text><rect class="box" x="660" y="180" width="450" height="180" fill="#ffe0d8"/><text x="680" y="213">HV output capacitors / bleed / protected load</text><text class="small" x="680" y="245">Short direct HV return to PGND power star</text><text class="small" x="680" y="273">Heat from bleed separate from NTC electronics</text><text class="small" x="680" y="301">HV connector / cover / discharge qualification HOLD</text><rect class="box" x="60" y="410" width="320" height="180" fill="#dcf0df"/><text x="80" y="443">12V / 5V / monitor / latch</text><text class="small" x="80" y="475">Control and sensor cable routing</text><text class="small" x="80" y="503">Manual START/RESET/STOP at panel</text><text class="small" x="80" y="531">Protected low-voltage observation</text><rect class="box" x="420" y="410" width="330" height="180" fill="#e8e2f6"/><text x="440" y="443">Controller / SENSE Kelvin star</text><text class="small" x="440" y="475">Dedicated shunt top/bottom sense pair</text><text class="small" x="440" y="503">No gate or power return in Kelvin trace</text><text class="small" x="440" y="531">GND_CTRL / GND_DRV net ties at star</text><text x="790" y="450">Thermal / mechanical HOLD</text><text class="small" x="790" y="485">Insulated M3 mounting candidates</text><text class="small" x="790" y="515">No position / metal clearance fixed</text><text class="small" x="790" y="545">Hotspot and heatsink envelope TBD</text><text x="55" y="642">No PCB file, no DRC, no universal 2mm/3mm safety-release spacing.</text><text class="small" x="30" y="720">Clearance/creepage needs working voltage, impulse, pollution, material group, altitude and enclosure basis.</text></svg>'''
 (HERE/'EVT01/PCB_PLAN.svg').write_text(svg,encoding='utf8')
 print(json.dumps(dict(critical_device_pin_rows=len(rows),NTC_trip_C=[min(temperatures),max(temperatures)],native_current_pages=14)))
if __name__=='__main__':main()
