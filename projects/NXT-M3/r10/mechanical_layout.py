"""Generate a dimensioned 2D assembly preview and check available geometry."""
import csv
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
mech=json.loads((HERE/"mechanical.json").read_text(encoding="utf-8-sig"))
w,h=mech["board"]["size"]
centers=mech["tube"]["centers"]
glass=mech["tube"]["diameter"]
approach=mech["socket"]["approach_envelope_diameter"]
mount=mech["mounting"]
carrier=mech["oled"]["carrier_keepout"]
evid=[]

def record(name,value,unit,status):
    evid.append([name,f"{value:g}" if isinstance(value,(float,int)) else value,unit,status])

def minimum_edge(center,diameter):
    x,y=center
    return min(x,y,w-x,h-y)-diameter/2

for idx,(left,right) in enumerate(zip(centers,centers[1:]),1):
    pitch=math.dist(left,right)
    record(f"V{idx}_V{idx+1}_pitch",pitch,"mm","PROVISIONAL")
    record(f"V{idx}_V{idx+1}_glass_clear",round(pitch-glass,2),"mm","2D_POSITIVE")
    record(f"V{idx}_V{idx+1}_approach_rings_clear",round(pitch-approach,2),"mm","PLACEHOLDER_POSITIVE")
    assert pitch>glass and pitch>approach
record("minimum_glass_to_pcb_edge",round(min(minimum_edge(c,glass) for c in centers),2),"mm","2D_POSITIVE")
record("minimum_approach_to_pcb_edge",round(min(minimum_edge(c,approach) for c in centers),2),"mm","PLACEHOLDER_POSITIVE")
cx,cy=carrier["center"]
cw,ch=carrier["size"]
record("oled_carrier_to_nearest_tube_projection",round(centers[1][1]-glass/2-(cy+ch/2),2),"mm","PLACEHOLDER_POSITIVE")
record("oled_carrier_to_nearest_approach_ring",round(centers[1][1]-approach/2-(cy+ch/2),2),"mm","PLACEHOLDER_POSITIVE")
record("minimum_mount_hardware_to_approach_ring",round(min(math.dist(a,b) for a in centers for b in mount["hole_centers"])-(approach+mount["hardware_envelope_diameter"])/2,2),"mm","PLACEHOLDER_POSITIVE")
record("socket_z_and_insertion","unknown","","TBD")
record("true_3D_enclosure","unknown","","TBD")
with (HERE/"evidence"/"mechanical_clearances.csv").open("w",newline="",encoding="utf-8") as f:
    wr=csv.writer(f)
    wr.writerow(("check","value","units","status"))
    wr.writerows(evid)

def rect(x,y,width,height,color,stroke,more=""):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{color}" stroke="{stroke}" {more}/>'

def circle(x,y,r,fill,stroke,more=""):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" {more}/>'

def label(x,y,msg,size=2.3,more=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" {more}>{msg}</text>'

def line(x1,y1,x2,y2,more=""):
    return f'<path d="M{x1},{y1} {x2},{y2}" stroke="#465a62" fill="none" {more}/>'

def arrow(x1,y1,x2,y2):
    return line(x1,y1,x2,y2,'marker-start="url(#arrow)" marker-end="url(#arrow)"')

diagram=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -15 150 113" width="900" height="678">',
         '<title>NXT R10 three-tube mechanical prelayout</title>',
         '<desc>Board 130 by 80 mm with measured glass and provisional mechanical features.</desc>',
         '<defs><marker id="arrow" viewBox="0 0 5 5" refX="4.5" refY="2.5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L5 2.5L0 5Z" fill="#465a62"/></marker></defs>',
         rect(-10,-15,150,113,"#fbf9f3","none"),
         '<g font-family="Arial, sans-serif" fill="#172b32" stroke-width=".36">',
         label(0,-9,"NXT R10 / MODULE FRONT / MECHANICAL PRELAYOUT",3.4,'font-weight="bold"'),
         arrow(0,-3,w,-3),label(w/2,-4,"130 mm",2.4,'text-anchor="middle"'),
         arrow(-4,0,-4,h),label(-6,h/2,"80 mm",2.4,'text-anchor="middle" transform="rotate(-90 -6 40)"'),
         rect(0,0,w,h,"#edf1ee","#40535a"),
         rect(89,2,35,34,"#f2ded4","#be6f58",'stroke-dasharray="1.2 .9"'),
         label(107,25,"HV power",2.5,'text-anchor="middle"'),
         rect(*mech["rf"]["near_field_reserve"],"#dfe9f1","#527495",'stroke-dasharray="1.2 .9"'),
         label(8.5,20,"RF",2.5,'text-anchor="middle"'),
         label(8.5,23,"reserve",2.1,'text-anchor="middle"'),
         rect(cx-cw/2,cy-ch/2,cw,ch,"#f3e6ba","#8d6e28",'stroke-dasharray="1.1 .7"'),
         label(cx,cy,"0.91 in OLED / carrier TBD",2.4,'text-anchor="middle"')]
for x,y in mount["hole_centers"]:
    diagram.extend((circle(x,y,mount["hardware_envelope_diameter"]/2,"none","#6e8290",'stroke-dasharray=".8 .6"'),
                    circle(x,y,mount["candidate_diameter"]/2,"#fbf9f3","#6e8290")))
for n,(x,y) in enumerate(centers,1):
    diagram.extend((circle(x,y,approach/2,"none","#7d6258",'stroke-dasharray="1.2 .9"'),
                    circle(x,y,glass/2,"#c6d7cd","#355d50"),
                    label(x,y-1,f"V{n} / glass Ø{glass}",2.6,'text-anchor="middle"'),
                    label(x,y+3,"socket TBD",2.3,'text-anchor="middle"')))
for (x1,y1),(x2,y2) in zip(centers,centers[1:]):
    diagram.extend((line(x1,y1+15,x1,76),line(x2,y2+15,x2,76),
                    arrow(x1,74,x2,74),label((x1+x2)/2,73,"38 mm",2.2,'text-anchor="middle"')))
diagram.extend([label(0,86,"Green: glass envelope  •  Dashed rings: provisional Ø35 mm approach, no socket land pattern",2.4),
                label(0,91,"Four M3 candidate points share one carrier  •  All board and carrier dimensions are provisional",2.4),
                "</g></svg>"])
(HERE/"mechanical_layout.svg").write_text("\n".join(diagram)+"\n",encoding="utf-8")
print(f"Checked {len(evid)} mechanical statements, including two explicitly unresolved items.")
