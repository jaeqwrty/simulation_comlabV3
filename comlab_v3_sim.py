"""Agent-based evacuation simulation for UMTC ComLab V3.

The implementation is intentionally compact and Colab-friendly. It uses a
cell-based room model with stochastic agent behavior, door queues, hallway
backpressure, and role-specific behavior for students, instructor, presiding
assistants, and lab custodians.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from heapq import heappop, heappush
from math import inf
import random
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


Position = Tuple[int, int]


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    layout: str = "current"
    panic: bool = False
    hazard: str = "none"
    locker_enabled: bool = True
    assigned_exits: bool = False
    custodians_manage_doors: bool = True
    remove_front_row: bool = False
    hallway_backpressure: float = 0.20
    v1_flow_intensity: float = 0.45
    v2_flow_intensity: float = 0.25
    random_seed: int = 7
    max_time: int = 900


@dataclass
class Agent:
    agent_id: str
    role: str
    behavior: str
    pos: Position
    base_speed: float
    reaction_delay: int
    target: Position
    assigned_door: Optional[str] = None
    phase: str = "waiting"
    wait_until: int = 0
    exited_at: Optional[int] = None
    trip_until: int = 0
    retrieved_extinguisher_at: Optional[int] = None
    locker_visited: bool = False


@dataclass
class SimulationResult:
    scenario: str
    layout: str
    evacuation_time: int
    cleared_agents: int
    total_agents: int
    trips: int
    door_collisions: int
    instructor_extinguisher_time: Optional[int]
    assistant_exit_times: Dict[str, Optional[int]]
    custodian_exit_times: Dict[str, Optional[int]]
    density_heatmap: np.ndarray
    door_usage: Dict[str, int]
    event_log: List[Dict[str, object]] = field(default_factory=list)
    frames: List[Dict[str, Position]] = field(default_factory=list)
    agent_frames: List[List[Dict[str, object]]] = field(default_factory=list)

    def summary(self) -> Dict[str, object]:
        student_exit_times = [
            int(event["time"])
            for event in self.event_log
            if event.get("event") == "exit" and str(event.get("agent_id", "")).startswith("S")
        ]
        return {
            "scenario": self.scenario,
            "layout": self.layout,
            "evacuation_time_s": self.evacuation_time,
            "student_clearance_time_s": max(student_exit_times) if student_exit_times else None,
            "cleared_agents": self.cleared_agents,
            "total_agents": self.total_agents,
            "trips": self.trips,
            "door_collisions": self.door_collisions,
            "instructor_extinguisher_time_s": self.instructor_extinguisher_time,
            "front_door_usage": self.door_usage.get("front", 0),
            "back_door_usage": self.door_usage.get("back", 0),
            "max_cell_density_visits": int(self.density_heatmap.max()),
        }


class ComLabV3Simulation:
    """Discrete-time ABM for the revised ComLab V3 evacuation proposal."""

    width = 9
    height = 12
    aisle_x = 4
    front_door = (8, 2)
    back_door = (8, 10)
    front_extinguisher = (7, 1)
    data_com_extinguisher = (7, 8)
    rear_extinguisher = (7, 10)
    locker = (8, 9)
    data_com_cells = {(7, 4), (7, 5), (7, 6)}

    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.layout = config.layout.lower()
        self.locker_pos = (8, 9) if self.layout == "current" else (0, 10)
        self.rng = random.Random(config.random_seed)
        self.seat_positions = self._seat_positions()
        self.workstation_cells = set(self.seat_positions)
        self.walkable = self._make_walkable_grid()
        self.agents = self._make_agents()
        self.time = 0
        self.heatmap = np.zeros((self.height, self.width), dtype=int)
        self.trips = 0
        self.door_collisions = 0
        self.door_usage = {"front": 0, "back": 0}
        self.event_log: List[Dict[str, object]] = []
        self.frames: List[Dict[str, Position]] = []
        self.agent_frames: List[List[Dict[str, object]]] = []
        self.blocked_cells: Dict[Position, int] = {}
        self.door_next_available = {"front": 0.0, "back": 0.0}

    def _make_walkable_grid(self) -> set[Position]:
        walkable: set[Position] = set()
        for y in range(self.height):
            walkable.add((self.aisle_x, y))
            walkable.add((7, y))
        for y in range(1, 12):
            for x in range(self.width):
                walkable.add((x, y))
        walkable.add((3, 0))
        walkable.add((4, 0))
        walkable.update({self.front_door, self.back_door, self.front_extinguisher})
        if self.config.remove_front_row:
            for x in range(self.width):
                walkable.add((x, 1))
        return walkable

    def _seat_positions(self) -> List[Position]:
        seats: List[Position] = []
        for row in range(6):
            y = 1 + row * 2
            if self.layout == "modified":
                # Same room area and same number of workstations, but the
                # right-wall workstation column is moved beside the center
                # aisle to keep a continuous exit lane along x=7.
                seats.extend([(0, y), (1, y), (2, y), (3, y), (5, y), (6, y)])
            else:
                seats.extend([(0, y), (1, y), (2, y), (5, y), (6, y), (7, y)])
        return seats

    def _student_behavior(self) -> str:
        r = self.rng.random()
        if r < 0.20:
            return "immediate"
        if r < 0.70:
            return "task_bound"
        return "peer_bound"

    def _reaction_delay(self, behavior: str) -> int:
        if behavior == "immediate":
            return self.rng.randint(2, 4)
        if behavior == "task_bound":
            return self.rng.randint(10, 20)
        if behavior == "peer_bound":
            return self.rng.randint(5, 10)
        return self.rng.randint(1, 3)

    def _make_agents(self) -> List[Agent]:
        agents: List[Agent] = []
        seats = self.seat_positions

        locker_use_rate = 0.60
        if self.config.panic:
            locker_use_rate = 0.60 * 0.80
        if self.layout == "modified":
            # Safer layout assumption: bag storage is moved out of the rear
            # doorway approach and students are instructed to leave belongings,
            # so fewer agents perform a locker detour during evacuation.
            locker_use_rate *= 0.15

        for idx, pos in enumerate(seats, start=1):
            behavior = self._student_behavior()
            if self.config.locker_enabled and self.rng.random() < locker_use_rate:
                behavior = "locker_bound"
            assigned = None
            if self.layout == "modified":
                assigned = "front" if pos[1] <= 3 else "back"
            elif self.config.assigned_exits:
                assigned = "front" if pos[1] <= 5 else "back"
            speed = self.rng.uniform(0.95, 1.35)
            if self.config.panic:
                speed *= self.rng.uniform(0.80, 1.15)
            if self.layout == "modified":
                speed *= 1.25
            agents.append(
                Agent(
                    agent_id=f"S{idx:02d}",
                    role="student",
                    behavior=behavior,
                    pos=pos,
                    base_speed=speed,
                    reaction_delay=self._reaction_delay(behavior),
                    target=pos,
                    assigned_door=assigned,
                )
            )

        agents.append(
            Agent("I01", "instructor", "extinguisher_first", (3, 0), 1.05, 1, self.front_extinguisher)
        )
        agents.extend(
            [
                Agent("PA1", "assistant", "guide_then_exit", (4, 1), 1.15, 1, self.front_door, "front"),
                Agent("PA2", "assistant", "guide_then_exit", (4, 10), 1.15, 1, self.back_door, "back"),
            ]
        )
        agents.extend(
            [
                Agent("LC1", "custodian", "door_manager", (7, 2), 1.00, 0, self.front_door, "front"),
                Agent("LC2", "custodian", "door_manager", (7, 9), 1.00, 0, self.back_door, "back"),
            ]
        )
        return agents

    def run(self) -> SimulationResult:
        for t in range(self.config.max_time + 1):
            self.time = t
            self._clear_expired_blocks()
            active = [a for a in self.agents if a.exited_at is None]
            if not active:
                break
            for agent in active:
                self.heatmap[agent.pos[1], agent.pos[0]] += 1
            self.frames.append({agent.agent_id: agent.pos for agent in active})
            self.agent_frames.append(
                [
                    {
                        "agent_id": agent.agent_id,
                        "role": agent.role,
                        "behavior": agent.behavior,
                        "phase": agent.phase,
                        "x": agent.pos[0],
                        "y": agent.pos[1],
                    }
                    for agent in active
                ]
            )
            self._step_agents(active)

        cleared = sum(1 for a in self.agents if a.exited_at is not None)
        evac_time = max((a.exited_at or 0) for a in self.agents)
        instructor = next(a for a in self.agents if a.role == "instructor")
        return SimulationResult(
            scenario=self.config.name,
            layout=self.layout,
            evacuation_time=evac_time,
            cleared_agents=cleared,
            total_agents=len(self.agents),
            trips=self.trips,
            door_collisions=self.door_collisions,
            instructor_extinguisher_time=instructor.retrieved_extinguisher_at,
            assistant_exit_times={a.agent_id: a.exited_at for a in self.agents if a.role == "assistant"},
            custodian_exit_times={a.agent_id: a.exited_at for a in self.agents if a.role == "custodian"},
            density_heatmap=self.heatmap.copy(),
            door_usage=dict(self.door_usage),
            event_log=list(self.event_log),
            frames=list(self.frames),
            agent_frames=list(self.agent_frames),
        )

    def _step_agents(self, active: List[Agent]) -> None:
        priority = {"custodian": 0, "assistant": 1, "instructor": 2, "student": 3}
        for agent in sorted(active, key=lambda a: (priority[a.role], a.reaction_delay, a.agent_id)):
            if agent.exited_at is not None:
                continue
            self._update_goal(agent)
            if self.time < agent.reaction_delay or self.time < agent.wait_until or self.time < agent.trip_until:
                continue
            if agent.pos in (self.front_door, self.back_door) and agent.phase in {"evacuating", "supervising_exit"}:
                self._try_exit(agent)
                continue
            if not self._can_move_this_second(agent):
                continue
            next_pos = self._next_step(agent.pos, agent.target)
            if next_pos is None or next_pos == agent.pos:
                self._handle_arrival(agent)
                continue
            if next_pos in self.blocked_cells:
                continue
            if self._maybe_trip(agent, next_pos):
                continue
            agent.pos = next_pos
            self._handle_arrival(agent)

    def _update_goal(self, agent: Agent) -> None:
        if agent.role == "student":
            if agent.phase == "waiting" and self.time >= agent.reaction_delay:
                if agent.behavior == "peer_bound":
                    agent.phase = "peer_wait"
                    agent.wait_until = self.time + self.rng.randint(2, 5)
                    agent.target = (self.aisle_x, agent.pos[1])
                elif agent.behavior == "locker_bound" and not agent.locker_visited:
                    agent.phase = "to_locker"
                    agent.target = self.locker_pos
                else:
                    agent.phase = "evacuating"
                    agent.target = self._choose_door(agent)
            elif agent.phase == "peer_wait" and self.time >= agent.wait_until:
                agent.phase = "evacuating"
                agent.target = self._choose_door(agent)
        elif agent.role == "instructor":
            if agent.phase == "waiting":
                agent.phase = "to_extinguisher"
                agent.target = self.front_extinguisher
            elif agent.phase == "supervising_exit":
                agent.target = self._choose_door(agent)
        elif agent.role == "assistant":
            if agent.phase == "waiting":
                agent.phase = "guiding"
                agent.wait_until = self._assistant_release_time()
                agent.target = (self.aisle_x, agent.pos[1])
            elif agent.phase == "guiding" and (
                self.time >= agent.wait_until or self._student_exit_fraction() >= 0.75
            ):
                agent.phase = "evacuating"
                agent.target = self._choose_door(agent)
        elif agent.role == "custodian":
            if agent.phase == "waiting":
                agent.phase = "holding_door"
                agent.wait_until = self._custodian_release_time()
            elif agent.phase == "holding_door" and (
                self.time >= agent.wait_until or self._student_exit_fraction() >= 0.90
            ):
                agent.phase = "evacuating"
                agent.target = self._choose_door(agent)

    def _handle_arrival(self, agent: Agent) -> None:
        if agent.pos != agent.target:
            return
        if agent.phase == "to_locker":
            agent.locker_visited = True
            agent.wait_until = self.time + self.rng.randint(3, 6)
            agent.phase = "evacuating"
            agent.target = self._choose_door(agent)
            self._log("locker_retrieval", agent)
        elif agent.phase == "to_extinguisher":
            agent.retrieved_extinguisher_at = self.time
            agent.wait_until = self.time + 3
            agent.phase = "supervising_exit"
            self._log("extinguisher_retrieval", agent)

    def _try_exit(self, agent: Agent) -> None:
        door = "front" if agent.pos == self.front_door else "back"
        if self.time < self.door_next_available[door]:
            return
        service_time = 1.0 / max(self._door_flow_rate(door), 0.05)
        self.door_next_available[door] = self.time + service_time
        agent.exited_at = self.time
        self.door_usage[door] += 1
        self._log("exit", agent, door=door)

    def _door_flow_rate(self, door: str) -> float:
        base = 1.5
        pressure = self.config.hallway_backpressure
        if door == "front":
            pressure += self.config.v1_flow_intensity * 0.25
        else:
            pressure += self.config.v2_flow_intensity * 0.18
        if self.config.panic:
            pressure += 0.15
        if self.layout == "modified":
            pressure *= 0.45
        if self.config.custodians_manage_doors and self._door_has_custodian(door):
            pressure *= 0.65
        restricted = self.rng.random() < pressure
        if restricted:
            self.door_collisions += 1
            self._log("doorway_swing_collision", None, door=door)
            return 0.5
        return max(0.3, base * (1.0 - min(pressure, 0.65)))

    def _door_has_custodian(self, door: str) -> bool:
        target = self.front_door if door == "front" else self.back_door
        return any(
            a.role == "custodian"
            and a.phase == "holding_door"
            and self._distance(a.pos, target) <= 1
            and a.exited_at is None
            for a in self.agents
        )

    def _choose_door(self, agent: Agent) -> Position:
        if agent.assigned_door == "front":
            return self.front_door
        if agent.assigned_door == "back":
            return self.back_door
        if agent.behavior == "locker_bound" and agent.locker_visited and self.layout == "current":
            return self.back_door
        front_dist = self._distance(agent.pos, self.front_door)
        back_dist = self._distance(agent.pos, self.back_door)
        if self.config.panic and self.rng.random() < 0.20:
            return self.front_door if self._nearby_agents(self.front_door) <= self._nearby_agents(self.back_door) else self.back_door
        return self.front_door if front_dist <= back_dist else self.back_door

    def _can_move_this_second(self, agent: Agent) -> bool:
        speed = agent.base_speed
        if agent.pos[0] not in self._fast_columns():
            speed *= 0.42
        if self.config.hazard == "electrical_fire" and self._distance_to_any(agent.pos, self.data_com_cells) <= 3:
            speed *= 0.70
        if agent.role == "instructor" and self.config.panic and agent.phase == "to_extinguisher":
            density = self._nearby_agents(agent.pos, radius=1)
            if density >= 3:
                return False
            speed *= 0.40
        if agent.role in {"assistant", "custodian"}:
            speed *= 1.10
        return self.rng.random() < min(1.0, speed)

    def _maybe_trip(self, agent: Agent, next_pos: Position) -> bool:
        if agent.role != "student":
            return False
        tight_row = next_pos[0] in self._tight_columns()
        if not tight_row:
            return False
        trip_rate = 0.05 * (1.35 if self.config.panic else 1.0)
        if self.layout == "modified":
            trip_rate *= 0.35
        if self.rng.random() < trip_rate:
            duration = self.rng.randint(3, 6)
            agent.trip_until = self.time + duration
            self.blocked_cells[agent.pos] = agent.trip_until
            self.trips += 1
            self._log("trip_or_fall", agent, duration=duration)
            return True
        return False

    def _next_step(self, start: Position, goal: Position) -> Optional[Position]:
        if start == goal:
            return start
        blocked = {p for p, until in self.blocked_cells.items() if until > self.time}
        queue: List[Tuple[int, Position]] = []
        came_from: Dict[Position, Optional[Position]] = {start: None}
        heappush(queue, (0, start))
        while queue:
            _, current = heappop(queue)
            if current == goal:
                break
            for nxt in self._neighbors(current):
                if nxt in came_from or nxt in blocked:
                    continue
                came_from[nxt] = current
                priority = self._distance(nxt, goal)
                heappush(queue, (priority, nxt))
        if goal not in came_from:
            return None
        current = goal
        while came_from[current] != start:
            current = came_from[current]  # type: ignore[index]
            if current is None:
                return None
        return current

    def _neighbors(self, pos: Position) -> Iterable[Position]:
        x, y = pos
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt in self.walkable:
                yield nxt

    def _fast_columns(self) -> set[int]:
        return {self.aisle_x, 7}

    def _tight_columns(self) -> set[int]:
        if self.layout == "modified":
            return {0, 1, 2, 3, 5, 6}
        return {0, 1, 2, 5, 6, 7}

    def _clear_expired_blocks(self) -> None:
        expired = [pos for pos, until in self.blocked_cells.items() if until <= self.time]
        for pos in expired:
            self.blocked_cells.pop(pos, None)

    def _assistant_release_time(self) -> int:
        if self._student_exit_fraction() >= 0.75:
            return self.time
        guide_duration = 70 if self.layout == "modified" else 90
        return min(self.config.max_time, self.time + guide_duration)

    def _custodian_release_time(self) -> int:
        if not self.config.custodians_manage_doors:
            return self.time
        if self._student_exit_fraction() >= 0.90:
            return self.time
        hold_duration = 95 if self.layout == "modified" else 120
        return min(self.config.max_time, self.time + hold_duration)

    def _student_exit_fraction(self) -> float:
        students = [a for a in self.agents if a.role == "student"]
        if not students:
            return 1.0
        exited = sum(1 for a in students if a.exited_at is not None)
        return exited / len(students)

    def _nearby_agents(self, pos: Position, radius: int = 2) -> int:
        return sum(
            1
            for a in self.agents
            if a.exited_at is None and self._distance(a.pos, pos) <= radius and a.pos != pos
        )

    @staticmethod
    def _distance(a: Position, b: Position) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @classmethod
    def _distance_to_any(cls, pos: Position, cells: Iterable[Position]) -> int:
        return min(cls._distance(pos, cell) for cell in cells)

    def _log(self, event: str, agent: Optional[Agent], **details: object) -> None:
        entry: Dict[str, object] = {"time": self.time, "event": event}
        if agent is not None:
            entry.update({"agent_id": agent.agent_id, "role": agent.role, "pos": agent.pos})
        entry.update(details)
        self.event_log.append(entry)


def default_scenarios(seed: int = 7) -> List[ScenarioConfig]:
    return [
        ScenarioConfig("orderly_fire_drill", panic=False, hazard="none", random_seed=seed),
        ScenarioConfig(
            "panicked_electrical_fire",
            panic=True,
            hazard="electrical_fire",
            hallway_backpressure=0.30,
            v1_flow_intensity=0.70,
            v2_flow_intensity=0.45,
            random_seed=seed,
        ),
        ScenarioConfig(
            "no_locker_detour",
            panic=True,
            hazard="electrical_fire",
            locker_enabled=False,
            hallway_backpressure=0.30,
            v1_flow_intensity=0.70,
            v2_flow_intensity=0.45,
            random_seed=seed,
        ),
        ScenarioConfig(
            "assigned_exits",
            panic=True,
            hazard="electrical_fire",
            assigned_exits=True,
            hallway_backpressure=0.30,
            v1_flow_intensity=0.70,
            v2_flow_intensity=0.45,
            random_seed=seed,
        ),
        ScenarioConfig(
            "custodians_hold_doors",
            panic=True,
            hazard="electrical_fire",
            custodians_manage_doors=True,
            hallway_backpressure=0.22,
            v1_flow_intensity=0.50,
            v2_flow_intensity=0.30,
            random_seed=seed,
        ),
    ]


def run_scenarios(configs: Iterable[ScenarioConfig], replications: int = 10) -> List[SimulationResult]:
    results: List[SimulationResult] = []
    for config in configs:
        for rep in range(replications):
            sim = ComLabV3Simulation(replace(config, random_seed=config.random_seed + rep))
            results.append(sim.run())
    return results


def summarize_results(results: Iterable[SimulationResult]) -> List[Dict[str, object]]:
    return [result.summary() for result in results]


if __name__ == "__main__":
    results = run_scenarios(default_scenarios(), replications=3)
    for row in summarize_results(results):
        print(row)
