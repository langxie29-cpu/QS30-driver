"""Run portable C host assertions in a mapped, instruction-limited RV32 emulator."""
import argparse
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_RISCV, UC_MODE_RISCV32, UC_HOOK_MEM_WRITE
from unicorn.riscv_const import UC_RISCV_REG_SP

outcome = None
def finish(uc, access, address, size, value, data):
    global outcome
    outcome = value
    uc.emu_stop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    uc = Uc(UC_ARCH_RISCV, UC_MODE_RISCV32)
    uc.mem_map(0x10000,0x20000)
    uc.mem_map(0x20000000,0x10000)
    uc.reg_write(UC_RISCV_REG_SP,0x2000fff0)
    with args.elf.open('rb') as binary:
        elf = ELFFile(binary)
        for segment in elf.iter_segments():
            if segment['p_type'] == 'PT_LOAD':
                uc.mem_write(segment['p_vaddr'],segment.data())
        uc.hook_add(UC_HOOK_MEM_WRITE,finish,begin=0x2000fffc,end=0x2000ffff)
        uc.emu_start(elf.header['e_entry'],0,count=1_000_000)
    if outcome != 0x600dcafe:
        raise SystemExit(f'FAILED: assertion line {outcome}')
    print('PASS: portable C firmware tests executed in RV32 emulator')
