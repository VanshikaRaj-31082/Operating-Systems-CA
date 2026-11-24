ENTRY(_start)

SECTIONS {
    /* The kernel starts at 1MB, the standard for x86 kernels */
    . = 1M;

    .boot : {
        /* Ensure that the multiboot header is at the very beginning */
        KEEP(*(.multiboot_header))
    }

    .text : {
        *(.text .text.*)
    }

    .rodata : {
        *(.rodata .rodata.*)
    }

    .data : {
        *(.data .data.*)
    }

    .bss : {
        *(.bss .bss.*)
    }

    /DISCARD/ : {
        *(.comment)
        *(.eh_frame)
    }
}
