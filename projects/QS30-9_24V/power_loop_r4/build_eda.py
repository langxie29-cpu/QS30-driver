"""Generate native KiCad hierarchical schematics. Device-level symbols with typed pins."""
from r4lib import *
import math,uuid,collections,re
OUT=HERE/'EVT01';PROJECT='NXT-PWR-EVT01'
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'qs30/r4/evt01/'+s))
def q(s):return json.dumps(str(s),ensure_ascii=True)
def effects(size=1,extra=''):return f'(effects(font(size {size} {size})){extra})'
def pinlayout(pins):
 keys=list(pins);n=math.ceil(len(keys)/2);rows=max(n,len(keys)-n);h=max(5.08,(rows+1)*2.54)
 out={}
 for i,k in enumerate(keys):
  side=-1 if i<n else 1;j=i if i<n else i-n
  out[k]=(side*20.32,(rows-1)*1.27-j*2.54,0 if side<0 else 180)
 return out,h
def symdef(name,pins,embedded=False):
 positions,h=pinlayout(pins);sid='NXT:'+name if embedded else name
 fields=f'(property "Reference" "U" (at 0 {h/2+3} 0){effects()})(property "Value" {q(name)}(at 0 {-h/2-3} 0){effects()})'
 if len(pins)==2 and name=='R':shape='(rectangle(start -3.81 1.27)(end 3.81 -1.27)(stroke(width .254)(type default))(fill(type none)))'
 elif len(pins)==2 and name=='C':shape='(polyline(pts(xy -1.27 2.54)(xy -1.27 -2.54))(stroke(width .254)(type default))(fill(type none)))(polyline(pts(xy 1.27 2.54)(xy 1.27 -2.54))(stroke(width .254)(type default))(fill(type none)))'
 else:shape=f'(rectangle(start -15.24 {h/2})(end 15.24 {-h/2})(stroke(width .254)(type default))(fill(type background)))'
 if name in ['R','C']:
  a=-3.81 if name=='R'else -1.27;b=3.81 if name=='R'else 1.27
  shape+=f'(polyline(pts(xy -15.24 0)(xy {a} 0))(stroke(width .254)(type default))(fill(type none)))(polyline(pts(xy {b} 0)(xy 15.24 0))(stroke(width .254)(type default))(fill(type none)))'
  positions={k:(x,0,ang)for k,(x,y,ang)in positions.items()}
 body=[]
 for k,(x,y,angle)in positions.items():
  label,kind=pins[k];body.append(f'(pin {kind} line(at {x} {y} {angle})(length 5.08)(name {q(label)} {effects(.85)})(number {q(k)} {effects(.85)}))')
 return f'(symbol {q(sid)}(pin_names(offset .8))(exclude_from_sim no)(in_bom yes)(on_board yes){fields}(symbol {q(name+"_0_1")}{shape})(symbol {q(name+"_1_1")}{"".join(body)}))',positions,h
