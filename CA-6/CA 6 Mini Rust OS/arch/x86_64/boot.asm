; CA-6 Mini Rust OS: Multiboot 1 to 64-bit Long Mode Bootloader
global _start
extern rust_main

MULTIBOOT_PAGE_ALIGN  equ 1 << 0
MULTIBOOT_MEMORY_INFO equ 1 << 1
MULTIBOOT_MAGIC       equ 0x1BADB002
MULTIBOOT_FLAGS       equ MULTIBOOT_PAGE_ALIGN | MULTIBOOT_MEMORY_INFO
MULTIBOOT_CHECKSUM    equ -(MULTIBOOT_MAGIC + MULTIBOOT_FLAGS)

section .multiboot_header
align 4
    dd MULTIBOOT_MAGIC
    dd MULTIBOOT_FLAGS
    dd MULTIBOOT_CHECKSUM

section .bss
align 4096
pml4_table:
    resb 4096
pdp_table:
    resb 4096
pd_table0:
    resb 4096 * 4      ; 16 KB: 4 Page Directories to map 4 GB (2048 * 2MB)
stack_bottom:
    resb 65536         ; 64 KB kernel stack
stack_top:

section .rodata
gdt64:
    dq 0               ; 0x00: Null descriptor
.code: equ $ - gdt64   ; 0x08: Code descriptor (64-bit)
    dq (1<<43) | (1<<44) | (1<<47) | (1<<53)
.data: equ $ - gdt64   ; 0x10: Data descriptor (64-bit)
    dq (1<<41) | (1<<44) | (1<<47)
.pointer:
    dw $ - gdt64 - 1
    dq gdt64

section .text
bits 32
_start:
    ; Set up temporary 32-bit stack
    mov esp, stack_top

    ; Save Multiboot info pointer (EBX) and magic (EAX)
    push eax
    push ebx

    ; Verify Multiboot magic
    cmp eax, 0x2BADB002
    jne .no_multiboot

    ; Check if CPUID is supported
    call check_cpuid
    ; Check if 64-bit long mode is supported
    call check_long_mode

    ; Set up identity paging for the first 1 GB (512 * 2MB)
    call setup_page_tables
    call enable_paging

    ; Load 64-bit Global Descriptor Table
    lgdt [gdt64.pointer]

    ; Far jump to 64-bit mode
    jmp gdt64.code:long_mode_start

.no_multiboot:
    mov al, "M"
    jmp error_32

check_cpuid:
    ; Check if CPUID is supported by attempting to flip ID bit (bit 21) in FLAGS
    pushfd
    pop eax
    mov ecx, eax
    xor eax, 1 << 21
    push eax
    popfd
    pushfd
    pop eax
    push ecx
    popfd
    cmp eax, ecx
    je .no_cpuid
    ret
.no_cpuid:
    mov al, "C"
    jmp error_32

check_long_mode:
    ; Test if extended processor info is available
    mov eax, 0x80000000
    cpuid
    cmp eax, 0x80000001
    jb .no_long_mode

    ; Extended function 0x80000001: EDX bit 29 is LM (Long Mode)
    mov eax, 0x80000001
    cpuid
    test edx, 1 << 29
    jz .no_long_mode
    ret
.no_long_mode:
    mov al, "L"
    jmp error_32

setup_page_tables:
    ; Map first PML4 entry to pdp_table (Present | Writable = 0x03)
    mov eax, pdp_table
    or eax, 0b11
    mov [pml4_table], eax
    mov dword [pml4_table + 4], 0

    ; Map 4 PDP entries to 4 consecutive Page Directories (pd_table0..3) to map 4 GB
    mov eax, pd_table0
    or eax, 0b11
    mov [pdp_table], eax
    mov dword [pdp_table + 4], 0

    mov eax, pd_table0 + 4096
    or eax, 0b11
    mov [pdp_table + 8], eax
    mov dword [pdp_table + 12], 0

    mov eax, pd_table0 + 8192
    or eax, 0b11
    mov [pdp_table + 16], eax
    mov dword [pdp_table + 20], 0

    mov eax, pd_table0 + 12288
    or eax, 0b11
    mov [pdp_table + 24], eax
    mov dword [pdp_table + 28], 0

    ; Map 2048 entries of 2MB pages (512 * 4 = 4 GB identity map)
    ; Flags: Present | Writable | Huge Page (2MB) = 0x83
    mov ecx, 0
.map_pd_table:
    mov eax, 0x200000          ; 2MB
    mul ecx
    or eax, 0b10000011         ; Present | Writable | Huge
    mov [pd_table0 + ecx * 8], eax
    mov dword [pd_table0 + ecx * 8 + 4], 0
    inc ecx
    cmp ecx, 2048
    jne .map_pd_table
    ret

enable_paging:
    ; Load CR3 with physical address of PML4
    mov eax, pml4_table
    mov cr3, eax

    ; Enable PAE (Physical Address Extension) in CR4 (bit 5)
    mov eax, cr4
    or eax, 1 << 5
    mov cr4, eax

    ; Enable Long Mode in EFER MSR (MSR 0xC0000080, bit 8)
    mov ecx, 0xC0000080
    rdmsr
    or eax, 1 << 8
    wrmsr

    ; Enable Paging in CR0 (bit 31) and Protection (bit 0)
    mov eax, cr0
    or eax, (1 << 31) | (1 << 0)
    mov cr0, eax
    ret

error_32:
    ; Print "ERR: X" to VGA text buffer at 0xb8000
    mov dword [0xb8000], 0x4f524f45   ; 'E', 'R' (White on Red)
    mov dword [0xb8004], 0x4f3a4f52   ; 'R', ':'
    mov byte  [0xb8008], al           ; error code char
    mov byte  [0xb8009], 0x4f
.halt:
    hlt
    jmp .halt

bits 64
long_mode_start:
    ; Reload 64-bit data segment registers
    mov ax, gdt64.data
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    ; Initialize 64-bit stack
    mov rsp, stack_top

    ; Call the Rust kernel entry point
    call rust_main

    ; If rust_main ever returns, halt CPU
.halt_loop:
    cli
    hlt
    jmp .halt_loop
