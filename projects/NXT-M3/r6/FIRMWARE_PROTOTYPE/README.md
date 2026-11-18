# Run the V1 low-voltage prototype

Native host with a C11 toolchain:

```text
cc -std=c11 -Wall -Wextra -Werror nxt.c test.c -o nxt-test
./nxt-test
python host_packet.py 123456789 --mask 7 --seq 41 --output example.bin
```

R6 ran the same C assertions in RV32 Unicorn using an installed Espressif GCC and the freestanding harness. See evidence/firmware_check.txt and REPRODUCE.md. The protocol tests do not depend on the MCU architecture. The STM32C011 minimal application is a receive-only prototype with USART1 AF0 on PB7, ISR ring buffer, monotonic SysTick, explicit fall-edge shift, latch and blank. PB6 and DE are provisioned on the schematic. Target cross-link has not been verified in this Windows application-control environment. Use a supported ARM toolchain and a fixture with the boost power domain physically disabled for hardware evaluation.

The reference host only writes frame files. Node configuration comes from the physical straps. Address 4 causes the node to stay blank. The C API can also be called locally to populate a three-digit display without the group bus.
