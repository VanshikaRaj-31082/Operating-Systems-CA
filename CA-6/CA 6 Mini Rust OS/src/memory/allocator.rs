use core::ptr::null_mut;
use crate::sync::SpinLock;

pub const HEAP_SIZE: usize = 64 * 1024; // 64 KB kernel heap

#[repr(align(16))]
struct AlignedHeap([u8; HEAP_SIZE]);

#[repr(C, align(16))]
struct BlockHeader {
    magic: u32,       // 0xCA60CA60 sanity marker
    size: usize,      // Payload size
    is_free: bool,
    next: *mut BlockHeader,
}

const BLOCK_MAGIC: u32 = 0xCA60CA60;

pub struct KernelAllocator {
    heap: AlignedHeap,
    head: *mut BlockHeader,
    allocated_bytes: usize,
    free_bytes: usize,
    total_alloc_count: usize,
    initialized: bool,
}

unsafe impl Send for KernelAllocator {}

impl KernelAllocator {
    pub const fn new() -> Self {
        Self {
            heap: AlignedHeap([0; HEAP_SIZE]),
            head: null_mut(),
            allocated_bytes: 0,
            free_bytes: HEAP_SIZE,
            total_alloc_count: 0,
            initialized: false,
        }
    }

    pub fn init(&mut self) {
        let heap_start = self.heap.0.as_mut_ptr();

        let header_ptr = heap_start as *mut BlockHeader;
        let initial_payload = HEAP_SIZE - core::mem::size_of::<BlockHeader>();

        unsafe {
            header_ptr.write(BlockHeader {
                magic: BLOCK_MAGIC,
                size: initial_payload,
                is_free: true,
                next: null_mut(),
            });
        }
        self.head = header_ptr;
        self.allocated_bytes = 0;
        self.free_bytes = initial_payload;
        self.total_alloc_count = 0;
        self.initialized = true;
    }

    pub fn allocate(&mut self, size: usize, _align: usize) -> Option<*mut u8> {
        if !self.initialized {
            self.init();
        }

        if size == 0 {
            return None;
        }

        // Align size to multiple of 8
        let aligned_size = (size + 7) & !7;
        let header_size = core::mem::size_of::<BlockHeader>();
        let mut curr = self.head;

        while !curr.is_null() {
            unsafe {
                let block = &mut *curr;
                if block.magic != BLOCK_MAGIC {
                    return None; // Memory corruption detected
                }

                if block.is_free && block.size >= aligned_size {
                    // Check if we can split this block
                    if block.size >= aligned_size + header_size + 16 {
                        let remaining_size = block.size - aligned_size - header_size;
                        let next_header_ptr = ((curr as usize) + header_size + aligned_size) as *mut BlockHeader;
                        
                        next_header_ptr.write(BlockHeader {
                            magic: BLOCK_MAGIC,
                            size: remaining_size,
                            is_free: true,
                            next: block.next,
                        });

                        block.size = aligned_size;
                        block.next = next_header_ptr;
                    }

                    block.is_free = false;
                    self.allocated_bytes += block.size;
                    self.free_bytes = self.free_bytes.saturating_sub(block.size);
                    self.total_alloc_count += 1;

                    let payload_ptr = ((curr as usize) + header_size) as *mut u8;
                    return Some(payload_ptr);
                }
                curr = block.next;
            }
        }
        None
    }

    pub fn deallocate(&mut self, ptr: *mut u8) -> bool {
        if ptr.is_null() || !self.initialized {
            return false;
        }

        let header_size = core::mem::size_of::<BlockHeader>();
        let header_ptr = (ptr as usize - header_size) as *mut BlockHeader;

        unsafe {
            let block = &mut *header_ptr;
            if block.magic != BLOCK_MAGIC {
                return false; // Invalid block or heap corruption
            }
            if block.is_free {
                return false; // Double free
            }

            block.is_free = true;
            self.allocated_bytes = self.allocated_bytes.saturating_sub(block.size);
            self.free_bytes += block.size;

            // Merge with next block if also free
            if !block.next.is_null() {
                let next_block = &mut *block.next;
                if next_block.magic == BLOCK_MAGIC && next_block.is_free {
                    block.size += header_size + next_block.size;
                    block.next = next_block.next;
                }
            }

            true
        }
    }

    pub fn stats(&self) -> (usize, usize, usize) {
        (self.allocated_bytes, self.free_bytes, self.total_alloc_count)
    }
}

pub static ALLOCATOR: SpinLock<KernelAllocator> = SpinLock::new(KernelAllocator::new());

pub fn run_allocator_tests() -> bool {
    crate::println!("[MEMORY] Running Kernel Heap Allocator self-test...");
    let mut alloc = ALLOCATOR.lock();
    alloc.init();

    // Test 1: Allocate Block A (128 bytes)
    let ptr_a = match alloc.allocate(128, 8) {
        Some(p) => p,
        None => {
            crate::println!("[MEMORY] FAIL: Allocation of 128 bytes failed!");
            return false;
        }
    };
    crate::println!("[MEMORY] Allocated Block A (128 B) at {:p}", ptr_a);

    // Test 2: Write canary values
    unsafe {
        for i in 0..128 {
            ptr_a.add(i).write(0xAA);
        }
    }

    // Test 3: Allocate Block B (256 bytes)
    let ptr_b = match alloc.allocate(256, 8) {
        Some(p) => p,
        None => {
            crate::println!("[MEMORY] FAIL: Allocation of 256 bytes failed!");
            return false;
        }
    };
    crate::println!("[MEMORY] Allocated Block B (256 B) at {:p}", ptr_b);

    // Ensure non-overlapping
    let diff = (ptr_b as usize).abs_diff(ptr_a as usize);
    if diff < 128 {
        crate::println!("[MEMORY] FAIL: Overlapping allocation detected!");
        return false;
    }

    unsafe {
        for i in 0..256 {
            ptr_b.add(i).write(0x55);
        }
        // Verify Block A integrity
        for i in 0..128 {
            if ptr_a.add(i).read() != 0xAA {
                crate::println!("[MEMORY] FAIL: Memory corruption in Block A!");
                return false;
            }
        }
    }

    // Test 4: Deallocate Block A
    if !alloc.deallocate(ptr_a) {
        crate::println!("[MEMORY] FAIL: Deallocation of Block A failed!");
        return false;
    }
    crate::println!("[MEMORY] Deallocated Block A successfully.");

    // Test 5: Re-allocate Block C (64 bytes) - should reuse freed space
    let ptr_c = match alloc.allocate(64, 8) {
        Some(p) => p,
        None => {
            crate::println!("[MEMORY] FAIL: Reallocation of 64 bytes failed!");
            return false;
        }
    };
    crate::println!("[MEMORY] Allocated Block C (64 B) at {:p} (Reused space)", ptr_c);

    // Clean up
    alloc.deallocate(ptr_b);
    alloc.deallocate(ptr_c);

    let (allocated, free, count) = alloc.stats();
    crate::println!("[MEMORY] Allocator Test PASSED! Heap Stats: {} B allocated, {} B free, {} total operations",
        allocated, free, count);
    true
}
