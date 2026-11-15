"""Build the NXT teaching book from its reviewed Markdown manuscript.

Run with the Codex bundled Python.  The engineering inputs are read only.
"""
from pathlib import Path
import re, math, json, hashlib, sys
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, PageBreak, CondPageBreak, Table, TableStyle, Image, KeepTogether, Flowable)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Line, Rect, String, PolyLine, Polygon, Circle

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'NXT工程进展与知识_第一版.pdf'
QA=ROOT/'.docx-work'/'nxt-book'
QA.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Song','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('HeiBold','C:/Windows/Fonts/msyhbd.ttc',subfontIndex=0))
pdfmetrics.registerFontFamily('Song',normal='Song',bold='HeiBold',italic='Song',boldItalic='HeiBold')
pdfmetrics.registerFontFamily('Hei',normal='Hei',bold='HeiBold',italic='Hei',boldItalic='HeiBold')
MM=72/25.4
W,H=A4
LEFT,RIGHT,TOP,BOTTOM=25*MM,18*MM,22*MM,20*MM
CW=W-LEFT-RIGHT
ink=colors.HexColor('#202020'); gray=colors.HexColor('#666666')
light=colors.HexColor('#D9D9D9'); pale=colors.HexColor('#F3F3F3')

styles={
 'body':ParagraphStyle('Body',fontName='Song',fontSize=11.5,leading=18.5,
    spaceAfter=8,wordWrap='CJK',textColor=ink,allowWidows=0,allowOrphans=0),
 'h1':ParagraphStyle('H1',fontName='HeiBold',fontSize=21,leading=30,spaceAfter=20,
    wordWrap='CJK',textColor=colors.black,keepWithNext=True),
 'h2':ParagraphStyle('H2',fontName='HeiBold',fontSize=13.2,leading=20,spaceBefore=11,
    spaceAfter=8,wordWrap='CJK',textColor=colors.black,keepWithNext=True),
 'eq':ParagraphStyle('Eq',fontName='Song',fontSize=12,leading=22,spaceAfter=5,
    leftIndent=12,rightIndent=5,wordWrap='CJK'),
 'small':ParagraphStyle('Small',fontName='Song',fontSize=9.5,leading=15.5,
    wordWrap='CJK',spaceAfter=7,textColor=gray),
 'cell':ParagraphStyle('Cell',fontName='Song',fontSize=10,leading=15,wordWrap='CJK'),
 'th':ParagraphStyle('TH',fontName='HeiBold',fontSize=10,leading=15,wordWrap='CJK',textColor=colors.black),
 'caption':ParagraphStyle('Caption',fontName='Song',fontSize=9.5,leading=15,
    spaceBefore=4,spaceAfter=12,wordWrap='CJK',textColor=gray),
}

supmap=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺','0123456789-+')
submap=str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789')
def clean(s):
    s=s.replace('−','-').replace('ℜ','Rmag').replace('ˣ','<super>x</super>')
    s=s.replace('e^(-t/(RC))','e<super>-t/(RC)</super>').replace('e^(-t/RC)','e<super>-t/RC</super>')
    s=s.replace('e^(-t/τ)','e<super>-t/τ</super>').replace('e^(-20/22)','e<super>-20/22</super>')
    s=re.sub('[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+',lambda m:'<super>'+m[0].translate(supmap)+'</super>',s)
    s=re.sub('[₀₁₂₃₄₅₆₇₈₉]+',lambda m:'<sub>'+m[0].translate(submap)+'</sub>',s)
    s=s.replace('**','')
    return s
def para(s,kind='body'):
    s=clean(s)
    if s.startswith('https://'):
        s='<link href="'+s+'" color="#333333">'+s+'</link>'
    return Paragraph(s,styles[kind])

def label(d,x,y,t,size=9,font='Hei',anchor='start',color=ink):
    d.add(String(x,y,clean(re.sub('<[^>]+>','',t)),fontName=font,fontSize=size,
        fillColor=color,textAnchor=anchor))
