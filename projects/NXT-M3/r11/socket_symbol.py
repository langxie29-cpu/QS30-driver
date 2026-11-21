"""Map the PCB hand-wire terminal to the eleven actually present tube functions."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
FILE = HERE/"eda/Tube_interfaces.kicad_sch"
LIB = FILE.with_name("R10_R10.kicad_sym")


def extract_socket(line):
    start=line.index('(symbol "R10_R10:Socket"')
    depth=0
    for index,char in enumerate(line[start:],start):
        if char=="(":
            depth+=1
        elif char==")":
            depth-=1
            if depth==0:
                return line[start:index+1]
    raise ValueError("Socket definition unbalanced")


def main():
    original=FILE.read_text(encoding="utf-8")
    definition=extract_socket(original.splitlines()[2])
    unused=r'\(pin passive line \(at [^)]*\) \(length [^)]*\) \(name "UNUSED_[28]"[^"]*\(number "[28]" \(effects \(font \(size [^)]*\)\) \)\)\)'
    new_def,hits=re.subn(unused,"",definition)
    if hits!=2:
        raise ValueError(f"Expected both unused pin definitions, found {hits}")
    new_def=new_def.replace("Socket","HandWireTube")
    sheet=original.replace(definition,new_def).replace('"R10_R10:Socket"','"R10_R10:HandWireTube"')
    sheet,pins=re.subn(r'(?m)^\(pin "[28]"[^\n]*\n(?=(?:\(pin "[0-9]+"[^\n]*\n)*\(instances[^\n]*\(reference "V[123]"\))',"",sheet)
    sheet,ncs=re.subn(r'(?m)^\(no_connect [^\n]*\n',"",sheet)
    assert (pins,ncs)==(6,6),(pins,ncs)
    FILE.write_text(sheet,encoding="utf-8")
    library=LIB.read_text(encoding="utf-8").rstrip()
    LIB.write_text(library[:-1]+new_def.replace('"R10_R10:HandWireTube"','"HandWireTube"')+"\n)\n",
                   encoding="utf-8")


if __name__=="__main__":
    main()
