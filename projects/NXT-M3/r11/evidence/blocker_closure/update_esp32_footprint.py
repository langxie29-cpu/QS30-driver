from pathlib import Path
import re

eda = Path("eda")
standard = "ESP32-S3-WROOM-1"
local = standard + "_0.30mm_Drill"
old_id = "RF_Module:" + standard
new_id = "R10_R10:" + local
source = Path(r"C:/Program Files/KiCad/10.0/share/kicad/footprints/RF_Module.pretty") / (standard + ".kicad_mod")
board = eda / "NXT-M3-R11.kicad_pcb"
schematic = eda / "ESP32.kicad_sch"

def adapt(footprint):
    if footprint.count("(drill 0.2)") != 12:
        raise ValueError("Unexpected ground drill count")
    footprint = footprint.replace("(drill 0.2)", "(drill 0.3)")
    antenna_silk = re.compile(r"\(fp_line\s+\(start -?9\.2 -12\.9\).*?\(layer \"F\.SilkS\"\)", re.S)
    def reclassify(match):
        line = match[0]
        coordinates = re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", line).groups()
        if coordinates not in {("9.2","-6.7"),("-9.2","-6.7"),("9.2","-12.9")}:
            raise ValueError(coordinates)
        # The full antenna outline is already present on F.Fab.
        return line.replace('"F.SilkS"', '"F.Fab"')
    footprint, edited = antenna_silk.subn(reclassify, footprint)
    if edited != 3:
        raise ValueError("Unexpected antenna outline")
    return footprint

definition = source.read_text(encoding="utf-8")
definition = adapt(definition.replace(f'(footprint "{standard}"', f'(footprint "{local}"', 1))
board_data = board.read_text(encoding="utf-8")
start = board_data.index(f'\t(footprint "{old_id}"')
end = board_data.index("\n\t)", start) + 3
instance = adapt(board_data[start:end].replace(old_id, new_id, 1))
schematic_data = schematic.read_text(encoding="utf-8")
assert schematic_data.count(old_id) == 1

(eda / "R10_R10.pretty" / (local + ".kicad_mod")).write_text(definition, encoding="utf-8", newline="\n")
board.write_text(board_data[:start] + instance + board_data[end:], encoding="utf-8", newline="\n")
schematic.write_text(schematic_data.replace(old_id, new_id), encoding="utf-8", newline="\n")
