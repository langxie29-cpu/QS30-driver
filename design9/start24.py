"""Create an isolated 24V project charter, migration inventory and task backlog.

This bootstrap does not generate an electrically revised schematic or PCB.
It refuses to overwrite a previously initialized 24V project.
"""
from pathlib import Path
import csv, hashlib, json, subprocess

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'projects/QS30-9_24V'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8',errors='replace')

TASKS=[
 ('24V-00','P0','初始化独立24V项目与迁移清单','DONE','','项目配置、旧输入哈希和受影响器件表已建立'),
 ('24V-01','P0','冻结输入与系统验收要求','READY','24V-00','输入连续/瞬态、170V容差、启动/纹波/温度、USB模式均记录来源和状态'),
 ('24V-02','P0','重建整机功率及各轨电流预算','READY','24V-00','包含九管/四支泄放/三路分压、3V3、DRV12、控制器、损耗与启动储能；避免重复计费'),
 ('24V-03','P0','重构24V输入保护与输入关断','TODO','24V-01;24V-02','精确MPN、额定/瞬态、反接/浪涌/热插拔、栅压、SOA及短路切断均有计算与验证'),
 ('24V-04','P0','新增12V辅助及受控驱动轨','TODO','24V-01;24V-02','HV5622/转换器/控制门驱负载、PG、时序、默认关闭及异常掉电验证'),
 ('24V-05','P0','重构3V3与USB电源路径','TODO','24V-01;24V-02','比较24→3V3与24→5V→3V3；USB独立供电、反灌、瞬态和完整料号/封装检查'),
 ('24V-06','P0','重选170V功率级并审查C10','TODO','24V-01;24V-02;24V-04','DCM/跨模式策略、电感饱和/DCR、MOS/二极管/电容、门驱、吸收与C10能量有据设计'),
 ('24V-07','P0','重构Kelvin采样、限流和控制模型','TODO','24V-06','弃用SW电压作电流采样；真实阈值/延迟/噪声、CT负载与斜坡、模型来源和步长敏感性通过分层检查'),
 ('24V-08','P0','建立自主启动与闭环正常工作点','TODO','24V-07','无170V预充；正常启动、消隐/单管/九管、输入角点与负载阶跃满足事先登记判据'),
 ('24V-09','P0','重构独立OVP、锁存与安全复位','TODO','24V-03;24V-04;24V-08','反馈开路、MCU死机/复位、失电、硬件复位许可、限流锁存及输入切断动态得到验证'),
 ('24V-10','P0','验证泄放及模块单故障','TODO','24V-06;24V-09','全连接/主板/拆模块、泄放单开路、容差/地线断开/反灌覆盖；触碰要求有来源'),
 ('24V-11','P1','建立24V设计数据源和原生原理图','TODO','24V-03;24V-04;24V-05;24V-06;24V-07','生成器仅写独立项目；逐引脚追踪BOM/网表/原生图；全部旧缺陷显式处置；原生ERC记录完整'),
 ('24V-12','P1','重做MAIN布局与DISPLAY兼容性审核','TODO','24V-08;24V-09;24V-10;24V-11','真实封装、开关/Kelvin回路、热、HV间距/返回地与接口规则冻结；原生DRC和未布线真实报告'),
 ('24V-13','P1','重建固件供电状态机与测试接口','TODO','24V-04;24V-05;24V-09;24V-11','HV请求/PG/BL/故障/复位/掉电状态和96位映射约束一致；MCU不能越过硬件保护'),
 ('24V-14','P1','完成分阶段台架计划及重构交付评审','TODO','24V-10;24V-12;24V-13','低压→独立HV→九管集成的仪器/限流/记录/故障注入清单齐备；未经实测保持HOLD'),
]

