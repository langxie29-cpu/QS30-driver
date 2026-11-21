"""Add a bounded low-voltage return pour and run native refill on the R3 board."""
import json
import os
from pathlib import Path
import subprocess

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
EDA = HERE / "eda/NXT-M3-R11.kicad_pcb"
OUT = HERE / "evidence/r4"
CLI = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin")) / "kicad-cli.exe"


def main():
    board = pcb.LoadBoard(str(EDA))
    tag = "R11 LV GND draft, outside RF reserve"
    if any(zone.GetZoneName() == tag for zone in board.Zones()):
        raise ValueError("R11 ground pour is already present")
    zone = pcb.ZONE(board)
    zone.SetLayer(pcb.B_Cu)
    zone.SetZoneName(tag)
    zone.SetNetCode(board.FindNet("GND").GetNetCode())
    zone.SetLocalClearance(pcb.FromMM(.25))
    zone.SetThermalReliefGap(pcb.FromMM(.30))
    zone.SetThermalReliefSpokeWidth(pcb.FromMM(.30))
    zone.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(pcb.FromMM(.22))
    poly = zone.Outline()
    poly.NewOutline()
    for x, y in ((70,54),(120,54),(120,87),(70,87)):
        poly.Append(pcb.FromMM(x), pcb.FromMM(y))
    board.Add(zone)
    pcb.SaveBoard(str(EDA), board)
    OUT.mkdir(exist_ok=True)
    args = [str(CLI), "pcb", "drc", "--refill-zones", "--save-board", "--schematic-parity",
            "--format", "json", "--exit-code-violations", "-o", str(OUT/"pour_final.json"), str(EDA)]
    done = subprocess.run(args, capture_output=True)
    print(done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace"))
    (OUT/"pour_final_command.json").write_text(json.dumps(
        {"command":args, "exit":done.returncode, "stdout":done.stdout.decode("utf-8","replace"),
         "stderr":done.stderr.decode("utf-8","replace")}, ensure_ascii=False, indent=2), encoding="utf-8")
    if done.returncode not in (0,5):
        raise RuntimeError("Native refill failed")


if __name__ == "__main__":
    main()

