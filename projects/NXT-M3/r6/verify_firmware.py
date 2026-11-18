"""Record actual C execution and static checks for the MCU source."""
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys

HERE=Path(__file__).resolve().parent
fw=HERE/'FIRMWARE_PROTOTYPE'
cli=argparse.ArgumentParser()
cli.add_argument('--gcc',type=Path,required=True)
cli.add_argument('--clang',type=Path,required=True)
args=cli.parse_args()
work=HERE/'.local'
work.mkdir(exist_ok=True)
elf=work/'nxt-c-test-rv32.elf'
commands=[
    [str(args.gcc),'--version'],
    [str(args.gcc),'-march=rv32im','-mabi=ilp32','-mno-relax','-msmall-data-limit=0',
     '-std=c11','-Os','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-nostdlib',
     '-DNXT_EMULATED','-Wl,-T,FIRMWARE_PROTOTYPE/machine_test.ld,--no-relax',
     'FIRMWARE_PROTOTYPE/nxt.c','FIRMWARE_PROTOTYPE/test.c','FIRMWARE_PROTOTYPE/machine_test.c','-o',str(elf)],
    [sys.executable,str(fw/'machine_run.py'),str(elf)],
    [str(args.clang),'--target=arm-none-eabi','-mcpu=cortex-m0plus','-mthumb','-std=c11',
     '-Wall','-Wextra','-Werror','-Wno-missing-multilib','-ffreestanding','-fsyntax-only',
     'FIRMWARE_PROTOTYPE/nxt.c','FIRMWARE_PROTOTYPE/stm32c011.c'],
    [sys.executable,str(fw/'host_packet.py'),'123456789','--mask','7','--seq','41','--output',str(work/'example.bin')]
]
report=[]
for argv in commands:
    result=subprocess.run(argv,cwd=HERE,capture_output=True,text=True,errors='replace')
    report.extend([subprocess.list2cmdline(argv),f'exit={result.returncode}',result.stdout,result.stderr])
    if result.returncode:
        (HERE/'evidence'/'firmware_check.txt').write_text('\n'.join(report),encoding='utf-8')
        sys.exit(result.returncode)
payload=(work/'example.bin').read_bytes()
assert len(payload)==48
report.extend(['RV32 emulator executes the portable C tests; STM32 frontend validates syntax only.',
               'ARM link unsupported by installed Espressif Clang backend; alternate Zig stopped by host application control.',
               'RV32 file SHA256 '+hashlib.sha256(elf.read_bytes()).hexdigest(),'V1 9-digit binary frame hex: '+payload.hex(' ')])
(HERE/'evidence'/'firmware_check.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print(report[-4])
