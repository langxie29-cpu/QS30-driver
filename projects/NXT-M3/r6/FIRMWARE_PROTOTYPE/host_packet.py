"""Emit binary V1 traffic for a low-voltage RS-485 host, no physical port access."""
import argparse
import binascii
from pathlib import Path
import struct

def packet(op,addr,seq,mask,data):
    body = struct.pack('<BBBBHB3B',0xa5,1,op,addr,seq,mask,*data)
    return body+struct.pack('<H',binascii.crc_hqx(body,0xffff))

def group(number, mask, seq):
    positions = [i for i in range(1,4) if mask & (1 << (i-1))]
    length = 3*len(positions)
    if not 1 <= len(number) <= length or any(c not in '0123456789' for c in number):
        raise ValueError('Enter an unsigned integer digit string that fits the display')
    spaced = number.rjust(length)
    digits = [15 if digit==' ' else int(digit) for digit in spaced]
    return (b''.join(packet(1,addr,seq,mask,digits[n*3:n*3+3]) for n,addr in enumerate(positions))
            +packet(2,0,seq,mask,[0,0,0]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('number')
    parser.add_argument('--mask', type=int, choices=range(1,8), required=True)
    parser.add_argument('--seq', type=int, choices=range(65536), required=True, metavar='0..65535')
    parser.add_argument('--output', type=Path, required=True)
    x = parser.parse_args()
    x.output.write_bytes(group(x.number,x.mask,x.seq))
