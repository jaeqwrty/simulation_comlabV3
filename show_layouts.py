"""Show the current and proposed safer ComLab V3 layouts.

This is a clean layout-only diagram. It does not animate agents; it focuses on
the room arrangement, workstation placement, exits, locker position, Data Com
area, and evacuation direction arrows.

Usage:
    python show_layouts.py
    python show_layouts.py --save comlab_layouts.png
"""

from __future__ import annotations

import argparse
from dataclasses import replace

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle

from comlab_v3_sim import ComLabV3Simulation, default_scenarios


COLORS = {
    "room": "#f8fafc",
    "grid": "#cbd5e1",
    "wall": "#111827",
    "workstation": "#475569",
    "aisle": "#e0f2fe",
    "exit": "#16a34a",
    "locker": "#facc15",
    "data": "#fb923c",
    "extinguisher": "#ef4444",
    "arrow": "#2563eb",
    "safe_arrow": "#059669",
}


def add_cell(ax, x: int, y: int, color: str, alpha: float = 1.0, label: str | None = None) -> None:
    ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=color, edgecolor="white", linewidth=1.0, alpha=alpha))
    if label:
        ax.text(x, y, label, ha="center", va="center", fontsize=7, weight="bold")


def add_arrow(ax, start: tuple[float, float], end: tuple[float, float], color: str, label: str | None = None) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=2.4,
        color=color,
        alpha=0.9,
    )
    ax.add_patch(arrow)
    if label:
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        ax.text(mid_x, mid_y - 0.25, label, ha="center", va="center", fontsize=8, color=color, weight="bold")


def setup_axis(ax, sim: ComLabV3Simulation, title: str) -> None:
    ax.set_xlim(-0.7, sim.width - 0.3)
    ax.set_ylim(sim.height - 0.2, -1.0)
    ax.set_aspect("equal")
    ax.set_facecolor(COLORS["room"])
    ax.set_xticks(range(sim.width))
    ax.set_yticks(range(sim.height))
    ax.grid(True, color=COLORS["grid"], linewidth=0.65, alpha=0.55)
    ax.tick_params(labelbottom=False, labelleft=False, length=0)
    ax.set_title(title, fontsize=13, weight="bold", pad=12)
    for spine in ax.spines.values():
        spine.set_linewidth(2)
        spine.set_color(COLORS["wall"])


def draw_layout(ax, sim: ComLabV3Simulation, safe: bool) -> None:
    setup_axis(ax, sim, "Current ComLab V3 Layout" if not safe else "Proposed Safer Layout")

    for y in range(sim.height):
        add_cell(ax, sim.aisle_x, y, COLORS["aisle"], alpha=0.42)
    for y in range(sim.height):
        add_cell(ax, 7, y, COLORS["aisle"], alpha=0.30)

    for x, y in sorted(sim.workstation_cells):
        add_cell(ax, x, y, COLORS["workstation"], alpha=0.74, label="PC")

    for x, y in sim.data_com_cells:
        add_cell(ax, x, y, COLORS["data"], alpha=0.70)
    ax.text(7, 5, "DATA\nCOM", ha="center", va="center", fontsize=7, weight="bold")

    locker_x, locker_y = sim.locker_pos
    add_cell(ax, locker_x, locker_y, COLORS["locker"], alpha=0.90, label="BAG")

    add_cell(ax, 7, 1, COLORS["extinguisher"], alpha=0.82, label="EXT")

    add_cell(ax, 8, 2, COLORS["exit"], alpha=0.88, label="EXIT")
    add_cell(ax, 8, 10, COLORS["exit"], alpha=0.88, label="EXIT")
    ax.text(8.35, 2.95, "Front Door", fontsize=8, color=COLORS["exit"], weight="bold")
    ax.text(8.35, 10.95, "Back Door", fontsize=8, color=COLORS["exit"], weight="bold")

    if safe:
        add_arrow(ax, (1.4, 1.2), (7.7, 2.0), COLORS["safe_arrow"], "front rows")
        add_arrow(ax, (1.6, 6.0), (7.8, 10.0), COLORS["safe_arrow"], "middle/rear rows")
        add_arrow(ax, (5.8, 6.0), (7.8, 10.0), COLORS["safe_arrow"])
        ax.text(
            0,
            11.65,
            "Safer changes: clear right-side exit lane, relocated bag area, assigned exits",
            fontsize=8.5,
            color="#065f46",
            weight="bold",
        )
    else:
        add_arrow(ax, (0.7, 6.0), (7.8, 10.0), COLORS["arrow"], "cross traffic")
        add_arrow(ax, (5.7, 1.5), (7.9, 10.0), COLORS["arrow"], "bag detour")
        ax.text(
            0,
            11.65,
            "Risks: right-wall exits, bag chokepoint, lateral crossing, crowded rear door",
            fontsize=8.5,
            color="#1d4ed8",
            weight="bold",
        )


def make_layout_figure(save_path: str | None = None) -> None:
    base = next(config for config in default_scenarios(seed=12) if config.name == "panicked_electrical_fire")
    current_sim = ComLabV3Simulation(replace(base, layout="current"))
    modified_sim = ComLabV3Simulation(replace(base, layout="modified", assigned_exits=True))

    fig, axes = plt.subplots(1, 2, figsize=(15, 8.5))
    draw_layout(axes[0], current_sim, safe=False)
    draw_layout(axes[1], modified_sim, safe=True)

    legend_items = [
        Rectangle((0, 0), 1, 1, facecolor=COLORS["workstation"], label="Workstation"),
        Rectangle((0, 0), 1, 1, facecolor=COLORS["aisle"], label="Clear aisle / exit lane"),
        Rectangle((0, 0), 1, 1, facecolor=COLORS["exit"], label="Exit door"),
        Rectangle((0, 0), 1, 1, facecolor=COLORS["locker"], label="Bag / locker area"),
        Rectangle((0, 0), 1, 1, facecolor=COLORS["data"], label="Data Com racks"),
        Rectangle((0, 0), 1, 1, facecolor=COLORS["extinguisher"], label="Fire extinguisher"),
        Line2D([0], [0], color=COLORS["safe_arrow"], linewidth=2.4, label="Safer evacuation flow"),
    ]
    fig.legend(handles=legend_items, loc="lower center", ncol=7, frameon=False, fontsize=8.5)
    fig.suptitle("ComLab V3 Layout Comparison for Emergency Evacuation", fontsize=16, weight="bold", y=0.98)
    plt.tight_layout(rect=(0, 0.07, 1, 0.95))

    if save_path:
        fig.savefig(save_path, dpi=180, bbox_inches="tight")
        print(f"Saved clear layout comparison to {save_path}")
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", default=None, help="Optional image path, e.g. comlab_layouts.png")
    args = parser.parse_args()
    make_layout_figure(save_path=args.save)


if __name__ == "__main__":
    main()
