"""Rebase the R9 yellow-OLED material roll-up against R10 fitted design candidates."""
from decimal import Decimal as D
from pathlib import Path
import csv
from circuit import parts

HERE=Path(__file__).resolve().parent
BUILD=(1,3,10)

# Incremental estimates apply to the eventual populated design, including the HV DNP
# parts. Quotes are carried as dated R9 public-price snapshots.
UPDATES={
    "3.3 V local reservoir and buck MLCC":("C4 C6 C7 C8 C10","5 rather than 3 selected-size MLCCs",
        ("1.10","0.84","0.64")),
    "Decoupling capacitors":("C1 C9 C12 C14 C16 C17 C18 C19 C20 C21 C22 C23 C24 C27 C29 C30 C32 C33 C34 C39 C46 C49 C50 C51",
        "Increment above budgeted ten; keep value-specific sourcing open",("1.26","0.98","0.84")),
    "EN strap / control R and C":("R7 R8 R9 R10 R11 R12 R13 R14 R15 R16 R17 R30 R31 R32 R33 R34 R35 R36 R54 R55 C11",
        "Nine additional small passives",("0.90","0.68","0.54")),
    "OLED switched rail and I2C isolation":("U5 U6 U7 D1 R18 R19 R20 R21 R22 C13 C15",
        "Adds reset gating and ESD; TCA9517A variant",("1.20","0.90","0.60")),
    "Fault latch and hardware OE":("U8 U9 U10 U19 Q31 R23 R24 R25 R26 R27",
        "Series permit chain and Q31, above the R9 allowance",("1.60","1.15","0.85")),
    "Service pads / hardware":("J2 J4 SW1 U24 TP1 TP2 TP3 TP4 TP5 TP6 TP7 TP8 TP9",
        "UART service buffer and hardware above R9 allowance",("2.60","2.00","1.45")),
    "Window watchdog and rail supervisor":("U4 U25","TPS3808G33 and TPS3430; retain R9 allowance",("0","0","0")),
    "Independent HV OVP/OCP detector":("U12 U13 R47 R48 R49 R60 R61 R62 R63 R64 C31 C35",
        "TLV1702+REF3312; allowance retained pending RFQ",("0","0","0")),
    "Residual voltage sense and re-arm":("U14 U15 R28 R46 R50 R51 R52 R53 R65 R66 R67 R68 R69 C36",
        "Detection and bias qualification candidates; R9 allowance retained",("0","0","0")),
    "Gate bias / driver":("U16 U18 L2 D2 R70 R71 R74 R75 R76 C37 C38 C45",
        "TPS61040 bias completed in CAD; retain R9 allowance until sourcing",("0","0","0")),
    "Feedback / shunt / compensation / snubber":("R72 R73 R77 R78 R79 R80 R81 R82 R83 R84 R85 R86 C40 C41 C42 C43 C44 C48",
        "Four-element FB divider, R73 and snubber candidates",("1.20","0.90","0.65")),
    "5V fuse/TVS, protection passives":("F1 D4 R1 R2 R3 R4 R5 R6 R40 R41 R42 R43 R44 R45 C2 C3 C25 C26 C28",
        "Adds second set of startup/timing parts; R9 had a protection allowance",("1.40","1.00","0.75")),
    "Anode load resistors":("R302 R303 R304 R305 R306 R307",
        "Move from axial R9 allowance to power SMD; derating and tolerance open",("0.90","0.75","0.60")),
}
REFS={
    "MCU and PCB antenna":"U3","3.3 V 1 A buck":"U2","2.2 uH buck inductor":"L1",
    "Input bulk and RF transient reserve":"C5","Shift register":"U20 U21 U22 U23",
    "Cathode NPN":"Q1..Q30","Bipolar base series resistor":"R100..R129",
    "Bipolar base pull down":"R200..R229","Boost controller":"U17","Boost magnetic":"L3",
    "Main switch":"Q32","Rectifier":"D3","HV reservoir":"C47",
    "Real HV input cut and reverse block":"U11","QS30-1 tube sockets":"V1 V2 V3",
    "5 V keyed connector and mating pigtail":"J1","OLED header and cable":"J3",
}
INPUTS={"existing QS30-1 tubes":"User has tubes; serviceability and interchangeability unverified. Excluded as in R9.",
        "0.91 inch OLED":"Yellow screenshot input ¥9.78; SKU, fit and optical acceptance open.",
        "branch fault hardware":"R9 allowance retained. Open architecture and pricing.",
        "bare PCB":"Existing R9 allowance only. 130×80 is a placement screen and quotes are open.",
        "assembly":"R9 conversion rows retained. 282 preliminary placed designators plus future sockets, stencil and sequence require a new RFQ.",
        "inventory":"No stock assumed for R10 parts apart from the user's visible tube pool."}

