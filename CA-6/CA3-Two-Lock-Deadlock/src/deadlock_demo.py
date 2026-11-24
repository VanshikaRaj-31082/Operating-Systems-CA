
import threading
import multiprocessing


def reproduce_deadlock():
    lock_a = threading.Lock()
    lock_b = threading.Lock()

    barrier = threading.Barrier(2)

    def thread_1():
        print("Thread 1: Acquiring Lock A", flush=True)

        with lock_a:
            print("Thread 1: Acquired Lock A", flush=True)

            barrier.wait()

            print("Thread 1: Waiting for Lock B", flush=True)

            with lock_b:
                print("Thread 1: Acquired Lock B", flush=True)

    def thread_2():
        print("Thread 2: Acquiring Lock B", flush=True)

        with lock_b:
            print("Thread 2: Acquired Lock B", flush=True)

            barrier.wait()

            print("Thread 2: Waiting for Lock A", flush=True)

            with lock_a:
                print("Thread 2: Acquired Lock A", flush=True)

    t1 = threading.Thread(target=thread_1)
    t2 = threading.Thread(target=thread_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


def main():
    print("Starting Two-Lock Deadlock Demonstration\n")

    process = multiprocessing.Process(
        target=reproduce_deadlock
    )

    process.start()
    process.join(timeout=3)

    if process.is_alive():
        print("\nDEADLOCK DETECTED!")
        print("Both threads are waiting for each other's locks.")

        process.terminate()
        process.join()

        print("Deadlocked process safely terminated.")

    else:
        print("No deadlock occurred.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