if __name__=='__main__':
    assert not PROJECT.exists(), 'Refusing to overwrite existing 24V project'
    for folder in ['docs','config','baseline_snapshot','design','sim','kicad','bom','netlist','sources']:
        (PROJECT/folder).mkdir(parents=True,exist_ok=False)
    paths=git('ls-files','--cached','--others','--exclude-standard','-z').split('\0')
    # Protect design inputs and historical evidence; unrelated attachments/tools
    # are outside this project's inherited electrical baseline.
    protected={p:sha(ROOT/p) for p in paths if p and (ROOT/p).is_file()
               and not p.startswith(('projects/QS30-9_24V/','.codex-attachments/','.docx-work/','output/','tools/'))}
    dump(PROJECT/'baseline_snapshot/baseline.json',dict(date='2026-11-14',timezone='Asia/Shanghai',
         head=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),
         status=git('status','--short'),protected_sha256=protected,
         note='Old 12V design retained; no migrated native project or manufacturing outputs yet'))
    for source,name in [('netlist9/QS30-9_REV.A_netlist.csv','legacy12_netlist.csv'),
                        ('design9/build9.py','legacy12_build9.py.txt'),
                        ('docs9/electrical_sprint04/SPRINT_04_REPORT.md','sprint04_report.md')]:
        (PROJECT/'baseline_snapshot'/name).write_bytes((ROOT/source).read_bytes())
    config=dict(project='QS30-9_24V',revision='R0-DRAFT',date='2026-11-14',
        lifecycle='REFACTOR_STARTED_NOT_ELECTRICALLY_IMPLEMENTED',manufacturing='HOLD',
        inherited_architecture=dict(tubes=9,physical_boards=3,native_project_templates=2,
            drivers='3xHV5622; 96-bit chain; 90 used cathodes; mapping retained pending regression'),
        rails=[dict(name='VIN24',nominal_V=24,status='USER_SELECTED_ARCHITECTURE',
                    continuous_range_V=None,transient_limits_V=None,adapter_mpn=None),
               dict(name='AUX12',nominal_V=12,status='DESIGN_TARGET',purpose='driver and control bias'),
               dict(name='DRV_VDD',nominal_V=12,status='DESIGN_TARGET',purpose='gated HV5622/level-shifter rail'),
               dict(name='3V3',nominal_V=3.3,status='DESIGN_TARGET',purpose='MCU and low-voltage logic'),
               dict(name='HV_BUS',nominal_V=170,status='USER_SELECTED_TARGET_TOLERANCE_PENDING'),
               dict(name='5V_SYS',nominal_V=5,status='USB_PATH_OPTION_PENDING')],
        research_only_input_envelopes_V=[[22.8,25.2],[21.6,26.4]],
        research_only_power_W=dict(HV_typical=4.077596073928697,HV_3mA_per_tube=5.225096073928697),
        unresolved=['input adapter and transients','exact MPNs and verified footprints','actual tube load',
                    '3V3 and AUX12 demand','output tolerance and acceptance limits','USB power architecture',
                    'C10 replacement/retention rationale','CS/protection/bleed known failures'],
        output_policy='Every generator writes only under projects/QS30-9_24V; no imports that execute legacy generation')
    dump(PROJECT/'config/project.json',config)
    with (PROJECT/'docs/TASKS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['id','priority','task','status','dependencies','acceptance']);w.writerows(TASKS)
    rows=list(csv.DictReader((ROOT/'netlist9/QS30-9_REV.A_netlist.csv').open(encoding='utf-8-sig')))
    selected=[r for r in rows if r['net'].startswith('EXT12') or r['net'] in ('HV_IN','DRV_VDD','DRV_VDD_G','HV_EN_G','VREF_UC')]
    with (PROJECT/'docs/LEGACY_POWER_CONNECTIONS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])+['migration_status']);w.writeheader()
        w.writerows(dict(r,migration_status='REVIEW_REQUIRED_NOT_RECONNECTED') for r in selected)
    tasks='\n'.join(f'|{i}|{p}|{t}|{s}|{d or "—"}|' for i,p,t,s,d,a in TASKS)
    (PROJECT/'docs/NEXT_SPRINT.md').write_text('''# 24V完整重构 — Sprint05任务清单

2026-11-14，Asia/Shanghai。用户已选择24V重构方向。本文件定义完整范围及下一轮优先交付，不能把已建立项目框架等同于电路重构完成。

## 下一轮优先范围

完成24V-01/02，推进24V-03/04/05/06至可审查的具体器件/参数及分层电路候选；随后以24V-07单元资格检查决定能否进入24V-08。没有可信工作点时不进行盲目闭环扫参。24V-11的数据模型/生成器隔离可以并行准备，正式连接采用已审查候选；PCB重布依赖后续电气门槛。

必须交付：输入/验收参数登记、全部电源轨功率表、精确MPN与原厂来源矩阵、24V输入与AUX12/3V3/USB候选原理连接、170V功率级及C10/CS处置计算、最小单元验证记录、逐器件迁移清单和下一阶段阻塞项。

## 完整任务分解

|编号|优先级|任务|状态|依赖|
|---|---|---|---|---|
'''+tasks+'''

详细验收条件见TASKS.csv。READY表示可以开始整理，不能视作规格已冻结；TODO也不等于阻塞，依赖可通过设计迭代逐项满足。

## 设计约束与已知问题

- 24V分别进入升压与辅助降压，170V功率级不绕经12V，以保留升压输入提高的收益。
- 三片HV5622保留约12V驱动供电；主板与左右模块的接口逐项审核，不能批量将EXT12替换为EXT24。
- 旧25V输入电容、高侧MOS直接拉栅至地、UC3843直接高压偏置/门驱等都必须显式重新设计。芯片家族名和占位封装不能视作完整选型。
- 旧CS错误、无限流锁存、复位缺许可、C10能量、短路直通、失电/泄放单故障均进入重构范围，不带着FAIL直接沿用。
- 220µH/78kHz与0.15Ω仅为历史研究参数；24V理想满载DCM约51.7%不是已冻结频率、磁件或限流方案。
- 170V为用户选择目标，容差、纹波、过冲、温度与保护触发窗待设计；不继承旧172.18V反馈分压或不自洽的验收窗口。
- 低压路径先比较直接3V3和经5V两级；USB离线编程能力暂作为兼容目标研究，不擅自删除。
- 本轮立项不授权下单、生成制造包或实物高压上电；原有HOLD不因改项目名而关闭。

## 阶段交付

S05：需求/功率/电源树/器件与单元电路。S06：模型资格/自主闭环/完整保护/24V原生原理图。S07：真实封装/PCB/规则与电气一致性。S08：低压、独立HV、九管集成的分阶段实测与交付评审。阶段名称不承诺固定轮数；失败保留证据并先解决依赖。
''',encoding='utf-8')
    (PROJECT/'README.md').write_text('''# QS30-9 — 24V重构项目

状态：R0-DRAFT，已立项并建立独立输入/任务基线；电气实现尚未完成，制造HOLD。

目标：24V输入，170V九管高压，约12V驱动/控制辅助轨，3.3V逻辑；USB/5V路径待方案比较。

- 下一轮与完整任务：[docs/NEXT_SPRINT.md](docs/NEXT_SPRINT.md)
- 机读任务及验收：[docs/TASKS.csv](docs/TASKS.csv)
- 唯一项目参数入口：[config/project.json](config/project.json)
- 旧电源域逐引脚审查入口：[docs/LEGACY_POWER_CONNECTIONS.csv](docs/LEGACY_POWER_CONNECTIONS.csv)
- 12V设计与Sprint04只读来源：baseline_snapshot/；旧电路快照不是24V原理图。

design/sim/kicad/bom/netlist/sources为新版本独立输出区域，目前没有已改造的原生工程。禁止运行旧生成器向旧目录回写；新生成器必须显式绑定本项目目录并验证写入边界。
''',encoding='utf-8')
    changed=[p for p,s in protected.items() if not (ROOT/p).exists() or sha(ROOT/p)!=s]
    manifest=[dict(path=str(p.relative_to(PROJECT)).replace('\\','/'),sha256=sha(p),bytes=p.stat().st_size)
              for p in PROJECT.rglob('*') if p.is_file()]
    dump(PROJECT/'baseline_snapshot/initialization-verification.json',dict(protected_files_checked=len(protected),
        inherited_files_changed=changed,migration_connections=len(selected),migration_components=len({r['ref'] for r in selected}),
        task_count=len(TASKS),initialized=True,electrical_refactor_complete=False,manufacturing='HOLD'))
    dump(PROJECT/'baseline_snapshot/initial-manifest.json',manifest)
    assert not changed
    print(json.dumps(dict(project=str(PROJECT),tasks=len(TASKS),connections=len(selected),
        components=len({r['ref'] for r in selected}),protected_files=len(protected),inherited_changed=changed),ensure_ascii=False))
