"""
CA-3 Phase 2: Diagram Generation Script
Generates high-resolution Resource Allocation Graph (RAG) and Wait-For Graph (WFG) figures.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

DIAGRAM_DIR = Path(__file__).resolve().parent


def render_rag(save_path: Path):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_xlim(-0.2, 3.2)
    ax.set_ylim(-0.5, 3.5)
    ax.axis('off')
    ax.set_title('Resource Allocation Graph (RAG)', fontsize=15, fontweight='bold', pad=15)

    # Thread nodes
    t1 = plt.Circle((0.5, 2.5), 0.35, color='#90CAF9', ec='#1565C0', lw=2.5, zorder=3)
    t2 = plt.Circle((2.5, 0.5), 0.35, color='#90CAF9', ec='#1565C0', lw=2.5, zorder=3)
    ax.add_patch(t1)
    ax.add_patch(t2)
    ax.text(0.5, 2.5, 'Thread 1\n(T1)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax.text(2.5, 0.5, 'Thread 2\n(T2)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)

    # Resource nodes
    la = patches.FancyBboxPatch((0.15, 0.15), 0.7, 0.7, boxstyle='round,pad=0.05', ec='#E65100', fc='#FFE0B2', lw=2.5, zorder=3)
    lb = patches.FancyBboxPatch((2.15, 2.15), 0.7, 0.7, boxstyle='round,pad=0.05', ec='#E65100', fc='#FFE0B2', lw=2.5, zorder=3)
    ax.add_patch(la)
    ax.add_patch(lb)
    ax.text(0.5, 0.72, 'Lock A', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax.text(2.5, 2.72, 'Lock B', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax.plot(0.5, 0.38, 'o', color='#E65100', markersize=8, zorder=4)
    ax.plot(2.5, 2.38, 'o', color='#E65100', markersize=8, zorder=4)

    # Allocation edges (solid green)
    ax.annotate('', xy=(0.5, 2.1), xytext=(0.5, 0.95), arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=2.5, mutation_scale=20))
    ax.text(0.12, 1.5, 'Allocated\n(Holds)', color='#2E7D32', fontweight='bold', fontsize=9, ha='center')
    ax.annotate('', xy=(2.5, 0.9), xytext=(2.5, 2.05), arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=2.5, mutation_scale=20))
    ax.text(2.88, 1.5, 'Allocated\n(Holds)', color='#2E7D32', fontweight='bold', fontsize=9, ha='center')

    # Request edges (dashed red)
    ax.annotate('', xy=(2.1, 2.5), xytext=(0.9, 2.5), arrowprops=dict(arrowstyle='->', color='#C62828', lw=2.5, linestyle='--', mutation_scale=20))
    ax.text(1.5, 2.68, 'Requests (Blocked)', color='#C62828', fontweight='bold', fontsize=9, ha='center')
    ax.annotate('', xy=(0.9, 0.5), xytext=(2.1, 0.5), arrowprops=dict(arrowstyle='->', color='#C62828', lw=2.5, linestyle='--', mutation_scale=20))
    ax.text(1.5, 0.32, 'Requests (Blocked)', color='#C62828', fontweight='bold', fontsize=9, ha='center')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def render_wfg(save_path: Path):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(-0.5, 3.5)
    ax.axis('off')
    ax.set_title('Wait-For Graph (WFG)', fontsize=15, fontweight='bold', pad=15)

    wt1 = plt.Circle((0.5, 1.5), 0.45, color='#FFCDD2', ec='#C62828', lw=2.5, zorder=3)
    wt2 = plt.Circle((2.5, 1.5), 0.45, color='#FFCDD2', ec='#C62828', lw=2.5, zorder=3)
    ax.add_patch(wt1)
    ax.add_patch(wt2)
    ax.text(0.5, 1.5, 'Thread 1\n(Holds A)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax.text(2.5, 1.5, 'Thread 2\n(Holds B)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)

    # Arcs forming circular wait
    ax.annotate('', xy=(2.2, 1.8), xytext=(0.8, 1.8), arrowprops=dict(arrowstyle='->', color='#B71C1C', lw=3, connectionstyle='arc3,rad=-0.4', mutation_scale=22))
    ax.text(1.5, 2.45, 'Waits for Lock B held by T2', color='#B71C1C', fontweight='bold', fontsize=10, ha='center')

    ax.annotate('', xy=(0.8, 1.2), xytext=(2.2, 1.2), arrowprops=dict(arrowstyle='->', color='#B71C1C', lw=3, connectionstyle='arc3,rad=-0.4', mutation_scale=22))
    ax.text(1.5, 0.55, 'Waits for Lock A held by T1', color='#B71C1C', fontweight='bold', fontsize=10, ha='center')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def render_combined(save_path: Path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: RAG
    ax1.set_xlim(-0.2, 3.2)
    ax1.set_ylim(-0.5, 3.5)
    ax1.axis('off')
    ax1.set_title('(A) Resource Allocation Graph (RAG)', fontsize=14, fontweight='bold', pad=15)

    t1 = plt.Circle((0.5, 2.5), 0.35, color='#90CAF9', ec='#1565C0', lw=2.5, zorder=3)
    t2 = plt.Circle((2.5, 0.5), 0.35, color='#90CAF9', ec='#1565C0', lw=2.5, zorder=3)
    ax1.add_patch(t1)
    ax1.add_patch(t2)
    ax1.text(0.5, 2.5, 'Thread 1\n(T1)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax1.text(2.5, 0.5, 'Thread 2\n(T2)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)

    la = patches.FancyBboxPatch((0.15, 0.15), 0.7, 0.7, boxstyle='round,pad=0.05', ec='#E65100', fc='#FFE0B2', lw=2.5, zorder=3)
    lb = patches.FancyBboxPatch((2.15, 2.15), 0.7, 0.7, boxstyle='round,pad=0.05', ec='#E65100', fc='#FFE0B2', lw=2.5, zorder=3)
    ax1.add_patch(la)
    ax1.add_patch(lb)
    ax1.text(0.5, 0.72, 'Lock A', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax1.text(2.5, 2.72, 'Lock B', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax1.plot(0.5, 0.38, 'o', color='#E65100', markersize=8, zorder=4)
    ax1.plot(2.5, 2.38, 'o', color='#E65100', markersize=8, zorder=4)

    ax1.annotate('', xy=(0.5, 2.1), xytext=(0.5, 0.95), arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=2.5, mutation_scale=20))
    ax1.text(0.12, 1.5, 'Allocated\n(Holds)', color='#2E7D32', fontweight='bold', fontsize=9, ha='center')
    ax1.annotate('', xy=(2.5, 0.9), xytext=(2.5, 2.05), arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=2.5, mutation_scale=20))
    ax1.text(2.88, 1.5, 'Allocated\n(Holds)', color='#2E7D32', fontweight='bold', fontsize=9, ha='center')

    ax1.annotate('', xy=(2.1, 2.5), xytext=(0.9, 2.5), arrowprops=dict(arrowstyle='->', color='#C62828', lw=2.5, linestyle='--', mutation_scale=20))
    ax1.text(1.5, 2.68, 'Requests (Blocked)', color='#C62828', fontweight='bold', fontsize=9, ha='center')
    ax1.annotate('', xy=(0.9, 0.5), xytext=(2.1, 0.5), arrowprops=dict(arrowstyle='->', color='#C62828', lw=2.5, linestyle='--', mutation_scale=20))
    ax1.text(1.5, 0.32, 'Requests (Blocked)', color='#C62828', fontweight='bold', fontsize=9, ha='center')

    # Panel 2: WFG
    ax2.set_xlim(-0.5, 3.5)
    ax2.set_ylim(-0.5, 3.5)
    ax2.axis('off')
    ax2.set_title('(B) Wait-For Graph (WFG)', fontsize=14, fontweight='bold', pad=15)

    wt1 = plt.Circle((0.5, 1.5), 0.45, color='#FFCDD2', ec='#C62828', lw=2.5, zorder=3)
    wt2 = plt.Circle((2.5, 1.5), 0.45, color='#FFCDD2', ec='#C62828', lw=2.5, zorder=3)
    ax2.add_patch(wt1)
    ax2.add_patch(wt2)
    ax2.text(0.5, 1.5, 'Thread 1\n(Holds A)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
    ax2.text(2.5, 1.5, 'Thread 2\n(Holds B)', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)

    ax2.annotate('', xy=(2.2, 1.8), xytext=(0.8, 1.8), arrowprops=dict(arrowstyle='->', color='#B71C1C', lw=3, connectionstyle='arc3,rad=-0.4', mutation_scale=22))
    ax2.text(1.5, 2.45, 'Waits for Lock B held by T2', color='#B71C1C', fontweight='bold', fontsize=10, ha='center')

    ax2.annotate('', xy=(0.8, 1.2), xytext=(2.2, 1.2), arrowprops=dict(arrowstyle='->', color='#B71C1C', lw=3, connectionstyle='arc3,rad=-0.4', mutation_scale=22))
    ax2.text(1.5, 0.55, 'Waits for Lock A held by T1', color='#B71C1C', fontweight='bold', fontsize=10, ha='center')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    render_rag(DIAGRAM_DIR / 'resource_allocation_graph.png')
    render_wfg(DIAGRAM_DIR / 'wait_for_graph.png')
    render_combined(DIAGRAM_DIR / 'deadlock_graphs.png')
    print("All diagrams generated successfully.")
