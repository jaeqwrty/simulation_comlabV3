"""Run a 2D animated ComLab V3 evacuation simulation.

Usage:
    python run_2d_simulation.py

Optional examples:
    python run_2d_simulation.py --scenario panicked_electrical_fire
    python run_2d_simulation.py --scenario no_locker_detour --save comlab_v3.gif
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import replace
from math import cos, pi, sin

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from comlab_v3_sim import ComLabV3Simulation, default_scenarios


ROLE_COLORS = {
    "student": "#2563eb",
    "instructor": "#dc2626",
    "assistant": "#16a34a",
    "custodian": "#9333ea",
}


def draw_room(ax, sim: ComLabV3Simulation, title: str | None = None) -> None:
    ax.set_xlim(-0.5, sim.width - 0.5)
    ax.set_ylim(sim.height - 0.5, -0.5)
    ax.set_aspect("equal")
    ax.set_xticks(range(sim.width))
    ax.set_yticks(range(sim.height))
    ax.grid(True, color="#d4d4d8", linewidth=0.8)
    ax.set_facecolor("#f8fafc")
    ax.set_title(title or f"ComLab V3 2D Evacuation Simulation - {sim.layout.title()} Layout")

    for y in range(sim.height):
        for x in range(sim.width):
            if (x, y) not in sim.walkable:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, color="#1f2937", alpha=0.14))

    for x, y in sim.workstation_cells:
        ax.add_patch(Rectangle((x - 0.36, y - 0.36), 0.72, 0.72, color="#64748b", alpha=0.22))

    for x, y in [(8, 2), (8, 10)]:
        ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, color="#22c55e", alpha=0.45))
        ax.text(x, y, "EXIT", ha="center", va="center", fontsize=7, weight="bold")

    locker_x, locker_y = sim.locker_pos
    ax.add_patch(Rectangle((locker_x - 0.5, locker_y - 0.5), 1, 1, color="#facc15", alpha=0.55))
    ax.text(locker_x, locker_y, "BAG", ha="center", va="center", fontsize=7, weight="bold")

    for x, y in sim.data_com_cells:
        ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, color="#fb923c", alpha=0.35))
    ax.text(7, 5, "DATA\nCOM", ha="center", va="center", fontsize=7, weight="bold")

    ax.add_patch(Rectangle((7 - 0.5, 1 - 0.5), 1, 1, color="#ef4444", alpha=0.35))
    ax.text(7, 1, "EXT", ha="center", va="center", fontsize=7, weight="bold")


def animate_result(sim: ComLabV3Simulation, save_path: str | None = None, show_labels: bool = False) -> None:
    result = sim.run()
    agent_ids = [agent.agent_id for agent in sim.agents]
    role_by_id = {agent.agent_id: agent.role for agent in sim.agents}
    fig, ax = plt.subplots(figsize=(8, 9))
    draw_room(ax, sim)

    agent_artists = {}
    for agent_id in agent_ids:
        role = role_by_id[agent_id]
        marker = "o"
        if role == "instructor":
            marker = "P"
        elif role == "assistant":
            marker = "^"
        elif role == "custodian":
            marker = "s"
        point = ax.scatter(
            [],
            [],
            s=82,
            c=ROLE_COLORS[role],
            marker=marker,
            edgecolor="white",
            linewidth=0.9,
            zorder=4,
        )
        label = ax.text(
            0,
            0,
            agent_id,
            ha="center",
            va="center",
            fontsize=5.7,
            color="white",
            weight="bold",
            zorder=5,
        )
        label.set_visible(show_labels)
        agent_artists[agent_id] = (point, label)

    time_label = ax.text(0, -0.9, "", fontsize=11, weight="bold")
    status_label = ax.text(0, sim.height + 0.45, "", fontsize=9)
    legend_handles = [
        ax.scatter([], [], s=82, c=color, marker=marker, edgecolor="white", label=label)
        for label, color, marker in [
            ("Student", ROLE_COLORS["student"], "o"),
            ("Instructor", ROLE_COLORS["instructor"], "P"),
            ("Presiding Assistant", ROLE_COLORS["assistant"], "^"),
            ("Lab Custodian", ROLE_COLORS["custodian"], "s"),
        ]
    ]
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1.0))

    def spread_positions(frame_agents: list[dict[str, object]]) -> dict[str, tuple[float, float]]:
        by_cell: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
        for item in frame_agents:
            by_cell[(int(item["x"]), int(item["y"]))].append(item)

        positions: dict[str, tuple[float, float]] = {}
        for (x, y), items in by_cell.items():
            if len(items) == 1:
                positions[str(items[0]["agent_id"])] = (x, y)
                continue
            radius = min(0.34, 0.12 + len(items) * 0.015)
            for index, item in enumerate(items):
                angle = 2 * pi * index / len(items)
                positions[str(item["agent_id"])] = (x + radius * cos(angle), y + radius * sin(angle))
        return positions

    def update(frame_index: int):
        frame_agents = result.agent_frames[frame_index]
        visible = {str(item["agent_id"]): item for item in frame_agents}
        positions = spread_positions(frame_agents)
        artists = []
        phase_counts: dict[str, int] = defaultdict(int)
        for item in frame_agents:
            phase_counts[str(item["phase"])] += 1

        for agent_id, (point, label) in agent_artists.items():
            if agent_id in visible:
                x, y = positions[agent_id]
                phase = str(visible[agent_id]["phase"])
                alpha = 1.0
                if phase in {"waiting", "guiding", "holding_door"}:
                    alpha = 0.78
                point.set_offsets(np.array([[x, y]]))
                point.set_alpha(alpha)
                label.set_position((x, y))
                label.set_alpha(1.0)
            else:
                point.set_offsets(np.empty((0, 2)))
                label.set_position((-10, -10))
                label.set_alpha(0.0)
            artists.extend([point, label])

        time_label.set_text(f"Time: {frame_index}s | Active agents: {len(frame_agents)}")
        phase_text = " | ".join(f"{phase}: {count}" for phase, count in sorted(phase_counts.items()))
        status_label.set_text(phase_text)
        artists.extend([time_label, status_label])
        return artists

    ani = animation.FuncAnimation(
        fig,
        update,
        frames=len(result.frames),
        interval=120,
        blit=False,
        repeat=False,
    )

    print(result.summary())
    if save_path:
        ani.save(save_path, writer="pillow", fps=8)
        print(f"Saved animation to {save_path}")
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="panicked_electrical_fire")
    parser.add_argument("--layout", choices=["current", "modified"], default="current")
    parser.add_argument("--labels", action="store_true", help="Show agent IDs on each moving point")
    parser.add_argument("--save", default=None, help="Optional .gif output path")
    args = parser.parse_args()

    scenarios = {config.name: config for config in default_scenarios(seed=12)}
    if args.scenario not in scenarios:
        valid = ", ".join(scenarios)
        raise SystemExit(f"Unknown scenario '{args.scenario}'. Valid options: {valid}")

    sim = ComLabV3Simulation(replace(scenarios[args.scenario], layout=args.layout))
    animate_result(sim, save_path=args.save, show_labels=args.labels)


if __name__ == "__main__":
    main()
