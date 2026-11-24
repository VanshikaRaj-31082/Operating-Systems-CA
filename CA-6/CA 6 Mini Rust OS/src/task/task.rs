#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskState {
    Ready,
    Running,
    Blocked,
    Terminated,
}

impl TaskState {
    pub fn as_str(&self) -> &'static str {
        match self {
            TaskState::Ready => "READY",
            TaskState::Running => "RUNNING",
            TaskState::Blocked => "BLOCKED",
            TaskState::Terminated => "TERMINATED",
        }
    }
}

pub type TaskAction = fn(task_id: usize, iteration: usize);

#[derive(Clone, Copy)]
pub struct Task {
    pub id: usize,
    pub name: &'static str,
    pub state: TaskState,
    pub priority: u8,
    pub total_runtime_ticks: usize,
    pub remaining_quantum: usize,
    pub total_iterations: usize,
    pub iterations_completed: usize,
    pub action: TaskAction,
}

impl Task {
    pub const fn new(
        id: usize,
        name: &'static str,
        priority: u8,
        total_iterations: usize,
        action: TaskAction,
    ) -> Self {
        Self {
            id,
            name,
            state: TaskState::Ready,
            priority,
            total_runtime_ticks: 0,
            remaining_quantum: 0,
            total_iterations,
            iterations_completed: 0,
            action,
        }
    }

    pub fn execute_slice(&mut self, ticks: usize) {
        self.state = TaskState::Running;
        for _ in 0..ticks {
            if self.iterations_completed < self.total_iterations {
                self.iterations_completed += 1;
                self.total_runtime_ticks += 1;
                (self.action)(self.id, self.iterations_completed);
            }
            if self.iterations_completed >= self.total_iterations {
                self.state = TaskState::Terminated;
                break;
            }
        }
        if self.state != TaskState::Terminated {
            self.state = TaskState::Ready;
        }
    }
}
