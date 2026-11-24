use crate::task::{Task, TaskState};
use crate::sync::SpinLock;

pub const MAX_TASKS: usize = 8;

pub struct RoundRobinScheduler {
    tasks: [Option<Task>; MAX_TASKS],
    task_count: usize,
    current_index: usize,
    time_quantum: usize,
    total_context_switches: usize,
    total_ticks: usize,
}

impl RoundRobinScheduler {
    pub const fn new(time_quantum: usize) -> Self {
        Self {
            tasks: [None, None, None, None, None, None, None, None],
            task_count: 0,
            current_index: 0,
            time_quantum,
            total_context_switches: 0,
            total_ticks: 0,
        }
    }

    pub fn set_quantum(&mut self, quantum: usize) {
        self.time_quantum = if quantum > 0 { quantum } else { 1 };
    }

    pub fn add_task(&mut self, task: Task) -> bool {
        for slot in self.tasks.iter_mut() {
            if slot.is_none() {
                *slot = Some(task);
                self.task_count += 1;
                return true;
            }
        }
        false
    }

    pub fn has_ready_tasks(&self) -> bool {
        for slot in self.tasks.iter() {
            if let Some(ref t) = slot {
                if t.state == TaskState::Ready {
                    return true;
                }
            }
        }
        false
    }

    pub fn pick_next_task_index(&mut self) -> Option<usize> {
        if self.task_count == 0 {
            return None;
        }

        let start = self.current_index;
        for i in 0..MAX_TASKS {
            let idx = (start + i) % MAX_TASKS;
            if let Some(ref t) = self.tasks[idx] {
                if t.state == TaskState::Ready {
                    self.current_index = (idx + 1) % MAX_TASKS;
                    return Some(idx);
                }
            }
        }
        None
    }

    pub fn schedule_next(&mut self) -> bool {
        let task_idx = match self.pick_next_task_index() {
            Some(idx) => idx,
            None => return false,
        };

        self.total_context_switches += 1;
        let quantum = self.time_quantum;

        if let Some(ref mut task) = self.tasks[task_idx] {
            let task_id = task.id;
            let task_name = task.name;
            let prev_done = task.iterations_completed;
            let total = task.total_iterations;

            crate::println!(
                "[SCHED] [SWITCH #{}] -> Dispatching Task {} ('{}') [State: READY -> RUNNING]",
                self.total_context_switches, task_id, task_name
            );

            // Execute time slice (up to quantum units)
            let remaining_work = total.saturating_sub(prev_done);
            let ticks_to_run = if remaining_work < quantum { remaining_work } else { quantum };
            
            task.execute_slice(ticks_to_run);
            self.total_ticks += ticks_to_run;

            if task.state == TaskState::Terminated {
                crate::println!(
                    "[SCHED] Task {} ('{}') completed all {}/{} iterations. [State: TERMINATED]",
                    task_id, task_name, task.iterations_completed, total
                );
            } else {
                crate::println!(
                    "[SCHED] Task {} ('{}') quantum expired (ran {} ticks, progress {}/{}). [State: RUNNING -> READY]",
                    task_id, task_name, ticks_to_run, task.iterations_completed, total
                );
            }
        }

        true
    }

    pub fn run_all(&mut self) {
        crate::println!("\n========================================================");
        crate::println!("  STARTING ROUND ROBIN SCHEDULER EXECUTION (Quantum: {})", self.time_quantum);
        crate::println!("========================================================");

        let mut round = 1;
        while self.has_ready_tasks() {
            crate::println!("--- Scheduler Cycle #{} ---", round);
            let mut ran_any = false;
            // Run each ready task up to one time slice per round
            for _ in 0..self.task_count {
                if self.schedule_next() {
                    ran_any = true;
                }
            }
            if !ran_any {
                break;
            }
            round += 1;
        }

        crate::println!("========================================================");
        crate::println!("  SCHEDULER FINISHED: Total Switches: {}, Total Ticks: {}",
            self.total_context_switches, self.total_ticks);
        crate::println!("========================================================\n");
    }
}

pub static SCHEDULER: SpinLock<RoundRobinScheduler> = SpinLock::new(RoundRobinScheduler::new(2));

// Demonstration task routines
fn task_telemetry(id: usize, iter: usize) {
    crate::println!("  [Task {} - Telemetry] Reading temperature sensor: {} C", id, 42 + (iter * 3) % 15);
}

fn task_memory_check(id: usize, iter: usize) {
    crate::println!("  [Task {} - MemCheck] Verifying kernel heap page frame #{}: OK", id, iter);
}

fn task_crypto_worker(id: usize, iter: usize) {
    let mock_hash = (iter * 0x1f1f1f1f) ^ 0x5a5a5a5a;
    crate::println!("  [Task {} - CryptoHash] Computed block hash for chunk #{}: {:#010x}", id, iter, mock_hash);
}

fn task_disk_cleaner(id: usize, iter: usize) {
    crate::println!("  [Task {} - DiskDaemon] Background journal flush step #{}: SYNCED", id, iter);
}

pub fn run_scheduler_demo() {
    let mut sched = SCHEDULER.lock();
    sched.set_quantum(2); // 2 ticks per time quantum

    crate::println!("[SCHED] Registering demonstration tasks in Ready Queue:");
    let t1 = Task::new(1, "Telemetry Sensor", 1, 4, task_telemetry);
    let t2 = Task::new(2, "Memory Integrity", 2, 3, task_memory_check);
    let t3 = Task::new(3, "Crypto Hash Engine", 1, 5, task_crypto_worker);
    let t4 = Task::new(4, "Disk Flush Daemon", 3, 2, task_disk_cleaner);

    crate::println!("  + Task 1: 'Telemetry Sensor' (4 iterations, Priority 1)");
    crate::println!("  + Task 2: 'Memory Integrity' (3 iterations, Priority 2)");
    crate::println!("  + Task 3: 'Crypto Hash Engine' (5 iterations, Priority 1)");
    crate::println!("  + Task 4: 'Disk Flush Daemon' (2 iterations, Priority 3)");

    sched.add_task(t1);
    sched.add_task(t2);
    sched.add_task(t3);
    sched.add_task(t4);

    sched.run_all();
}