def references(text):
    for word in text.split():
        if ".." not in word:
            yield word
            continue
        a,b=word.split("..")
        yield from (f"{a[0]}{n}" for n in range(int(a[1:]),int(b[1:])+1))

def main():
    source=HERE.parent/"r9"/"BOM_COST_MODEL.csv"
    with source.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    output=[]
    totals={}
    coverage=set()
    for tier,n in enumerate(BUILD):
        chosen=[r for r in rows if r["oled"]=="A" and r["build_qty"]==str(n)]
        baseline=next(D(r["used_or_summary_cny"]) for r in chosen if r["item"]=="MATERIAL_PER_BOARD")
        subtotal=D(0)
        for row in (r for r in chosen if r["record"]=="MATERIAL"):
            name=row["item"]
            refs,note,delta=UPDATES.get(name,(REFS.get(name,""),"R9 unit estimate retained",("0","0","0")))
            old=D(row["used_or_summary_cny"])/n
            if name=="Permanent bleeder resistors":
                refs="R400..R407"
                note="Four series 2512 resistors per independent path; unit estimate, exact MPN open"
                new=8*D(("0.35","0.28","0.20")[tier])
            else:
                new=old+D(delta[tier])
            actual=new-old
            subtotal+=actual
            coverage.update(references(refs))
            output.append((n,name,refs,row["candidate_mpn"],f"{old:.2f}",f"{new:.2f}",f"{actual:.2f}",
                           row["availability_or_class"] if actual==0 else "R10_INCREMENT_ESTIMATE",note,row["evidence"]))
        duplicate=next(D(r["used_or_summary_cny"])/n for r in chosen if r["item"]=="Real HV input cut and reverse block")
        output.append((n,"5 V system entry eFuse","U1","TPS259474LRPWR","0.00",f"{duplicate:.2f}",f"{duplicate:.2f}",
                       "R9_PUBLIC_PRICE_APPLIED","Uses same tier as U11; shipping, lot and CAD release TBD","../r9/BOM_COST_MODEL.csv"))
        coverage.add("U1")
        subtotal+=duplicate
        totals[n]=(baseline,subtotal,baseline+subtotal)
        for row in (r for r in chosen if r["record"] in ("CONVERSION","CASH")):
            output.append((n,row["item"],"",row["candidate_mpn"],"","","","R9_BATCH_ALLOWANCE_CARRIED",
                           f"R9 cash allowance CNY {row['cash_cny']}; R10 quote pending",row["evidence"]))
    expected={p["ref"] for p in parts if p["kind"]!="Flag"}
    if coverage!=expected:
        raise AssertionError(f"Coverage differs: missing {sorted(expected-coverage)}, extra {sorted(coverage-expected)}")
    with (HERE/"BOM_R10_COST.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(("modules","item","R10_ref_or_range","R9_mpn_text","R9_cny_per_board",
                        "R10_cny_per_board","delta_cny_per_board","evidence_class","note","source"))
        writer.writerows(output)
        for n,(old,delta,new) in totals.items():
            writer.writerow((n,"TOTAL MATERIAL","","",f"{old:.2f}",f"{new:.2f}",f"{delta:.2f}",
                             "ENGINEERING_ESTIMATE","includes PCB and protection reserves; excludes assembly, freight and tubes",""))
        for name,note in INPUTS.items():
            writer.writerow(("",name,"","","","","","SCOPE",note,""))
    for n,values in totals.items():
        print(n,*[f"{value:.2f}" for value in values])

if __name__=="__main__":
    main()
