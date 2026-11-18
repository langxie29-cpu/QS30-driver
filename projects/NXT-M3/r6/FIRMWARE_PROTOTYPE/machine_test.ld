ENTRY(test_entry)
PHDRS { image PT_LOAD FLAGS(7); }
SECTIONS {
    . = 0x10000;
    .text : { *(.text*) } :image
    .rodata : { *(.rodata*) *(.srodata*) } :image
    .data : { *(.data*) *(.sdata*) } :image
    .bss : { *(.bss*) *(.sbss*) *(COMMON) } :image
}
