"""Apply the R14 low-voltage interfaces to the frozen R11 native sheets."""
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from uuid import NAMESPACE_URL, uuid5

HERE = Path(__file__).resolve().parent
EDA = HERE / "eda"
BASE = HERE.parent / "r11/eda"
sys.path.insert(0, str(HERE.parent / "r10"))
import build_schematic as sch
import circuit as ck

PROJECT = "NXT-M3-R14"
R11 = "NXT-M3-R11"
GPIO = dict(zip(("BTN1", "BTN2", "AUX1", "AUX2"), range(18, 22)))
NEW_SHEET = "Physical_controls"


def identity(name):
    return str(uuid5(NAMESPACE_URL, "nxt-m3/r14/" + name))


def append_sheet_content(path, lines):
    original = path.read_text(encoding="utf-8").splitlines()
    sch.write(path, [*original[:-1], *lines, ")"])


def definitions():
    ck.parts.clear()
    ck.sheet, ck.hold = NEW_SHEET, False
    gh = "Connector_JST:JST_GH_BM06B-GHS-TBT_1x06-1MP_P1.25mm_Vertical"
    ph = "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"
    ck.kind("ButtonHarness", "GND:p BTN1:p BTN2:p AUX1:p AUX2:p 3V3_AUX:p MP:p",
            gh, "https://www.jst-mfg.com/product/pdf/eng/eGH.pdf")
    pins = ck.kinds["ButtonHarness"][0]
    pins["MP"] = pins.pop("7")
    ck.kind("StopHarness", "LOOP:p RETURN:p", ph,
            "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf")
    ck.kind("HarnessTVS", "IO:p GND:p", "Diode_SMD:D_SOD-523",
            "https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf")
    ck.kind("AuxBlockDiode", "K:p A:p", "Diode_SMD:D_SOD-123F",
            "https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf")

    ck.add("J5", "ButtonHarness", "J_BTN / dry contacts", "GND BTN1 BTN2 AUX1 AUX2 3V3_AUX GND",
           "BM06B-GHS-TBT(LF)(SN)", status="HOLD_DNP")
    for i, signal in enumerate(GPIO):
        filtered = f"{signal}_GPIO"
        ck.r(f"R{500+i}", "1k 1%", signal, filtered)
        ck.r(f"R{504+i}", "10k 1%", "3V3", filtered)
        ck.c(f"C{60+i}", "10n", filtered)
        ck.add(f"D{10+i}", "HarnessTVS", "TPD1E10B06", [signal, "GND"], "TPD1E10B06DYAR")
    ck.r("R508", "330R 1%", "3V3", "AUX_FEED", status="HOLD_DNP")
    ck.add("D14", "AuxBlockDiode", "BAT54H", "3V3_AUX AUX_FEED", "BAT54H,115", status="HOLD_DNP")

    ck.add("J6", "StopHarness", "HV STOP / NC dry loop", "STOP_LOOP GND", "S2B-PH-K-S(LF)(SN)")
    ck.r("R509", "220R 1%", "STOP_LOOP", "STOP_GATE")
    ck.r("R510", "3.3k 1%", "3V3", "STOP_GATE")
    ck.c("C64", "1n", "STOP_GATE")
    ck.add("D15", "HarnessTVS", "TPD1E10B06", "STOP_LOOP GND", "TPD1E10B06DYAR")
    ck.add("Q35", "MOS", "2N7002BK / STOP sink", "STOP_GATE GND FAULT_N", "2N7002BK,215")


def connect_gpio():
    path = EDA / "ESP32.kicad_sch"
    data = path.read_text(encoding="utf-8")
    _, pins, _ = sch.symbol("ESP32", True)
    for signal, pin in GPIO.items():
        xx, yy = pins[str(pin)]
        x, y = round(72.39+xx, 4), round(85.09-yy, 4)
        end = round(x - 2.54, 4)
        nc = identity(f"unused-{pin}")
        pattern = rf'\(no_connect \(at {x} {y}\) \(uuid "[^"]+"\)\)'
        replacement = (
            f'(wire (pts (xy {x} {y}) (xy {end} {y})) (stroke (width 0) (type default)) (uuid "{nc}"))\n'
            f'(global_label "{signal}_GPIO" (shape input) (at {end} {y} 180) '
            f'(effects (font (size .78 .78)) (justify left)) (uuid "{identity(signal)}") '
            f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {end} {y} 0) '
            f'(effects (font (size .8 .8)) (hide yes))))'
        )
        data, count = re.subn(pattern, lambda _: replacement, data)
        if count != 1:
            raise ValueError(f"Expected one isolated U3 pad {pin}")
    path.write_text(data, encoding="utf-8", newline="\n")


