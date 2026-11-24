//! CA5 to CA6 Technical Bridge: Low-Level Synchronization & Micro-OS Primitives
//! Author: Vanshika Raj (USN: 25BTRCL278)
//! Demonstrates the difference between User-Space Spinlocks and Kernel Mutexes.
//! In CA6 Micro-OS:
//! - Spinlocks are used inside the kernel where interrupt handlers or non-blocking
//!   scheduler critical sections cannot sleep.
//! - Mutexes require a scheduler / task waiting queue to yield CPU timeslices.

use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Instant;

/// Minimal User-Space Spinlock using atomic compare-and-exchange (CAS).
/// Warning: In a user-space OS with preemption, spinlocks can waste CPU cycles
/// and cause priority inversion if preempted. In CA6 Micro-OS kernel, spinlocks
/// disable local interrupts.
pub struct SpinLock {
    locked: AtomicBool,
}

impl SpinLock {
    pub const fn new() -> Self {
        Self {
            locked: AtomicBool::new(false),
        }
    }

    pub fn lock(&self) {
        // Spin until compare_exchange succeeds in transitioning false -> true
        while self
            .locked
            .compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            // Hint to CPU that we are in a spin-wait loop
            std::hint::spin_loop();
        }
    }

    pub fn unlock(&self) {
        self.locked.store(false, Ordering::Release);
    }
}

fn main() {
    println!("==================================================================");
    println!("   CA5 -> CA6 RUST SYSTEMS BRIDGE: SYNCHRONIZATION BENCHMARK      ");
    println!("==================================================================");

    let num_threads = 4;
    let increments_per_thread = 250_000;
    let expected_total = num_threads * increments_per_thread;

    // 1. Lock-free Atomic fetch_add
    println!("\n1. Testing Lock-Free Atomic fetch_add (Hardware RMW Instruction):");
    let atomic_counter = Arc::new(AtomicUsize::new(0));
    let start_atomic = Instant::now();
    let mut handles = Vec::new();

    for _ in 0..num_threads {
        let counter_clone = Arc::clone(&atomic_counter);
        handles.push(thread::spawn(move || {
            for _ in 0..increments_per_thread {
                counter_clone.fetch_add(1, Ordering::Relaxed);
            }
        }));
    }
    for h in handles {
        h.join().unwrap();
    }
    let duration_atomic = start_atomic.elapsed();
    println!("   Final Counter: {} (Expected: {})", atomic_counter.load(Ordering::SeqCst), expected_total);
    println!("   Duration:      {:?}", duration_atomic);

    // 2. Standard Library Mutex (Linux futex wrapper)
    println!("\n2. Testing std::sync::Mutex (Linux futex / Sleeping Lock):");
    let mutex_counter = Arc::new(Mutex::new(0usize));
    let start_mutex = Instant::now();
    let mut handles = Vec::new();

    for _ in 0..num_threads {
        let counter_clone = Arc::clone(&mutex_counter);
        handles.push(thread::spawn(move || {
            for _ in 0..increments_per_thread {
                let mut guard = counter_clone.lock().unwrap();
                *guard += 1;
            }
        }));
    }
    for h in handles {
        h.join().unwrap();
    }
    let duration_mutex = start_mutex.elapsed();
    println!("   Final Counter: {} (Expected: {})", *mutex_counter.lock().unwrap(), expected_total);
    println!("   Duration:      {:?}", duration_mutex);

    // 3. User-Space SpinLock (Busy-wait lock)
    println!("\n3. Testing Custom Atomic SpinLock (Busy-Waiting):");
    let spin_lock = Arc::new(SpinLock::new());
    let spin_counter = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let start_spin = Instant::now();
    let mut handles = Vec::new();

    for _ in 0..num_threads {
        let lock_clone = Arc::clone(&spin_lock);
        let counter_clone = Arc::clone(&spin_counter);
        handles.push(thread::spawn(move || {
            for _ in 0..increments_per_thread {
                lock_clone.lock();
                // Inside critical section
                counter_clone.fetch_add(1, Ordering::Relaxed);
                lock_clone.unlock();
            }
        }));
    }
    for h in handles {
        h.join().unwrap();
    }
    let duration_spin = start_spin.elapsed();
    println!("   Final Counter: {} (Expected: {})", spin_counter.load(Ordering::SeqCst), expected_total);
    println!("   Duration:      {:?}", duration_spin);

    println!("\n--- Architectural Takeaways for CA6 Micro-OS ---");
    println!("* Atomic operations avoid lock overhead by emitting direct bus-locked CPU instructions (e.g. LOCK XADD on x86_64).");
    println!("* Mutexes put contended threads to sleep using kernel futexes, causing voluntary context switches.");
    println!("* Spinlocks busy-wait on CPU cores without context switches; in CA6 Micro-OS, spinlocks will guard scheduler queues.");
    println!("==================================================================");
}
