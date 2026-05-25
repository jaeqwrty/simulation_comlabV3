"""Compare current vs safer modified ComLab V3 layouts.

This keeps the same room area and agent population, then compares:
- current workstation placement
- modified placement with a clear right-wall exit corridor and relocated bag area

Usage:
    python compare_layouts.py
    python compare_layouts.py --save layout_comparison.gif
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import replace
from math import cos, pi, sin

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from comlab_v3_sim import ComLabV3Simulation, default_scenarios, run_scenarios, summarize_results
from run_2d_simulation import ROLE_COLORS, draw_room


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


def print_comparison_table(scenario_name: str, seed: int, replications: int) -> None:
    base = next(config for config in default_scenarios(seed=seed) if config.name == scenario_name)
    configs = [
        replace(base, name=f"{scenario_name}_current", layout="current"),
        replace(
            base,
            name=f"{scenario_name}_modified",
            layout="modified",
            assigned_exits=True,
            custodians_manage_doors=True,
        ),
    ]
    rows = summarize_results(run_scenarios(configs, replications=replications))

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["layout"])].append(row)

    metrics = [
        "student_clearance_time_s",
        "evacuation_time_s",
        "trips",
        "door_collisions",
        "max_cell_density_visits",
    ]
    print("\nLayout comparison averages")
    print("-" * 78)
    print(f"{'metric':30} {'current':>12} {'modified':>12} {'change':>14}")
    print("-" * 78)
    for metric in metrics:
        current = float(np.mean([float(row[metric]) for row in grouped["current"]]))
        modified = float(np.mean([float(row[metric]) for row in grouped["modified"]]))
        change = current - modified
        print(f"{metric:30} {current:12.2f} {modified:12.2f} {change:14.2f}")
    print("-" * 78)


def make_agent_artists(ax, sim: ComLabV3Simulation):
    artists = {}
    for agent in sim.agents:
        marker = "o"
        if agent.role == "instructor":
            marker = "P"
        elif agent.role == "assistant":
            marker = "^"
        elif agent.role == "custodian":
            marker = "s"
        point = ax.scatter(
            [],
            [],
            s=70,
            c=ROLE_COLORS[agent.role],
            marker=marker,
            edgecolor="white",
            linewidth=0.8,
            zorder=4,
        )
        label = ax.text(
            0,
            0,
            agent.agent_id,
            ha="center",
            va="center",
            fontsize=5,
            color="white",
            weight="bold",
            zorder=5,
        )
        artists[agent.agent_id] = (point, label)
    return artists


def animate_comparison(scenario_name: str, seed: int, save_path: str | None) -> None:
    base = next(config for config in default_scenarios(seed=seed) if config.name == scenario_name)
    current_sim = ComLabV3Simulation(replace(base, layout="current"))
    modified_sim = ComLabV3Simulation(
        replace(base, layout="modified", assigned_exits=True, custodians_manage_doors=True)
    )
    current_result = current_sim.run()
    modified_result = modified_sim.run()

    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    draw_room(axes[0], current_sim)
    draw_room(axes[1], modified_sim)
    axes[0].set_title("Current Layout")
    axes[1].set_title("Modified Safer Layout")

    current_artists = make_agent_artists(axes[0], current_sim)
    modified_artists = make_agent_artists(axes[1], modified_sim)
    current_label = axes[0].text(0, -0.9, "", fontsize=10, weight="bold")
    modified_label = axes[1].text(0, -0.9, "", fontsize=10, weight="bold")

    max_frames = max(len(current_result.agent_frames), len(modified_result.agent_frames))

    def update_side(frame_index: int, result, artists, label):
        frame_agents = result.agent_frames[frame_index] if frame_index < len(result.agent_frames) else []
        visible = {str(item["agent_id"]): item for item in frame_agents}
        positions = spread_positions(frame_agents)
        drawn = []
        for agent_id, (point, text) in artists.items():
            if agent_id in visible:
                x, y = positions[agent_id]
                point.set_offsets(np.array([[x, y]]))
                text.set_position((x, y))
                text.set_alpha(1.0)
            else:
                point.set_offsets(np.empty((0, 2)))
                text.set_position((-10, -10))
                text.set_alpha(0.0)
            drawn.extend([point, text])
        label.set_text(f"Time: {frame_index}s | Active agents: {len(frame_agents)}")
        drawn.append(label)
        return drawn

    def update(frame_index: int):
        drawn = []
        drawn.extend(update_side(frame_index, current_result, current_artists, current_label))
        drawn.extend(update_side(frame_index, modified_result, modified_artists, modified_label))
        return drawn

    ani = animation.FuncAnimation(fig, update, frames=max_frames, interval=120, repeat=False, blit=False)
    print("\nSingle-run summaries")
    print(current_result.summary())
    print(modified_result.summary())

    plt.tight_layout()
    if save_path:
        ani.save(save_path, writer="pillow", fps=8)
        print(f"Saved comparison animation to {save_path}")
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="panicked_electrical_fire")
    parser.add_argument("--seed", type=int, default=12)
    parser.add_argument("--replications", type=int, default=30)
    parser.add_argument("--save", default=None, help="Optional .gif output path")
    args = parser.parse_args()

    valid = {config.name for config in default_scenarios()}
    if args.scenario not in valid:
        raise SystemExit(f"Unknown scenario '{args.scenario}'. Valid options: {', '.join(sorted(valid))}")

    print_comparison_table(args.scenario, args.seed, args.replications)
    animate_comparison(args.scenario, args.seed, args.save)


if __name__ == "__main__":
    main()
