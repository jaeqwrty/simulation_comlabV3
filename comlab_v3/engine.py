"""Core Python agent-based simulation engine for ComLab V3.

This module contains no UI code. The web server and any future desktop,
notebook, or test harness should import from here.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math


CELL = 34
LAB_COLS = 9
HALL_COLS = 4
ROWS = 12
COLS = LAB_COLS + HALL_COLS

FRONT_EXIT = (8, 2)
BACK_EXIT = (8, 10)
FRONT_STAIRS = (12, 1)
EMERGENCY_STAIRS = (12, 10)
CURRENT_LOCKER = (7, 9)
MODIFIED_LOCKER = (0, 0)
DATA_RACKS = {(8, 4), (8, 5), (8, 6)}
INSTRUCTOR_DESK = {(1, 0), (2, 0), (3, 0)}
WORKSTATIONS = [(x, 1 + row * 2) for row in range(6) for x in (0, 1, 2, 5, 6, 7)]
WORKSTATIONS_SET = set(WORKSTATIONS)


@dataclass
class Agent:
    agent_id: str
    kind: str
    behavior: str
    x: int
    y: int
    seed: int
    wait_until: int = 0
    phase: str = "waiting"
    target: tuple[int, int] = (0, 0)
    path: list[tuple[int, int]] = field(default_factory=list)
    speed_bank: float = 0.0
    exited: bool = False
    visited_locker: bool = False
    assigned_exit: str | None = None
    trip_until: int = 0


def seeded_random(seed: int) -> float:
    value = math.sin(seed * 9301 + 49297) * 233280
    return value - math.floor(value)


def cell_key(pos: tuple[int, int]) -> str:
    return f"{pos[0]},{pos[1]}"


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_lab_cell(pos: tuple[int, int]) -> bool:
    x, y = pos
    return 0 <= x < LAB_COLS and 0 <= y < ROWS


def is_hallway_cell(pos: tuple[int, int]) -> bool:
    x, y = pos
    return LAB_COLS <= x < COLS and 0 <= y < ROWS


def is_exit_cell(pos: tuple[int, int]) -> bool:
    return pos in {FRONT_EXIT, BACK_EXIT}


def locker_for(mode: str) -> tuple[int, int]:
    return MODIFIED_LOCKER if mode == "modified" else CURRENT_LOCKER


def fire_origin_for(origin: str) -> tuple[int, int]:
    return (2, 0) if origin == "desk" else (8, 5)


def is_obstacle(pos: tuple[int, int], blocked_cells: set[tuple[int, int]]) -> bool:
    x, y = pos
    if not (0 <= x < COLS and 0 <= y < ROWS):
        return True
    if x >= LAB_COLS or pos in {FRONT_EXIT, BACK_EXIT}:
        return False
    return (pos in blocked_cells) and (pos not in WORKSTATIONS_SET)


def neighbors(pos: tuple[int, int], blocked_cells: set[tuple[int, int]]) -> list[tuple[int, int]]:
    x, y = pos
    candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return [item for item in candidates if not is_obstacle(item, blocked_cells)]


def find_path(
    start: tuple[int, int],
    target: tuple[int, int],
    blocked_cells: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    queue = deque([start])
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == target:
            break
        options = sorted(neighbors(current, blocked_cells), key=lambda pos: manhattan(pos, target))
        for next_pos in options:
            if next_pos not in came_from:
                came_from[next_pos] = current
                queue.append(next_pos)

    if target not in came_from:
        return []

    path = []
    current = target
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path[1:]


class Simulation:
    """Stateful ABM simulation for one layout/scenario run."""

    def __init__(self, mode: str = "current", panic: bool = True, fire_origin: str = "data"):
        self.mode = mode
        self.panic = panic
        self.fire_origin_name = fire_origin
        self.fire_origin = fire_origin_for(fire_origin)
        
        # Precompute static blocked cells set for speed
        self.blocked_cells = set(INSTRUCTOR_DESK) | set(DATA_RACKS) | {locker_for(mode)} | {self.fire_origin}
        
        self.time = 0
        self.trips = 0
        self.door_collisions = 0
        self.door_cooldown = {"front": 0, "back": 0}
        self.heatmap: dict[str, int] = {}
        self.rate = [(0, 0)]
        self.events: list[tuple[int, str, str]] = []
        self.completed = False
        self.path_cache: dict[tuple[tuple[int, int], tuple[int, int]], list[tuple[int, int]]] = {}
        self.agents = self.make_agents()

    def make_agents(self) -> list[Agent]:
        agents: list[Agent] = []
        if self.mode == "modified":
            locker_rate = 0.16 if self.panic else 0.08
        else:
            locker_rate = 0.50 if self.panic else 0.34

        for index, seat in enumerate(WORKSTATIONS):
            roll = seeded_random(index + 10)
            behavior = "immediate" if roll < 0.25 else "task" if roll < 0.55 else "peer" if roll < 0.78 else "locker"
            if seeded_random(index + 99) < locker_rate:
                behavior = "locker"

            delay = 0
            if behavior == "task":
                delay = 2 + int(seeded_random(index + 21) * 3)
            elif behavior == "peer":
                delay = 1 + int(seeded_random(index + 22) * 3)

            agents.append(
                Agent(
                    agent_id=f"S{index + 1:02d}",
                    kind="student",
                    behavior=behavior,
                    x=seat[0],
                    y=seat[1],
                    seed=index + 1,
                    wait_until=delay,
                    target=seat,
                    assigned_exit=("front" if seat[1] <= 3 else "back") if self.mode == "modified" else None,
                )
            )

        agents.extend(
            [
                Agent("I01", "instructor", "instructor", 4, 0, 101, target=(3, 0), phase="to_extinguisher"),
                Agent("PA1", "assistant", "assistant", 4, 1, 102, wait_until=62 if self.mode == "modified" else 82, target=(4, 1), phase="guiding", assigned_exit="front"),
                Agent("PA2", "assistant", "assistant", 4, 10, 103, wait_until=62 if self.mode == "modified" else 82, target=(4, 10), phase="guiding", assigned_exit="back"),
                Agent("LC1", "custodian", "custodian", 7, 2, 104, wait_until=78 if self.mode == "modified" else 110, target=(7, 2), phase="holding_door", assigned_exit="front"),
                Agent("LC2", "custodian", "custodian", 7, 9, 105, wait_until=78 if self.mode == "modified" else 110, target=(7, 9), phase="holding_door", assigned_exit="back"),
            ]
        )
        return agents

    def add_event(self, event_type: str, message: str):
        self.events.insert(0, (self.time, event_type, message))
        self.events = self.events[:40]

    def density_map(self) -> dict[tuple[int, int], int]:
        density: dict[tuple[int, int], int] = {}
        for agent in self.agents:
            if not agent.exited:
                pos = (agent.x, agent.y)
                density[pos] = density.get(pos, 0) + 1
        return density

    def choose_exit(self, agent: Agent, density: dict[tuple[int, int], int]) -> tuple[int, int]:
        if agent.assigned_exit == "front":
            return FRONT_EXIT
        if agent.assigned_exit == "back":
            return BACK_EXIT
        if agent.behavior == "locker" and agent.visited_locker:
            return BACK_EXIT
        if self.panic and seeded_random(agent.seed + len(density)) < 0.18:
            return FRONT_EXIT if density.get(FRONT_EXIT, 0) <= density.get(BACK_EXIT, 0) else BACK_EXIT
        return FRONT_EXIT if manhattan((agent.x, agent.y), FRONT_EXIT) <= manhattan((agent.x, agent.y), BACK_EXIT) else BACK_EXIT

    def target_for(self, agent: Agent, density: dict[tuple[int, int], int]) -> tuple[int, int]:
        if agent.kind == "student":
            if self.time < agent.wait_until:
                return agent.target
            if agent.behavior == "locker" and not agent.visited_locker:
                return locker_for(self.mode)
            if agent.behavior == "peer" and agent.phase == "waiting":
                return (4, agent.y)
            return self.choose_exit(agent, density)
        if agent.kind == "instructor":
            if agent.phase == "to_extinguisher":
                return (3, 0) if self.fire_origin_name == "desk" else (7, 1)
            return self.choose_exit(agent, density)
        if agent.kind in {"assistant", "custodian"} and self.time >= agent.wait_until:
            return FRONT_EXIT if agent.assigned_exit == "front" else BACK_EXIT
        return agent.target

    def speed_for(self, agent: Agent, density: dict[tuple[int, int], int]) -> float:
        speed = 1.0 if agent.kind == "student" else 1.08
        crowded = density.get((agent.x, agent.y), 1)
        if is_lab_cell((agent.x, agent.y)) and agent.x not in {4, 7}:
            speed *= 0.58
        if manhattan((agent.x, agent.y), self.fire_origin) <= 3:
            speed *= 0.70
        if crowded >= 3:
            speed *= 0.55
        if self.panic:
            speed *= 0.92 if agent.kind == "student" else 0.82
        if self.mode == "modified":
            speed *= 1.12
        return speed

    def step(self):
        if self.completed:
            return

        self.time += 1
        density = self.density_map()
        for pos, count in density.items():
            density_key = f"{pos[0]},{pos[1]}"
            self.heatmap[density_key] = self.heatmap.get(density_key, 0) + count

        for agent in self.agents:
            if agent.exited:
                continue

            new_target = self.target_for(agent, density)
            if new_target != agent.target:
                agent.target = new_target
                agent.path = []  # Target changed, clear cached path to recalculate

            if self.time < agent.wait_until or self.time < agent.trip_until:
                continue

            current = (agent.x, agent.y)
            if current == agent.target:
                self.handle_arrival(agent)
                continue

            # Compute/Retrieve static path if empty
            if not agent.path:
                cache_key = (current, agent.target)
                if cache_key not in self.path_cache:
                    self.path_cache[cache_key] = find_path(current, agent.target, self.blocked_cells)
                agent.path = list(self.path_cache[cache_key])

            if not agent.path:
                continue

            agent.speed_bank += self.speed_for(agent, density)
            if self.panic and agent.kind == "student" and seeded_random(self.time + agent.seed) < 0.025:
                continue
            if agent.speed_bank < 1:
                continue
            agent.speed_bank -= 1

            next_cell = agent.path[0]
            local_density = density.get(next_cell, 0)
            trip_chance = (0.045 if local_density >= 3 else 0.012) * (1.6 if self.panic else 1.0) * (0.45 if self.mode == "modified" else 1.0)
            if agent.kind == "student" and seeded_random(self.time * agent.seed + self.trips) < trip_chance:
                self.trips += 1
                agent.trip_until = self.time + 3
                agent.phase = "tripped"
                self.add_event("trip", f"{agent.agent_id} tripped in a congested zone")
                continue

            agent.x, agent.y = next_cell
            agent.path.pop(0)  # Move successful, consume node
            self.handle_arrival(agent)

        evacuated = sum(1 for agent in self.agents if agent.exited)
        self.rate.append((self.time, evacuated))
        if evacuated == len(self.agents) or self.time >= 240:
            self.completed = True

    def handle_arrival(self, agent: Agent):
        pos = (agent.x, agent.y)
        if agent.behavior == "locker" and not agent.visited_locker and pos == locker_for(self.mode):
            agent.visited_locker = True
            agent.wait_until = self.time + (1 if self.mode == "modified" else 4)
            agent.phase = "retrieving_locker"
            self.add_event("locker", f"{agent.agent_id} retrieved belongings")
            return
        if agent.behavior == "peer" and agent.phase == "waiting" and pos == (4, agent.y):
            agent.wait_until = self.time + 2
            agent.phase = "peer_wait"
            return
        if agent.kind == "instructor" and agent.phase == "to_extinguisher":
            agent.phase = "evacuating"
            agent.wait_until = self.time + 2
            self.add_event("extinguisher", "Instructor retrieved extinguisher")
            return
        if pos in {FRONT_EXIT, BACK_EXIT}:
            self.try_exit(agent, "front" if pos == FRONT_EXIT else "back")

    def try_exit(self, agent: Agent, door: str):
        if self.time < self.door_cooldown[door]:
            return

        pressure = (0.12 if self.mode == "modified" else 0.28) + (0.14 if self.panic else 0.0) + (0.06 if door == "front" else 0.02)
        if seeded_random(self.time + agent.seed + self.door_collisions) < pressure:
            self.door_collisions += 1
            self.door_cooldown[door] = self.time + 2
            self.add_event("door", f"{door.title()} door collision from hallway backpressure")
            return
        agent.exited = True

    def summary(self) -> dict[str, int]:
        return {
            "time": self.time,
            "evacuated": sum(1 for agent in self.agents if agent.exited),
            "trips": self.trips,
            "door_collisions": self.door_collisions,
            "max_heat": max(self.heatmap.values(), default=0),
        }