def arrow(d,x1,y1,x2,y2,color=ink):
    d.add(Line(x1,y1,x2,y2,strokeColor=color,strokeWidth=1))
    a=math.atan2(y2-y1,x2-x1); l=5
    pts=[x2,y2,x2-l*math.cos(a-.45),y2-l*math.sin(a-.45),
        x2-l*math.cos(a+.45),y2-l*math.sin(a+.45)]
    d.add(Polygon(pts,fillColor=color,strokeColor=color))
def box(d,x,y,w,h,lines):
    d.add(Rect(x,y,w,h,fillColor=colors.white,strokeColor=gray,strokeWidth=.7))
    for j,t in enumerate(lines):label(d,x+w/2,y+h/2+(len(lines)-1)*6-j*12,t,9,anchor='middle')
def graph_axes(d,x,y,w,h,xname,yname):
    arrow(d,x,y,x+w,y);arrow(d,x,y,x,y+h)
    label(d,x+w,y-14,xname,9,anchor='end');label(d,x,y+h+7,yname,9)

class Diagram(Flowable):
    def __init__(self,key):
        Flowable.__init__(self);self.key=key;self.width=CW
        self.height={'power_tree':220,'flux':160,'current_area':190,
            'boost_states':244,'kelvin':188,'discharge':196}[key]
    def draw(self):
        d=Drawing(CW,self.height);k=self.key
        if k=='power_tree':
            box(d,0,164,92,40,['24V适配器','输入保护候选'])
            box(d,140,164,100,40,['独立HV切断','升压功率级'])
            box(d,316,164,145,40,['170V母线','九管及泄放分压'])
            arrow(d,92,184,140,184);arrow(d,240,184,316,184)
            d.add(Line(114,184,114,40,strokeColor=gray))
            box(d,140,95,100,40,['24V降至AUX12','控制与保护偏置'])
            box(d,316,95,145,40,['默认关DRV12','HV5622及电平转换'])
            arrow(d,114,115,140,115);arrow(d,240,115,316,115)
            box(d,140,20,100,40,['24V降至5V','USB电源选择'])
            box(d,316,20,145,40,['3.3V逻辑','ESP32及外围'])
            arrow(d,114,40,140,40);arrow(d,240,40,316,40)
            label(d,190,5,'USB VBUS也进入选择级',8.5,anchor='middle')
        elif k=='flux':
            d.add(Rect(110,32,225,88,fillColor=pale,strokeColor=gray))
            for x in [135,185,235,285]:arrow(d,x,5,x,148)
            label(d,350,103,'B方向与法线相同',10)
            label(d,350,82,'θ = 0',10)
            label(d,221,66,'截面积 A',12,anchor='middle')
            label(d,25,143,'磁场垂直穿过面',10)
        elif k=='current_area':
            graph_axes(d,36,34,405,124,'时间 t','二极管电流 i')
            d.add(Polygon([58,34,58,145,292,34],fillColor=colors.HexColor('#E4E4E4'),strokeColor=ink))
            d.add(Line(292,34,425,34,strokeColor=ink))
            label(d,54,151,'0.8A',9);label(d,58,19,'0',9)
            label(d,292,19,'1μs',9,anchor='middle')
            label(d,159,65,'面积 = 电荷 0.4μC',10,anchor='middle')
            label(d,340,75,'剩余时段无输出电流',9,anchor='middle')
            label(d,36,175,'理想单次传能示意  平均电流 = 每次电荷 × 频率',10)
        elif k=='boost_states':
            for i,(name,slope,caption) in enumerate([
                ('导通充能','电感电流上升','输入 → 电感；电容供负载'),
                ('关断传能','电感电流下降','输入与电感 → 二极管 → 输出'),
                ('DCM空闲','电感电流为零','二极管截止；电容供负载')]):
                x=4+i*156
                label(d,x+73,219,name,11,font='HeiBold',anchor='middle')
                graph_axes(d,x+8,116,132,73,'t','iL')
                pts=([x+15,116,x+126,177] if i==0 else
                    [x+15,177,x+126,116] if i==1 else [x+15,116,x+126,116])
                d.add(PolyLine(pts,strokeColor=ink,strokeWidth=1.8))
                label(d,x+73,78,slope,10,anchor='middle')
                # Split captions deliberately to keep all Chinese labels inside their panel.
                parts=[caption] if len(caption)<16 else caption.split('；')
                for j,p in enumerate(parts):label(d,x+73,55-j*15,p,8,anchor='middle')
            label(d,4,12,'CCM没有最后一段空闲；三段图仅示意电流形态，不代表真实比例。',9)
        elif k=='kelvin':
            box(d,28,117,85,33,['MOS源极'])
            box(d,28,49,85,33,['分流 R230'])
            arrow(d,70,117,70,82);arrow(d,70,49,70,16)
            label(d,15,1,'功率返回',9)
            d.add(Circle(70,99,2,fillColor=ink));d.add(Circle(70,30,2,fillColor=ink))
            box(d,287,111,135,39,['100Ω与220pF','CS输入与比较'])
            box(d,287,24,135,39,['控制器参考地','CT及CS返回'])
            d.add(PolyLine([70,99,190,99,190,131,287,131],strokeColor=ink))
            d.add(PolyLine([70,30,206,30,206,44,287,44],strokeColor=gray))
            label(d,157,114,'正端细线取样',9);label(d,132,10,'负端独立Kelvin返回',9)
            label(d,24,171,'概念连接示意  正式PCB还需控制回路面积与寄生',10)
        elif k=='discharge':
            x,y,w,h=45,33,390,125
            graph_axes(d,x,y,w,h,'时间 s','电压 V')
            for v in [60,170]:
                yy=y+h*v/180
                d.add(Line(x,yy,x+w,yy,strokeColor=light,strokeDashArray=[3,3]))
                label(d,x-6,yy-3,str(v),8,anchor='end')
            for t in [0,1,2,3,4,5]:label(d,x+w*t/5,y-13,str(t),8,anchor='middle')
            for rc,col,dash in [(50000*20.3e-6,ink,None),(200000*20e-6,gray,[4,3])]:
                pts=[]
                for n in range(101):
                    t=n*.05;pts.extend([x+w*t/5,y+h*170*math.exp(-t/rc)/180])
                d.add(PolyLine(pts,strokeColor=col,strokeWidth=1.4,strokeDashArray=dash))
            label(d,45,180,'名义理想RC放电  初始170V  不构成安全许可',10)
            label(d,182,119,'虚线 主板独立200kΩ与20μF',9)
            label(d,124,68,'实线 全连50kΩ与20.3μF',9)
        d.drawOn(self.canv,0,0)

