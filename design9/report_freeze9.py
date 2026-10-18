"""Generate traceable REV.A9.1 reports from already completed native evidence.

python design9/report_freeze9.py --run rev_a9_1_20261018
Does not run EDA, alter rules, or rewrite historical reports.
"""
import argparse
import collections
import csv
import json
from pathlib import Path
from validate_freeze9 import TUBE_PINS

ROOT = Path(__file__).resolve().parents[1]


def write(name, text):
    (ROOT/name).write_text(text.rstrip()+'\n', encoding='utf-8')


def native_items(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    items = []
    def visit(obj, section='root'):
        if isinstance(obj, dict):
            if 'severity' in obj and 'type' in obj:
                items.append((section,obj))
            else:
                for key,value in obj.items(): visit(value,key)
        elif isinstance(obj,list):
            for value in obj: visit(value,section)
    visit(data)
    return items


FIXES = [
('A91-F01','架构边界','三板两项目，中心显示在MAIN；排除四板描述歧义','G0_ARCHITECTURE.md；F01模板等价'),
('A91-F02','网络标签冲突','按引脚高度分配原理图位置，端点回1.27mm网格；取消固定6列/26mm间距','原生18组合并→0；multiple_net_names 19→0；endpoint_off_grid 799→0'),
('A91-F03','电气连接错误','删除U_C/U_R DIN覆写，三模块均经本地上转换','F07：2条绕行修复'),
('A91-F04','电压域错误','3个DOUT新增CD40109B下转换；分离12V原始DOUT与3V3回线','F07、F09；功能/掉电时序仍A91-E11 HOLD'),
('A91-F05','符号/焊盘映射','生成完整引脚库存，采用原厂管脚名；补回管座1/8、驱动NC与未用输出；PCB/SCH同引用和路径','F03/F06；connected pad mismatch=0；NC另见A91-N04'),
('A91-F06','串行移位映射','更正90条记录的发送序号：每器件先32后1，链最远R先发送','F11独立96级模型；实体walking-one仍HOLD'),
('A91-F07','返回地连接','新增MAIN唯一R_HV_STAR；模块GND_HV不与VSS短接','F10；不是安规或布局放行'),
('A91-F08','默认状态','新增每模块DIN/CLK/LAT/BL/DOUT共15个3V3下拉；U9六个未用输入接地','F07及CSV；瞬态行为待验'),
('A91-F09','料号/封装映射','CD40109BE配SOIC的错误改为CD40109BNSR/SOP-16-NS','TI官方封装表；真实焊盘仍HOLD'),
('A91-F10','验证/证据','新检查采用JSON按severity/type计数、非零违规返回码、逐网络成员比较和PCB焊盘比较、追加式目录','reconcile9.py；旧头部字符串误计error数量不再当真实违规')]

ELECTRICAL = [
('A91-E06','P0','OPEN','电气连接错误','U23.2=VREF_OVP,.3=OVP_SNS；低有效PNP置位与比较器极性相反','先复现，交换输入候选并重验上电/复位','OVP_SIMULATION_INPUTS.md；直流扫描+瞬态/角点'),
('A91-E07','P0','OPEN','电气连接错误/高压风险','Q20源极直地；R36从SW_HV接CS_FILT，缺电流采样分流','重建源极采样、滤波、限流和斜坡补偿','原生MAIN网表；开关SPICE/峰流波形'),
('A91-E08','P0','OPEN','电源引脚/基准冲突','U20.8内部5V输出与U21 TL4312.5V钳位同网VREF_UC','分离5V参考与2.5V基准，不得短接有源输出','TI UC3843表5-1；启动仿真与供电电流'),
('A91-E09','P0','OPEN','电压域/门控错误','R39=100Ω跨HV_EN(3V3输出)与HV_EN_G(EXT12上拉门极)','取消逻辑直连，验证Q5间接驱动和默认关断','原生MAIN网表；请求低/失电注入与反灌电流'),
('A91-E10','P0','HOLD','高压保护/分立锁存','Q21/Q22直接再生路径及复位策略未做BJT级仿真，基极电流无明确限制','真实模型检查限流、锁存保持和过压持续时复位禁止','原生MAIN网表；保存器件电流与COMP/HV峰值'),
('A91-E11','P1','HOLD','未验证时序/电源域','新增CD40109B下转换虽官方支持，累计传播/CLK偏斜/失电行为未测','负载/线长/温度下100kHz测试及先后上电测试；必要时降低频率','TI SCHS099B；96bit逻辑分析仪和掉电波形'),
('A91-E12','P1','HOLD','封装尺寸尚未确认','管座焊脚XY、观察面/触点交叉引出未知；PCB现在是矩形SMD占位','13触点→焊脚实测、坐标/孔径/外形/座高、1:1叠图','QS30_PIN_MAPPING.md；实物通断/治具；H03/H9-03'),
('A91-E13','P0','HOLD','高压安全/连接器','HV2P确切型号DC/瞬态额定、防触碰/爬电未定','厂家壳体/端子/线材成套证据和整机绝缘评审','INTERCONNECT_PINOUT.md；H07/H9-07；耐压及动态过冲验证'),
('A91-E14','P1','HOLD','封装映射/库','PQFP44、SOP16、ESP32、USB、端子等均仍PRELIM矩形占位；电阻串并聚合包非实体封装','按确切订购料号建真实封装；聚合R33/R34/R41/R54及模块泄放拆分；保留引脚号','官方封装图/库验证；PCB原理图一致性和DRC'),
('A91-E15','P0','HOLD','高压安全/规则','默认DRC并非已批准高压间距；板框和回流布局未冻结','按实际环境/材料/器件/瞬态建立净类和间距，审核机壳/地和线束','高压安规设计输入/PCB DRC；不把默认规则PASS当安全'),
('A91-E16','P1','HOLD','未验证警告/软件输入','电气位序已推导，实物管座及walking-one/固件帧未验证','96bit包含6个0备用位；逐管0–9轮测、禁止同管多阴极','QS30_PIN_MAPPING.md；逻辑分析仪/低压夹具/安全高压测试'),
('A91-E17','P1','HOLD','电源引脚类型','HV5622/CD40109/LM393/74HC08已赋电气类型，其余多数符号仍passive','按官方器件功能逐脚赋型；不靠通用passive掩盖驱动冲突','生成器pin_type()审查和完整ERC；关注U20/U21、MCU/电源'),
('A91-E18','P1','OPEN','计算/报告冲突','旧POWER9反馈窗口/模式、泄放τ单位与架构数字有冲突；新转换级也改变BOM/负载','按本轮209器件/三板/实际接线重算，保留旧计算为历史','OVP_SIMULATION_INPUTS.md；重算CSV/BOM/功率和测量'),
('A91-E19','P1','HOLD','保护检测能力','R_SAFE_C只证明板内连通，不证明中心三管装好；安全链阈值及断线动态未测','明确检测覆盖，模拟R57/R58门限、拔线/失地/短接和开关逻辑','F12仅拓扑PASS；故障注入与PG/ALLOW/HV_EN波形')]

TYPE_ROOT = {
 'power_pin_not_driven':('A91-N01','P1','电源引脚类型','未声明供电源，DISPLAY连接器为passive','证明实际电源来源/域后赋正确power_out或边界PWR_FLAG；不能盲加标志'),
 'footprint_link_issues':('A91-N02','P1','符号/封装映射','原理图引用QS30占位库未配置','建立本地库表/经审核封装，保留机械HOLD'),
 'lib_symbol_issues':('A91-N03','P2','符号/封装映射','嵌入符号可加载，但无外部QS30库关联','导出同版本符号库/表并重新ERC'),
 'net_conflict':('A91-N04','P2','可解释但未关闭警告','55个显式NC在原理图导出为独立unconnected网络、PCB对应pad故意无net','逐脚证明确为NC；用正式KiCad更新方式同步未连接网名，保留隔离；不全局忽略'),
 'unconnected_items':('A91-N05','P1','未连接引脚/未布线','PCB无走线，飞线未完成；不是原理图NC标记遗漏','真实封装/布局冻结后布线，重跑DRC并验证导通'),
 'shorting_items':('A91-N06','P0','PCB几何冲突/真实短接','占位焊盘重叠，存在HV/LV等不同网铜短接','重建真实封装/摆放/布线；逐条消除短路后DRC'),
 'clearance':('A91-N07','P0','PCB几何/高压安全','占位焊盘间距不足；尚无HV专用规则','真实布局和经批准高压间距规则后DRC'),
 'copper_edge_clearance':('A91-N08','P1','PCB几何冲突','占位封装铜到板边不足','尺寸/布局冻结后退让并复跑DRC'),
 'solder_mask_bridge':('A91-N09','P1','PCB几何冲突','占位焊盘间阻焊桥冲突','封装焊盘/阻焊尺寸与板厂能力确认后逐条DRC'),
 'lib_footprint_issues':('A91-N10','P1','封装尺寸尚未确认','板载占位封装未关联已配置库，含安装孔','正式本地封装库/表；官方尺寸及实物核对后DRC')}


def main(run):
    folder=ROOT/'kicad/logs'/run
    current=json.loads((folder/'results.json').read_text(encoding='utf-8'))
    baseline=json.loads((ROOT/'kicad/logs/before_a9_1_complete/results.json').read_text(encoding='utf-8'))
    audit=json.loads((folder/'electrical_audit.json').read_text(encoding='utf-8'))
    mapping=list(csv.DictReader((ROOT/'docs9/channel_map9.csv').open(encoding='utf-8-sig')))
    prefix=f'../kicad/logs/{run}'
    pintext=['# REV.A9.1 QS30-1 电气与串行映射','',
      '原厂首要证据：南昌电子管厂说明书电极接线图，仓库原始扫描 [整页](../docs/source_scans/QS30-1_原厂说明书_p1_外形与电极接线图.png)、[放大图](../docs/source_scans/QS30-1_电极接线图_放大.png)。本轮直接读图核对，不使用通用管座顺序推导。',
      '', '原厂管脚号→原理图符号脚号已冻结。逻辑焊盘号意图为同号1:1；**实际管座触点→PCB焊脚关系、XY、镜像/观察面未实测，机械封装HOLD**。PCB中的同号矩形SMD焊盘只是电气占位，不能证明实际插座焊脚号已确认。1/8在原图没有显示电极标注；本设计保持悬空，不推断其内部用途，更不接地。',
      '', '| 原厂脚号 | 电极 | 原理图脚号 | PCB逻辑焊盘号 | 实际管座焊脚 |', '|---|---|---|---|---|']
    pin_names={1:'未标显示电极，保持悬空',2:'A',8:'未标显示电极，保持悬空',**{p:f'K{d}' for d,p in TUBE_PINS.items()}}
    for p in range(1,14): pintext.append(f'| {p} | {pin_names[p]} | {p} | {p}'+('（无net）' if p in (1,8) else '')+' | HOLD：需触点→焊脚通断与观察面 |')
    pintext += ['', 'HV5622PG-G官方依据：[DS20005854A](https://ww1.microchip.com/downloads/en/DeviceDoc/20005854A.pdf) Table2-1、3-2，已归档PDF/哈希。HVOUT1…22→PQFP脚22…1；HVOUT23…32→44…35。CLK28下降沿、DIN32、DOUT23、LE31、BL33、POL27、VDD30、VSS29；24/25/26/34为NC。未使用HVOUT31/32（脚36/35）开路不接地；数据位恒0是本设计策略，并非虚构手册的接地要求。',
      '', '## 90路完整映射', '', '引用均为DesignRef；对应KiCad U/J序号见原生网表组件的DesignRef属性和electrical_audit.json.references。T1–3左、T4–6中央、T7–9右。序号0是整帧最先发送位；byte为0基，bit为字节内7…0；frame_bit为96位整数的95…0位。', '',
      '| 管 | 数字 | 驱动 | HVOUT | PQFP脚 | 管脚/符号脚/逻辑pad | 网络 | 发送序号 | frame_bit | byte.bit | 证据 |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in mapping:
        pintext.append(f"| T{r['tube']} | {r['digit']} | {r['device']} | {r['hvout']} | {r['driver_pin']} | {r['socket_pin']} | {r['cathode_net']} | {r['serial_index']} | {r['frame_bit']} | {r['byte']}.{r['bit_in_byte']} | {'原生' if r['module']!='R' else 'DISPLAY模板等价'} |")
    pintext += ['', '## 6个未用位与初始化', '', '| 驱动 | HVOUT/PQFP脚 | 发送序号 | 数据 |', '|---|---|---|---|', '| U_R | 32/35，31/36 | 0，1 | 0，0 |', '| U_C | 32/35，31/36 | 32，33 | 0，0 |', '| U_L | 32/35，31/36 | 64，65 | 0，0 |', '',
      '每帧12字节，按R32→R1、C32→C1、L32→L1传输。POL接VDD，BL低强制全关，BL高且锁存位1时开漏导通；LE高透明装载、低保持。软件先BL低→96个0→锁存→仍保持禁止HV；低压台架及walking-one确认后才允许点亮。独立96级移位模型F11通过，实际时序/管座接线/点亮实验仍HOLD。', '',
      '9个阳极：每管单独 HV_BUS→R_ANn_1(10kΩ)→A_Tn_MID→R_ANn_2(10kΩ)→A_Tn→J_Tn.2；每支20kΩ，9支/18电阻。原生网表加右模板审计逐支通过，不经过HV5622预算。', '',
      f'审计：[electrical_audit.json]({prefix}/electrical_audit.json)，CSV源 [channel_map9.csv](channel_map9.csv)。60通道为两板原生实际网络，右30通道为同一DISPLAY模板等价实例；没有声称另开第三套KiCad项目验证。']
    write('docs9/QS30_PIN_MAPPING.md','\n'.join(pintext))

    nettext=['# REV.A9.1 原生网表收敛记录','', f'真实工具 KiCad {current["kicad_version"]}；日期2026-10-18；制造/高压调试HOLD。输入哈希、全部argv/输出/返回码见 [{run}/results.json]({prefix}/results.json) 和 commands.log。旧根目录报告/网表不覆盖；b6a9082关键文件逐字节备份及SHA256在kicad/logs/b6a9082_evidence/。', '',
      '## 实测数量', '', '| 板 | 修前预期/原生有效网 | 修前名称一致/节点 | 修后预期/有效网 | 独立NC网 | 原生总网/总节点 | 修后已连接节点一致 | 合并/拆分/PCB已连接焊盘差异 |', '|---|---|---|---|---|---|---|---|']
    for b,v in current['boards'].items():
        old=baseline['boards'][b]
        nettext.append(f"| {b} | {old['expected_nets']}/{old['actual_nets']} | {old['matched_nodes']}/{old['expected_nodes']} | {v['expected_nets']}/{v['connected_actual_nets']} | {v['explicit_nc_nets']} | {v['actual_nets']}/{v['actual_nodes']} | {v['matched_nodes']}/{v['expected_nodes']} | {len(v['merges'])}/{len(v['splits'])}/{len(v['pcb_pad_mismatches'])} |")
    nettext += ['', 'NC是原生KiCad为显式no_connect引脚导出的unconnected-*单节点网，不是有效通道。DISPLAY17、MAIN38项均与完整引脚库存一致，逐项隔离。有效网络53/132的变化来自真实新增转换/偏置、门控未用输入和主板地桥。旧134/500节点全部存在仍发生18组合并、428条名称不符；同节点数量不能证明电气正确。', '',
      '根因是生成器固定26mm行距且未按长符号分配高度，导线可重叠跨入另一符号；另有端点不在网格。此次修复布局生成算法，所有有效网络成员按集合比较，0合并、0拆分、0缺失、0意外连接；不通过改CSV名称迎合原生错误网络。原生multiple_net_names由19变0、off-grid由799变0。', '',
      '逐输出核对90项、每个阴极恰好(驱动脚,管座脚)两端点；9条独立阳极支路；6未用输出；36个连接器配对；DIN/CLK/LE/BL/串行回线、5种电源地组及唯一地桥均有机器审计。右模块是已核对DISPLAY等价模板，不是额外原生项目。参见QS30_PIN_MAPPING、INTERCONNECT_PINOUT及F01–F12审计。', '',
      'PCB与原理图统一Reference、DesignRef与symbol path；已连接焊盘网络逐引脚相等，**这不消除几何上的铜短接**。本轮开启--schematic-parity；其55个net_conflict都是原理图显式NC名与PCB无net焊盘的差异，单列A91-N04，不忽略；其余PCB短路/间距/未布线见问题清单。', '',
      '## 原生ERC/DRC（JSON实际条目，不数报告标题字符串）', '', '| 板 | 修前ERC错误/警告 | 本轮ERC错误/警告 | 修前DRC错误/警告 | 本轮DRC错误/警告 |', '|---|---|---|---|---|']
    for b,v in current['boards'].items():
        old=baseline['boards'][b]
        fmt=lambda x:f"{x['severity'].get('error',0)}/{x['severity'].get('warning',0)}"
        nettext.append(f"| {b} | {fmt(old['erc'])} | {fmt(v['erc'])} | {fmt(old['drc'])} | {fmt(v['drc'])} |")
    nettext += ['', '两板sexpr/XML导出均rc=0；ERC与DRC（report/json各执行）均rc=5，明确FAIL。以前ERC/DRC rc=0只表示命令正常结束，未启用违规退出；旧脚本用error/错误/violation全文匹配还误计标题。此次未修改任何规则严重度、未增加排除或跳过检查；默认KiCad ignored_checks清单亦保留。', '',
      '## 实际执行与可重跑方式', '', '```text', 'git status --short', 'git log -6 --oneline', 'git switch -c rev-a9-1-electrical-freeze', 'python design9/reconcile9.py --run before_a9_1_complete  # rc=1：证实基线网络错误', 'python design9/freeze9.py                           # rc=0', 'python design9/kicad_gen.py                         # rc=0', f'python design9/kicad_check.py --run {run} --publish  # rc=0：拓扑收敛，不是ERC/DRC通过', f'python design9/validate_freeze9.py --run {run}       # rc=0：12/12结构核对', f'python design9/report_freeze9.py --run {run}', '```', '',
      '原生命令模板（每板均实际执行sexpr、XML、ERC report/json、DRC report/json，确切绝对路径与rc见commands.log）：', '', '```text', 'kicad-cli sch export netlist --format kicadsexpr -o <new-run>/<board>.net <board>.kicad_sch', 'kicad-cli sch export netlist --format kicadxml -o <new-run>/<board>.xml <board>.kicad_sch', 'kicad-cli sch erc --format report|json --severity-all --exit-code-violations -o <new-run>/<board>.erc.rpt|json <board>.kicad_sch', 'kicad-cli pcb drc --schematic-parity --format report|json --severity-all --exit-code-violations -o <new-run>/<board>.drc.rpt|json <board>.kicad_pcb', '```', '',
      '证据过程：before_a9_1首次捕获在Python读取kiutils properties时异常（非KiCad错误），已保留6份DISPLAY原生输出；before_a9_1_complete修复后完整捕获。after_a9_1和after_a9_1_final是中间版本，均保留；最终以本文件run为准。目录已存在时脚本拒绝覆盖。新运行使用新的--run名称，不可重复覆盖本run。未生成Gerber/钻孔等制造文件，未下单，未运行SPICE。']
    write('docs9/NETLIST_RECONCILIATION.md','\n'.join(nettext))

    issues=[]
    totals=collections.Counter()
    for board in current['boards']:
        for kind in ('erc','drc'):
            filename=f'{board}.{kind}.json'
            for index,(section,item) in enumerate(native_items(folder/filename),1):
                root,priority,category,cause,action=TYPE_ROOT[item['type']]
                totals[root]+=1
                issues.append(dict(id=f'A91-{board.removeprefix("QS30-9_")}-{kind.upper()}-{index:04d}',root_id=root,
                                   severity=item['severity'],priority=priority,category=category,type=item['type'],
                                   evidence=f'kicad/logs/{run}/{filename}#{section}:{index}',
                                   description=item['description'],items=json.dumps(item.get('items',[]),ensure_ascii=False),
                                   action=action,verification='Rerun full native '+kind.upper()+'; retain old evidence'))
    with (ROOT/'docs9/EDA_ISSUES_NATIVE.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(issues[0]));w.writeheader();w.writerows(issues)
    issue=['# REV.A9.1 EDA问题登记表','', '优先级：P0=禁止高压/制造的危险或功能根本错误；P1=电气/布局签核前必须处理；P2=可解释、可追溯的库/命名警告。FIXED仅指该项架构/接线更正经指定验证，绝非整机批准。OPEN=已证实待修；HOLD=缺证据/模型/实物。责任归后续电气设计与机械/高压审核；本轮不批量忽略警告。', '',
      '## 已完成10项根因修复', '', '| ID | 等级 | 状态 | 分类 | 变更/措施 | 验证/证据 |', '|---|---|---|---|---|---|']
    for row in FIXES:
        priority = 'P0' if row[0] in ('A91-F02','A91-F03','A91-F04','A91-F07') else 'P1'
        issue.append('| '+' | '.join((row[0],priority,'FIXED',*row[1:]))+' |')
    issue += ['', '## 原生违规逐项归档与根因', '', f'本轮共 **{len(issues)}** 条原生违规，每条已赋独立ID、严重度、原始JSON证据/对象坐标、措施/验证方式，见 [EDA_ISSUES_NATIVE.csv](EDA_ISSUES_NATIVE.csv)。下表是根因索引，不替代逐条清单；同一根因可对应多条报告。', '', '| 根因ID | 级别 | 分类 | 条数 | 根因/证据 | 措施/验证 |', '|---|---|---|---|---|---|']
    for typ,(rid,priority,category,cause,action) in TYPE_ROOT.items():
        issue.append(f'| {rid} | {priority} | {category} | {totals[rid]} | `{typ}`：{cause} | {action}；完整原生检查 |')
    issue += ['', 'A91-N04的55个NC警告可按设计意图解释，但未标为关闭；A91-N06的几何短路即使连接属性一致仍是真实铜短接风险。不可用拓扑PASS覆盖DRC FAIL。', '',
      '## 原生检查不能自动发现/证明的问题', '', '| ID | 等级 | 状态 | 分类 | 证据/风险 | 修复措施 | 验证 |', '|---|---|---|---|---|---|---|']
    for row in ELECTRICAL: issue.append('| '+' | '.join(row)+' |')
    issue += ['', '旧H03/H9-03、H07/H9-07与旧E02–E05的HOLD未解除；旧AUDIT/FAIL原文全部保留。新增保护问题与旧“STRONGLY SUPPORTED”结论冲突时采用此表更保守的OPEN/HOLD状态。', '', '## 本轮停止条件', '', '| 问题 | 答案 |', '|---|---|', '| 1 九位三板明确？ | 是，左3/MAIN含中3/右3，两套项目 |', '| 2 90阴极完整？ | 是，60路原生+30路同模板等价，90条脚号/位序表；实物walking-one HOLD |', '| 3 9独立阳极？ | 是，每管两只10k串联，9支/18电阻，不计阴极预算 |', '| 4 三板接口一致？ | 是，左右36配对针逐项匹配；中央同信号板内连接 |', '| 5 原理图和网表可解释？ | 是，有效网/节点/成员及PCB已连接pad相等；55个NC命名差异单列，几何短路仍在 |', '| 6 机械哪些待量？ | 管座触点↔焊脚/XY/观察面/座高，HV/LV连接器确切型号/安装方向，所有PRELIM需真实封装审核 |', '| 7 哪些是真实电气风险？ | E06–E10模拟电路与门控、E13/E15高压安全、N06/N07铜短接/间距；详见本表 |', '| 8 OVP下一步输入？ | OVP_SIMULATION_INPUTS.md：当前错误拓扑、模型、数值/公差、负载/失效角点及必存波形；未执行SPICE |']
    write('docs9/EDA_ISSUE_REGISTER.md','\n'.join(issue))
    # The old summary remains immutable; put a new dated index beside it.
    write('kicad/EDA_CHECK_RESULTS_A9_1.md', '# REV.A9.1 native checks\n\nCurrent machine index: eda_check_results.json\n\n'+f'Evidence: logs/{run}/; reconciliation {audit["status"]}; ERC FAIL; DRC FAIL; manufacturing HOLD.\n\n'+
          'Detailed counts/commands: ../docs9/NETLIST_RECONCILIATION.md\n\nIssues: ../docs9/EDA_ISSUE_REGISTER.md')
    # machine-readable interface copy with full engineering fields
    interface=[]
    for pin,signal,direction,domain,default,floating,fault in [
        (1,'3V3','MAIN->MOD','3V3','supply established','NO','loss disables LS; transient HOLD'),
        (2,'GND','RETURN','GND','bond MAIN','NO','loss of reference/cathode return'),
        (3,'DRV_VDD','MAIN->MOD','10.8-13.2V','OFF','NO','PG/HV disable required; E09 OPEN'),
        (4,'GND','RETURN','GND','bond MAIN','NO','same net as pin2'),
        (5,'MOD_x_DIN','MAIN->MOD','3V3','100k pulldown','NO','no valid frame'),
        (6,'MOD_x_DOUT','MOD->MAIN','3V3','100k pulldown','ONLY terminal consumer optional','raw DOUT requires DS'),
        (7,'DISP_CLK','MAIN->MOD','3V3','100k pulldown','NO','no valid frame'),
        (8,'DISP_LAT','MAIN->MOD','3V3','100k pulldown','NO','hold latch'),
        (9,'DISP_ALLOW','MAIN->MOD','3V3','100k pulldown','NO','BL=0 all OFF with POL=HIGH'),
        (10,'SAFETY_LOOP_x_IN','MAIN->MOD','3V3','R57 source','NO','open forces terminal LOW'),
        (11,'SAFETY_LOOP_x_OUT','MOD->MAIN','3V3','0ohm link from10','NO','R58 terminal pulldown')]+[
        (p,'GND','RETURN','GND','bond MAIN','NO','same net as pin2') for p in range(12,17)]:
        interface.append(dict(connector='LV16P',pin=pin,signal=signal,direction=direction,domain=domain,
                              default=default,may_float=floating,fault=fault,relationship='MAIN_L/R pinN <-> MOD_L/R pinN; C internal'))
    for pin,signal,direction,domain,default,fault in [(1,'HV_BUS','MAIN->MOD','172.18V nominal; peak TBD','OFF','OVP E06-E10 OPEN'),(2,'GND_HV','MOD->MAIN','HV capacitor/bleeder return','MAIN star bond','NO module GND bond')]:
        interface.append(dict(connector='HV2P',pin=pin,signal=signal,direction=direction,domain=domain,default=default,may_float='NO',fault=fault,relationship='same pin both ends; actual rating UNKNOWN; target >=300V DC'))
    with (ROOT/'docs9/interface9.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(interface[0]));w.writeheader();w.writerows(interface)
    # Current index is a derived review, raw native run/results.json stays immutable.
    current['review'] = dict(overall_status='HOLD', manufacturing='HOLD', native_erc='FAIL', native_drc='FAIL',
                            electrical_topology=audit['status'], checks_passed=sum(c['status']=='PASS' for c in audit['checks']),
                            checks_total=len(audit['checks']), fixed_roots=len(FIXES),
                            remaining_native_violations=len(issues), remaining_native_root_groups=len(totals),
                            remaining_electrical_roots=len(ELECTRICAL), evidence=f'kicad/logs/{run}',
                            audit=f'kicad/logs/{run}/electrical_audit.json', issues='docs9/EDA_ISSUES_NATIVE.csv')
    write('kicad/eda_check_results.json',json.dumps(current,ensure_ascii=False,indent=2))
    print(f'Wrote mapping/netlist/issue reports, {len(issues)} individually identified native violations, 10 fixed roots, {len(ELECTRICAL)} open/HOLD electrical roots')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);args=parser.parse_args();main(args.run)
