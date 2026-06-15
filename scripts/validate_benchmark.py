from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from comlab_v3.engine import Simulation


FIRE_ORIGINS = ("data", "desk", "workstation", "tv", "assistant")
IMPROVEMENT_FIRE_ORIGINS = {"data", "desk"}

SCENARIOS = [
    (mode, panic, fire_origin)
    for mode in ("current", "modified")
    for panic in (True, False)
    for fire_origin in FIRE_ORIGINS
]


def run_scenario(mode: str, panic: bool, fire_origin: str):
    sim = Simulation(mode, panic, fire_origin)
    steps = 0
    while not sim.completed:
        sim.step()
        steps += 1
    summary = sim.summary()
    summary["steps"] = steps
    summary["inside"] = len(sim.agents) - summary["evacuated"]
    return summary


def validate():
    rows = []
    failures = []
    for mode, panic, fire_origin in SCENARIOS:
        summary = run_scenario(mode, panic, fire_origin)
        row = {
            "mode": mode,
            "panic": panic,
            "fire_origin": fire_origin,
            **summary,
        }
        rows.append(row)
        if row["inside"] != 0:
            failures.append(f"{mode}/{panic}/{fire_origin}: {row['inside']} agents still inside")
        if row["time"] >= 400:
            failures.append(f"{mode}/{panic}/{fire_origin}: reached 400-step max limit (no full evacuation)")

    current_by_condition = {
        (row["panic"], row["fire_origin"]): row
        for row in rows
        if row["mode"] == "current"
    }
    for row in rows:
        if row["mode"] != "modified":
            continue
        if row["fire_origin"] not in IMPROVEMENT_FIRE_ORIGINS:
            continue
        current = current_by_condition[(row["panic"], row["fire_origin"])]
        if row["time"] >= current["time"]:
            failures.append(
                f"modified/{row['panic']}/{row['fire_origin']}: "
                f"{row['time']}s was not faster than current {current['time']}s"
            )

    return rows, failures


def benchmark(iterations: int):
    elapsed_runs = []
    total_steps = 0
    for _ in range(iterations):
        start = perf_counter()
        for mode, panic, fire_origin in SCENARIOS:
            total_steps += run_scenario(mode, panic, fire_origin)["steps"]
        elapsed_runs.append(perf_counter() - start)

    elapsed_total = sum(elapsed_runs)
    scenario_count = iterations * len(SCENARIOS)
    return {
        "iterations": iterations,
        "scenarios": scenario_count,
        "total_seconds": elapsed_total,
        "mean_matrix_seconds": mean(elapsed_runs),
        "scenarios_per_second": scenario_count / elapsed_total,
        "steps_per_second": total_steps / elapsed_total,
    }


def print_validation(rows):
    print("Validation")
    print("mode      panic  fire         time  evacuated  avg_wait  avg_queue  throughput  util_pct  trips  doors  max_heat")
    for row in rows:
        print(
            f"{row['mode']:<9} {str(row['panic']):<5}  {row['fire_origin']:<11}  "
            f"{row['time']:>4}  {row['evacuated']:>9}  "
            f"{row['average_wait_time']:>8.2f}  {row['average_queue_length']:>9.2f}  "
            f"{row['throughput_per_minute']:>10.2f}  {row['exit_utilization_percent']:>8.2f}  "
            f"{row['trips']:>5}  {row['door_collisions']:>5}  {row['max_heat']:>8}"
        )


def print_benchmark(result):
    print()
    print("Benchmark")
    print(f"iterations:          {result['iterations']}")
    print(f"scenarios:           {result['scenarios']}")
    print(f"total_seconds:       {result['total_seconds']:.6f}")
    print(f"mean_matrix_seconds: {result['mean_matrix_seconds']:.6f}")
    print(f"scenarios_per_sec:   {result['scenarios_per_second']:.2f}")
    print(f"steps_per_sec:       {result['steps_per_second']:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Validate and benchmark the ComLab V3 simulation engine.")
    parser.add_argument("--iterations", type=int, default=1, help="Benchmark matrix iterations.")
    args = parser.parse_args()

    rows, failures = validate()
    print_validation(rows)
    if failures:
        print()
        print("Failures")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    result = benchmark(args.iterations)
    print_benchmark(result)


if __name__ == "__main__":
    main()