class Book(BaseDocTemplate):
    def __init__(self,path):
        BaseDocTemplate.__init__(self,str(path),pagesize=A4,leftMargin=LEFT,
            rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,
            title='NXT工程进展与知识',author='Σ',subject='Sprint05结束工程进展与教学读本')
        self.addPageTemplates([
            PageTemplate(id='odd',frames=[Frame(LEFT,BOTTOM,CW,H-TOP-BOTTOM,
                leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.page,
                autoNextPageTemplate='even'),
            PageTemplate(id='even',frames=[Frame(RIGHT,BOTTOM,CW,H-TOP-BOTTOM,
                leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.page,
                autoNextPageTemplate='odd')])
        self.head='NXT工程进展与知识';self.bookmarks=[]
    def beforeDocument(self):
        self.head='NXT工程进展与知识';self.bookmarks=[]
    def page(self,c,doc):
        c.saveState()
        if doc.page>1:
            xleft=LEFT if doc.page%2 else RIGHT
            xright=W-RIGHT if doc.page%2 else W-LEFT
            c.setFont('Hei',8);c.setFillColor(gray)
            c.drawString(xleft,H-13*MM,'Σ   NXT工程进展与知识')
            c.drawRightString(xright,H-13*MM,'工程状态 2026 11 14')
            c.setFont('Song',9)
            if doc.page%2:
                c.drawString(xleft,11*MM,'第一版  ·  成书 2026 11 15')
                c.drawRightString(xright,11*MM,str(doc.page))
            else:
                c.drawString(xleft,11*MM,str(doc.page))
                c.drawRightString(xright,11*MM,'第一版  ·  成书 2026 11 15')
        c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name=='H1':
            txt=f.getPlainText();key='chapter-'+str(len(self.bookmarks))
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(txt,key,0)
            if txt not in ['目录','阅读方法']:self.notify('TOCEntry',(0,txt,self.page,key))
            self.bookmarks.append((txt,self.page))

def make_table(lines):
    rows=[]
    for line in lines:
        vals=[x.strip() for x in line.strip('|').split('|')]
        if all(re.fullmatch(r'[:\- ]+',x or '-') for x in vals):continue
        rows.append(vals)
    n=len(rows[0]); lens=[max(len(re.sub('<.*?>','',r[i])) for r in rows) for i in range(n)]
    if n==2:ratios=[.47,.53] if max(lens)>30 else [.59,.41]
    elif n==3:ratios=[.19,.39,.42]
    else:ratios=[1/n]*n
    data=[[para(v,'th' if j==0 else 'cell') for v in row] for j,row in enumerate(rows)]
    t=Table(data,colWidths=[CW*r for r in ratios],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,light),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EAEAEA')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,pale]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    return t

def build():
    text=(HERE/'书稿.md').read_text('utf-8');lines=text.splitlines();story=[]
    # The opening is typeset explicitly; the rest remains manuscript-driven.
    firstpage=lines.index('@page')
    story += [Spacer(1,25),Paragraph('Σ',ParagraphStyle('Sigma',fontName='Song',fontSize=88,leading=100,textColor=colors.black)),
        Spacer(1,28),Paragraph('NXT工程进展与知识',ParagraphStyle('Title',fontName='HeiBold',fontSize=26,leading=39,textColor=colors.black)),
        Spacer(1,13),Paragraph('从九管辉光显示的真实问题<br/>理解电源重构与工程验证',ParagraphStyle('Sub',fontName='Hei',fontSize=14,leading=24,textColor=colors.black)),
        Spacer(1,22),para('Σ　工程学习读本　第一版','small'),
        para('工程状态截至2026年11月14日<br/>成书日期2026年11月15日','small'),Spacer(1,14)]
    # Opening conclusions belong at the beginning, before readers reach the chapters.
    opening=[x for x in lines[:firstpage] if x.startswith(('这本书','当前结论','本书介绍'))]
    for s in opening:story.append(para(s,'small'))
    story.append(PageBreak())
    i=firstpage+1; in_refs=False
    while i<len(lines):
        s=lines[i].strip();i+=1
        if not s:continue
        if s=='@page':story.append(PageBreak());continue
        if s=='@toc':
            story.append(PageBreak());story.append(para('目录','h1'))
            toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC',fontName='Song',fontSize=10.8,
                leading=16,spaceBefore=1,wordWrap='CJK',leftIndent=0,rightIndent=8)]
            toc.dotsMinLevel=0;story.append(toc);continue
        if s.startswith('# '):
            title=s[2:]
            if title!='阅读方法':
                if title[:2] in ['01','05','09','15','17'] or not re.match(r'^\d\d ',title):
                    story.append(PageBreak())
                else:
                    story.extend([CondPageBreak(225),Spacer(1,22)])
            in_refs=title=='证据索引与版本说明'
            story.append(para(title,'h1'));continue
        if s=='## 本章练习':
            block=[para('本章练习','h2')]
            while i<len(lines) and not lines[i].strip().startswith('# '):
                x=lines[i].strip();i+=1
                if x:block.append(para(x,'small' if x.startswith(('本章证据','本章关联')) else 'body'))
            story.append(KeepTogether(block));continue
        if s.startswith('## '):story.append(para(s[3:],'h2'));continue
        if s.startswith('@figure '):
            story.extend([Spacer(1,5),Diagram(s.split()[1]),Spacer(1,8)]);continue
        if s.startswith('@image '):
            from PIL import Image as PILImage
            p=ROOT/s[7:]
            with PILImage.open(p) as img:iw,ih=img.size
            im=Image(str(p),width=CW,height=CW*ih/iw)
            story.extend([Spacer(1,5),im,Spacer(1,9)]);continue
        if s.startswith('|'):
            block=[s]
            while i<len(lines) and lines[i].strip().startswith('|'):
                block.append(lines[i].strip());i+=1
            t=make_table(block)
            story.extend([KeepTogether([t]) if len(block)<=9 else t,Spacer(1,11)]);continue
        if s.startswith('= '):story.append(para(s[2:],'eq'));continue
        kind='small' if in_refs or s.startswith('本章证据') or s.startswith('本章关联') else 'body'
        story.append(para(s,kind))
    doc=Book(OUT);doc.multiBuild(story)
    (QA/'chapters.json').write_text(json.dumps(doc.bookmarks,ensure_ascii=False,indent=2),'utf-8')
    sourcepaths=[
        'docs9/ELECTRICAL_CLOSURE_SPRINT01.md','docs9/ELECTRICAL_CLOSURE_SPRINT02.md',
        'docs9/electrical_sprint03/SPRINT_03_REPORT.md','docs9/electrical_sprint04/SPRINT_04_REPORT.md',
        'projects/QS30-9_24V/docs/SPRINT05_REPORT.md','projects/QS30-9_24V/docs/S05_POWER_AND_QUALIFICATION.md',
        'projects/QS30-9_24V/docs/S05_CIRCUIT_CANDIDATES.md','projects/QS30-9_24V/docs/S05_REQUIREMENTS.md',
        'projects/QS30-9_24V/config/sprint05.json','projects/QS30-9_24V/sim/cs_v1/results.json',
        'projects/QS30-9_24V/sim/cs_v1/preregister.json','projects/QS30-9_24V/docs/TASKS.csv',
        'projects/QS30-9_24V/docs/sprint05/final_verification.json',
        'projects/QS30-9_24V/netlist/candidate_power_pins.meta.json',
        'projects/QS30-9_24V/docs/BREAKPOINT_S05_2026-11-14.md',
        'projects/QS30-9_24V/sources/manifest.json',
        'sim/sprint04/open_loop_v1/input24/waveforms.png',
        'sim/sprint03/diagnostics_v1/historical_type2_analysis.png']
    manifest={'book':'NXT工程进展与知识','edition':1,'compiled':'2026-11-15',
        'engineering_as_of':'2026-11-14','manuscript_chars':len(text),'sources':{}}
    for p in sourcepaths:manifest['sources'][p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    for p in [OUT,HERE/'书稿.md',Path(__file__)]:
        manifest[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (HERE/'来源与构建记录.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
    # Fail early if a printable manuscript character would disappear in the embedded body font.
    visible=re.sub('<[^>]*>','',clean(text));font=pdfmetrics.getFont('Song')
    missing=sorted({c for c in visible if ord(c)>32 and ord(c) not in font.face.charToGlyph})
    (QA/'glyph_audit.json').write_text(json.dumps({'missing_body_glyphs':missing},ensure_ascii=False),'utf-8')
    print(json.dumps({'output':str(OUT),'chars':len(text),'chapters':doc.bookmarks,'missing_glyphs':missing},ensure_ascii=True))

if __name__=='__main__':build()