def main():
    sch.PROJECT = PROJECT
    definitions()
    baseline = ET.parse(HERE / "evidence/baseline/netlist.xml")
    existing = {x.get("ref") for x in baseline.findall("./components/comp")}
    new = {part["ref"] for part in ck.parts}
    if len(new) != len(ck.parts) or new & existing:
        raise ValueError(f"Reference collision: {new & existing}")
    for source in BASE.glob("*.kicad_sch"):
        target = EDA / source.name.replace(R11, PROJECT)
        data = source.read_text(encoding="utf-8").replace(R11, PROJECT)
        data = data.replace("R11 engineering HOLD", "R14 engineering HOLD")
        if source.stem == R11:
            data = data.replace("DIGITS / R10", "DIGITS / R14").replace("R11     GATE", "R14     GATE")
            data = data.replace("Logical socket pins are reviewable. Physical socket lands remain undefined.",
                                "GZC13-F / hand-wired socket projection remains under mechanical HOLD.")
        target.write_text(data, encoding="utf-8", newline="\n")
    connect_gpio()
    extras = ("ButtonHarness", "StopHarness", "HarnessTVS", "AuxBlockDiode")
    source = BASE / "R10_R10.kicad_sym"
    lib = EDA / source.name
    shutil.copyfile(source, lib)
    append_sheet_content(lib, [sch.symbol(name)[0] for name in extras])

    sheet_id = identity("sheet-" + NEW_SHEET)
    root = EDA / f"{PROJECT}.kicad_sch"
    append_sheet_content(root, [
        f'(sheet (at 275 208) (size 105 24) (stroke (width .254) (type default))'
        f' (fill (color 0 0 0 0)) (uuid "{sheet_id}")'
        f' (property "Sheetname" "{NEW_SHEET}" (at 275 207 0) {sch.effect(1.2,"(justify left)")})'
        f' (property "Sheetfile" "{NEW_SHEET}.kicad_sch" (at 275 233 0) {sch.effect(.9,"(justify left)")})'
        f' (instances (project "{PROJECT}" (path "/{sch.ROOT}" (page "16")))))',
    ])
    page = sch.page(NEW_SHEET, identity("file-" + NEW_SHEET),
                    " ".join(sch.symbol(k, True)[0] for k in sorted({p["kind"] for p in ck.parts})))
    page[1] = page[1].replace("R10 engineering HOLD", "R14 engineering HOLD")
    page.extend([
        sch.note("FUNCTION BUTTONS / ACCESSORY", 18, 16, 1.7),
        sch.note("J5 dry contacts to GND. Fit neither R508 nor D14 for the passive harness.", 18, 24),
        sch.note("HARDWARE HV STOP", 18, 201, 1.7),
        sch.note("J6 external NC dry loop. Opening pulls FAULT_N low. Re-arm locally at J4.", 18, 210),
    ])
    points = {"J5":(58,43), "R508":(165,43), "D14":(256,43), "J6":(46,236),
              "R509":(125,236), "R510":(205,236), "C64":(287,236), "D15":(365,236), "Q35":(46,268)}
    for i in range(4):
        for ref, y in ((f"D{10+i}", 79), (f"R{500+i}", 108), (f"R{504+i}", 138), (f"C{60+i}", 168)):
            points[ref] = (53 + i * 99, y)
    for part in ck.parts:
        page.extend(sch.place(part, *points[part["ref"]], sheet_id))
    sch.write(EDA / f"{NEW_SHEET}.kicad_sch", [*page, ")"])

    for sheet, note, y in (
        ("Hardware_inhibit", "J6 HV STOP sinks FAULT_N. Reclosed loop requires a new local ARM edge.", 27),
        ("HV_cutoff", "HV STOP deasserts ARMED through U8 hardware clear. R40 remains physically open DNP.", 27),
    ):
        append_sheet_content(EDA / f"{sheet}.kicad_sch", [sch.note(note, 16, y)])

    project = json.loads((BASE / f"{R11}.kicad_pro").read_text())
    project["meta"]["filename"] = f"{PROJECT}.kicad_pro"
    (EDA / f"{PROJECT}.kicad_pro").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