def text(s,x,y,size=1.2):return f'(text {q(s)}(at {x} {y} 0){effects(size,"(justify left)")}(uuid {q(uid(s+str(x)+str(y)))}))'
def generate():
 d=json.loads((OUT/'design_source.json').read_text(encoding='utf8'));types=d['types'];parts=d['parts']
 library=['(kicad_symbol_lib(version 20250114)(generator "kicad_symbol_editor")']
 for name,pins in types.items():library.append(symdef(name,pins)[0])
 library.append(')');(OUT/'NXT.kicad_sym').write_text('\n'.join(library),encoding='utf8')
 (OUT/'sym-lib-table').write_text('(sym_lib_table(version 7)(lib(name "NXT")(type "KiCad")(uri "${KIPRJMOD}/NXT.kicad_sym")(options "")(descr "R4 device pin definitions; manufacturing HOLD")))',encoding='utf8')
 groups=collections.defaultdict(list)
 for p in parts:groups[p['group']].append(p)
 sheets=[];rootid=uid('ROOT')
 for group in ['INPUT','FRONTEND','AUX','POWER','MONITORS','SAFETY','INTERFACES']:
  for start in range(0,len(groups[group]),20):sheets.append((group+'_'+str(start//20+1),groups[group][start:start+20]))
 for page,(name,ps)in enumerate(sheets,2):
  sid=uid('sheet-'+name);used={p['kind']for p in ps};lib=''.join(symdef(k,types[k],True)[0]for k in sorted(used))
  content=[f'(kicad_sch(version 20250114)(generator "eeschema")(uuid {q(uid("file-"+name))})(paper "A3")(title_block(title {q(PROJECT+" / "+name)})(rev "R4-DRAFT-HOLD")(comment 1 "No manufacture/HV authorization. Q101 DNP; HOLD inputs pulled LOW."))(lib_symbols {lib})']
  content.append(text('R4 ENGINEERING CANDIDATE - ALL SAFETY / MANUFACTURING HOLD RETAINED',12,12,1.5))
  content.append(text('Physical pin inventory / explicit net labels. No PCB / no DRC. See design_source.json and review reports.',12,19,1.0))
  for i,p in enumerate(ps):
   x=55.88+(i%4)*101.6;y=50.8+(i//4)*45.72
   kind=p['kind'];_,positions,h=symdef(kind,types[kind],True);ref=p['ref'];value=p['value'];flag=kind=='FLAG';dnp=p['status'].startswith('HOLD_DNP')
   elem=f'(symbol(lib_id {q("NXT:"+kind)})(at {x} {y} 0)(unit 1)(exclude_from_sim no)(in_bom {"no"if flag else"yes"})(on_board {"no"if flag else"yes"})(dnp {"yes"if dnp else"no"})(uuid {q(uid(ref))})'
   for prop,val,px,py,hide,size in [('Reference',ref,x,y-h/2-5,False,1.05),('Value',value,x,y-h/2-2,False,.9),('Footprint',p['footprint'],x,y,True,1),('Datasheet',p['source'],x,y,True,1),('MPN',p['mpn'],x,y,True,1),('Status',p['status'],x,y,True,1),('Notes',p['note'],x,y,True,1)]:
    elem+=f'(property {q(prop)} {q(val)}(at {px} {py} 0)(effects(font(size {size} {size})){"(hide yes)"if hide else""}))'
   for k in p['pins']:elem+=f'(pin {q(k)}(uuid {q(uid(ref+"/"+k))}))'
   elem+=f'(instances(project {q(PROJECT)}(path {q("/"+rootid+"/"+sid)}(reference {q(ref)})(unit 1)))))';content.append(elem)
   for k,net in p['pins'].items():
    xx,yy,angle=positions[k];px=x+xx;py=y-yy
    if net is None:content.append(f'(no_connect(at {px} {py})(uuid {q(uid(ref+"/NC/"+k))}))');continue
    tx=px+(-2.54 if xx<0 else 2.54);justify='right'if xx<0 else'left'
    content.append(f'(wire(pts(xy {px} {py})(xy {tx} {py}))(stroke(width 0)(type default))(uuid {q(uid(ref+"/wire/"+k))}))')
    content.append(f'(global_label {q(net)}(shape bidirectional)(at {tx} {py} 0){effects(.85,"(justify "+justify+")")}(uuid {q(uid(ref+"/label/"+k))})(property "Intersheetrefs" "${{INTERSHEET_REFS}}"(at {tx} {py} 0)(effects(font(size .8 .8))(hide yes))))')
   if 'HOLD'in p['status']:content.append(text(p['status'],x-32,y+h/2+4,.8))
  content.append(')');(OUT/(name+'.kicad_sch')).write_text('\n'.join(content),encoding='utf8')
 root=[f'(kicad_sch(version 20250114)(generator "eeschema")(uuid {q(rootid)})(paper "A3")(title_block(title "NXT-PWR-EVT01")(rev "R4-DRAFT-HOLD")(comment 1 "Engineering inspection candidate; NOT manufacturing or HV release"))(lib_symbols)']
 root+=[text('NXT-PWR-EVT01 / R4 / DESIGN CANDIDATE - HOLD',15,14,2),text('Authority: KiCad 10.0.8 native hierarchy. Child sheets contain device pins / actual named nets.',15,22,1.2),text('Q101 is deliberately DNP with no selected MPN. No deliberate L_FEED bulk capacitor. All HOLD enables are pulled LOW.',15,29,1.0),text('TPS26601 U100 main input; LM5069-1 candidate branch. Loaded gateoff / SOA / hot magnetics remain unqualified.',15,35,1.0)]
 for i,(name,ps)in enumerate(sheets):
  x=20+(i%3)*130;y=50+(i//3)*42
  root.append(f'(sheet(at {x} {y})(size 113 30)(stroke(width .254)(type default))(fill(color 0 0 0 0))(uuid {q(uid("sheet-"+name))})(property "Sheetname" {q(name)}(at {x} {y-1} 0){effects(1.1,"(justify left)")})(property "Sheetfile" {q(name+".kicad_sch")}(at {x} {y+31} 0){effects(.85,"(justify left)")}))')
 root.append('(sheet_instances(path "/"(page "1")))');root.append(')')
 (OUT/(PROJECT+'.kicad_sch')).write_text('\n'.join(root),encoding='utf8')
 dump(OUT/(PROJECT+'.kicad_pro'),dict(meta=dict(filename=PROJECT+'.kicad_pro',version=1),erc=dict(erc_exclusions=[],meta=dict(version=0)),text_variables=dict(QUALIFICATION='ALL_HOLD',AUTHORITY='R4_KICAD_10.0.8'),schematic=dict(meta=dict(version=1))))
 libraries={p['footprint'].split(':')[0]for p in parts if p['footprint']}
 table='(fp_lib_table(version 7)'+''.join(f'(lib(name {q(n)})(type "KiCad")(uri {q("${KICAD10_FOOTPRINT_DIR}/"+n+".pretty")})(options "")(descr "Installed KiCad10 footprint, verifymechanically before manufacture"))'for n in sorted(libraries))+')'
 (OUT/'fp-lib-table').write_text(table,encoding='utf8')
 libroot=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints');missing=[];footprints=[]
 for p in parts:
  if p['footprint']:
   lib,fp=p['footprint'].split(':');f=libroot/(lib+'.pretty')/(fp+'.kicad_mod')
   if not f.exists():missing.append(dict(ref=p['ref'],footprint=p['footprint']))
   else:
    pads=set(re.findall(r'\(pad\s+"([^\"]+)"',f.read_text(encoding='utf8')));expected=set(p['pins']);footprints.append(dict(ref=p['ref'],footprint=p['footprint'],sha256=sha(f),pads=sorted(pads),symbol_pins=sorted(expected),padset_matches=pads==expected,qualification='Padnumbers only; exactland/thermal/mechanical qualifications separately reviewed'))
 dump(OUT/'footprint_audit.json',dict(missing_files=missing,records=footprints,scope='Installed library existence and actual pad numbers, not full footprint or PCB qualification'))
 dump(OUT/'generation_receipt.json',dict(native_sheets=len(sheets)+1,parts=len(parts),pins=sum(len(p['pins'])for p in parts),symbols_sha256=sha(OUT/'NXT.kicad_sym'),missing_footprint_files=missing,PCB_present=False,DRC_performed=False,manufacturing='HOLD'))
 print(json.dumps(dict(sheets=len(sheets)+1,parts=len(parts),missing_footprint_files=missing)))
if __name__=='__main__':generate()
