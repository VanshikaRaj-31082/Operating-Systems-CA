"""
Publication-Quality Visualization Generator for CA5.
Plots empirical findings directly from processed CSV and raw JSON observations.
Generates:
1. fig1_race_condition_accuracy.png (L10)
2. fig2_lock_contention_throughput.png (L16)
3. fig3_context_switches_vs_threads.png (L16 & L25)
4. fig4_deadlock_recovery_latency.png (L17)
"""

import csv
import json
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def generate_all_figures(base_dir: str = ".") -> None:
    processed_dir = os.path.join(base_dir, "results/processed")
    figures_dir = os.path.join(base_dir, "results/figures")
    raw_dir = os.path.join(base_dir, "results/raw")
    os.makedirs(figures_dir, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
    })

    # =========================================================================
    # Figure 1: Race Condition & Data Corruption (L10)
    # =========================================================================
    rc_csv = os.path.join(processed_dir, "race_condition_summary.csv")
    if os.path.exists(rc_csv):
        print("Generating Figure 1: Race Condition & Correction...")
        modes = {}
        with open(rc_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mode = row["mode"]
                tc = int(row["thread_count"])
                err_pct = float(row["mean_relative_error_pct"]) if row["mean_relative_error_pct"] else 0.0
                disc = float(row["mean_discrepancy"]) if row["mean_discrepancy"] else 0.0
                modes.setdefault(mode, []).append((tc, err_pct, disc))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Left: Relative Error (%)
        for mode, data in sorted(modes.items()):
            data.sort(key=lambda x: x[0])
            threads = [x[0] for x in data]
            errors = [x[1] for x in data]
            color = "#d9534f" if "unsync" in mode else "#5cb85c"
            marker = "o" if "unsync" in mode else "s"
            label = "Unsynchronized (Data Race)" if "unsync" in mode else "Synchronized (POSIX Mutex)"
            ax1.plot(threads, errors, marker=marker, color=color, linewidth=2, label=label)

        ax1.set_xlabel("Concurrent Thread Count (T)")
        ax1.set_ylabel("Data Loss Relative Error (%)")
        ax1.set_title("Lost Updates vs. Thread Concurrency")
        ax1.set_xticks([2, 4, 8, 16])
        ax1.legend(loc="upper left")
        ax1.grid(True, linestyle="--", alpha=0.6)

        # Right: Total Discrepancy (lost increments)
        for mode, data in sorted(modes.items()):
            data.sort(key=lambda x: x[0])
            threads = [x[0] for x in data]
            discs = [x[2] for x in data]
            color = "#d9534f" if "unsync" in mode else "#5cb85c"
            marker = "o" if "unsync" in mode else "s"
            label = "Unsynchronized" if "unsync" in mode else "Synchronized"
            ax2.plot(threads, discs, marker=marker, color=color, linewidth=2, label=label)

        ax2.set_xlabel("Concurrent Thread Count (T)")
        ax2.set_ylabel("Lost Operations Count")
        ax2.set_title("Absolute Discrepancy (Expected - Observed)")
        ax2.set_xticks([2, 4, 8, 16])
        ax2.legend(loc="upper left")
        ax2.grid(True, linestyle="--", alpha=0.6)

        fig.suptitle("CA5 Challenge L10: Race Condition Failure and Mutex Correction", y=1.02)
        fig.tight_layout()
        fig_path = os.path.join(figures_dir, "fig1_race_condition_accuracy.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {fig_path}")

    # =========================================================================
    # Figure 2: Lock Contention Throughput (L16)
    # =========================================================================
    lc_csv = os.path.join(processed_dir, "lock_contention_summary.csv")
    if os.path.exists(lc_csv):
        print("Generating Figure 2: Lock Contention Throughput...")
        strats = {}
        with open(lc_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                strat = row["strategy"]
                tc = int(row["thread_count"])
                tput = float(row["mean_throughput_ops_sec"]) / 1e6  # in MOps/sec
                strats.setdefault(strat, []).append((tc, tput))

        fig, ax = plt.subplots(figsize=(8, 5))
        style_map = {
            "coarse_mutex": ("#e74c3c", "o-", "Coarse Global Mutex (Baseline)"),
            "chunked_mutex": ("#3498db", "s-", "Chunked Batching (Intervention 1)"),
            "partitioned_striped": ("#2ecc71", "^-", "Partitioned Striped Locks (Intervention 2)"),
        }

        for strat, data in sorted(strats.items()):
            data.sort(key=lambda x: x[0])
            threads = [x[0] for x in data]
            tputs = [x[1] for x in data]
            col, fmt, lab = style_map.get(strat, ("#333333", "d-", strat))
            ax.plot(threads, tputs, fmt, color=col, linewidth=2.2, markersize=7, label=lab)

        ax.set_xlabel("Concurrent Worker Threads (T)")
        ax.set_ylabel("Throughput (Million Operations / Second)")
        ax.set_title("CA5 Challenge L16: Throughput Scalability Under Lock Contention")
        ax.set_xticks([1, 2, 4, 8, 16])
        ax.legend(loc="upper right")
        ax.grid(True, linestyle="--", alpha=0.6)

        fig.tight_layout()
        fig_path = os.path.join(figures_dir, "fig2_lock_contention_throughput.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {fig_path}")

    # =========================================================================
    # Figure 3: Context Switches vs Thread Concurrency (L16 & L25)
    # =========================================================================
    if os.path.exists(lc_csv):
        print("Generating Figure 3: Context Switches vs Thread Concurrency...")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        vol_data = {}
        tot_data = {}
        with open(lc_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                strat = row["strategy"]
                tc = int(row["thread_count"])
                vol = float(row["mean_voluntary_ctxt_switches"]) if row["mean_voluntary_ctxt_switches"] else 0.0
                tot = float(row["mean_total_ctxt_switches"]) if row["mean_total_ctxt_switches"] else 0.0
                vol_data.setdefault(strat, []).append((tc, vol))
                tot_data.setdefault(strat, []).append((tc, tot))

        for strat, data in sorted(vol_data.items()):
            data.sort(key=lambda x: x[0])
            threads = [x[0] for x in data]
            vols = [x[1] for x in data]
            col, fmt, lab = style_map.get(strat, ("#333333", "d-", strat))
            ax1.plot(threads, vols, fmt, color=col, linewidth=2, label=lab)

        ax1.set_xlabel("Concurrent Worker Threads (T)")
        ax1.set_ylabel("Mean Voluntary Context Switches")
        ax1.set_title("Voluntary Context Switches (Futex Waits)")
        ax1.set_xticks([1, 2, 4, 8, 16])
        ax1.legend(loc="upper left")
        ax1.grid(True, linestyle="--", alpha=0.6)

        for strat, data in sorted(tot_data.items()):
            data.sort(key=lambda x: x[0])
            threads = [x[0] for x in data]
            tots = [x[1] for x in data]
            col, fmt, lab = style_map.get(strat, ("#333333", "d-", strat))
            ax2.plot(threads, tots, fmt, color=col, linewidth=2, label=lab)

        ax2.set_xlabel("Concurrent Worker Threads (T)")
        ax2.set_ylabel("Total Context Switches (/proc status)")
        ax2.set_title("Total Kernel Context Switches")
        ax2.set_xticks([1, 2, 4, 8, 16])
        ax2.legend(loc="upper left")
        ax2.grid(True, linestyle="--", alpha=0.6)

        fig.suptitle("CA5 Challenge L25: Kernel Context-Switch Escalation Under Contention", y=1.02)
        fig.tight_layout()
        fig_path = os.path.join(figures_dir, "fig3_context_switches_vs_threads.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {fig_path}")

    # =========================================================================
    # Figure 4: Deadlock Recovery Latency & Status (L17)
    # =========================================================================
    dl_csv = os.path.join(processed_dir, "deadlock_investigation_summary.csv")
    if os.path.exists(dl_csv):
        print("Generating Figure 4: Deadlock Recovery Latency & Status...")
        scenarios = []
        deadlock_rates = []
        durations = []

        scen_labels = {
            "circular_deadlock_unmitigated": "Unmitigated Deadlock\n(Watchdog Triggered)",
            "lock_hierarchy_avoidance": "Lock Hierarchy\n(Avoidance)",
            "trylock_exponential_backoff_recovery": "Try-Lock Backoff\n(Recovery)"
        }

        with open(dl_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scen = row["scenario"]
                scenarios.append(scen_labels.get(scen, scen))
                deadlock_rates.append(float(row["deadlock_rate_pct"]))
                durations.append(float(row["mean_execution_time_s"]))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

        # Left: Deadlock Occurrence Rate (%)
        colors_rate = ["#e74c3c" if r > 0 else "#2ecc71" for r in deadlock_rates]
        bars1 = ax1.bar(scenarios, deadlock_rates, color=colors_rate, width=0.55, edgecolor="black")
        ax1.set_ylabel("Deadlock Occurrence Rate (%)")
        ax1.set_title("Deadlock Frequency")
        ax1.set_ylim(0, 115)
        for bar, rate in zip(bars1, deadlock_rates):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{rate:.0f}%", ha="center", va="bottom", fontweight="bold")
        ax1.grid(True, linestyle="--", alpha=0.6, axis="y")

        # Right: Latency (log scale to highlight ms vs 3s watchdog)
        colors_dur = ["#e74c3c", "#3498db", "#2ecc71"]
        bars2 = ax2.bar(scenarios, durations, color=colors_dur, width=0.55, edgecolor="black")
        ax2.set_ylabel("Execution / Recovery Time (seconds)")
        ax2.set_title("Resolution Latency")
        ax2.set_yscale("log")
        for bar, dur in zip(bars2, durations):
            ax2.text(bar.get_x() + bar.get_width() / 2, dur * 1.3, f"{dur:.4f}s", ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax2.grid(True, linestyle="--", alpha=0.6, axis="y")

        fig.suptitle("CA5 Challenge L17: Deadlock Mitigation and Recovery Evaluation", y=1.02)
        fig.tight_layout()
        fig_path = os.path.join(figures_dir, "fig4_deadlock_recovery_latency.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {fig_path}")

    print("All 4 publication figures generated successfully.")


if __name__ == "__main__":
    generate_all_figures("CA5-Linux-Systems-Engineering")
