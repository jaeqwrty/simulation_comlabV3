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

FRONT_EXIT = (8, 0)
BACK_EXIT = (8, 11)
FRONT_STAIRS = (12, 1)
EMERGENCY_STAIRS = (12, 11)
CURRENT_LOCKER = (7, 11)
MODIFIED_LOCKER = (7, 10)
DATA_RACKS = {(7, y) for y in range(2, 7)}
STUDENT_ASSISTANT_DESK = {(7, y) for y in range(7, 10)}
EXTRA_PCS = {(x, 11) for x in range(4)}
SHELVES = {(7, 11)}
INSTRUCTOR_DESK = {(6, 0)}
WORKSTATION_ROWS = (1, 2, 4, 5, 7, 8)
WORKSTATIONS = [(x, y) for y in WORKSTATION_ROWS for x in (0, 1, 2, 4, 5, 6)]
WORKSTATIONS_SET = set(WORKSTATIONS)
BACK_WORKSTATION_ROWS = {7, 8}

# Solid wall between lab and hallway — only exit doors are passable
HALLWAY_WALL = {(8, y) for y in range(ROWS)} - {FRONT_EXIT, BACK_EXIT}

# Right-side service bay from the sketch: data rack above, student assistant below.
# Column 7 has no workstations; right group is at x=4,5,6; aisle is x=3.
PARTITION_WALL = DATA_RACKS | STUDENT_ASSISTANT_DESK
SERVICE_BAY_PASSAGE = (7, 10)
SERVICE_BAY_STAFF = DATA_RACKS | STUDENT_ASSISTANT_DESK | {SERVICE_BAY_PASSAGE}
ASSISTANT_AID_POSTS = {"front": (3, 4), "back": (3, 8)}

# Fire extinguisher positions — beside professor desk, student assistant bay, and shelves
EXTINGUISHER_PROFESSOR = (7, 0)
EXTINGUISHER_ASSISTANT = (6, 9)
EXTINGUISHER_SHELVES = (6, 11)
FIRE_EXTINGUISHERS = (EXTINGUISHER_PROFESSOR, EXTINGUISHER_ASSISTANT, EXTINGUISHER_SHELVES)
EXTINGUISHER_EXIT = EXTINGUISHER_PROFESSOR
EXTINGUISHER_ENTRANCE = None



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
    reached_corridor: bool = False
    stamped_until: int = 0   # pinned by stampede
    packed_up: bool = False  # finished packing belongings before standing up
    bay_passage_cleared: bool = False  # staff used the (7,10)->(6,10) passage gap



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


def fire_origin_for(origin: str, mode: str = "current") -> tuple[int, int]:
    if mode == "modified":
        if origin == "desk":
            return (6, 0)
        elif origin == "workstation":
            return (3, 5)
        else:  # "data"
            return (0, 4)
    else:
        if origin == "desk":
            return (6, 0)
        elif origin == "workstation":
            return (2, 5)
        else:  # "data"
            return (7, 4)


def should_route_via_center_aisle(agent: "Agent", target_cell: tuple[int, int], mode: str = "current") -> bool:
    if agent.kind not in ("student", "assistant"):
        return False
    if agent.behavior == "peer" and agent.phase == "waiting":
        return False
    if agent.reached_corridor:
        return False
    
    target_y = target_cell[1]
    if agent.y == target_y:
        return False
    if target_y == 0:
        if agent.y == 0:
            return False
    elif target_y in {10, 11}:
        if agent.y >= 10:
            return False
    return True



def is_service_bay_staff(agent_kind: str | None) -> bool:
    return agent_kind in {"custodian", "assistant"}


def is_staff_bay_cell(pos: tuple[int, int], mode: str = "current") -> bool:
    staff_bay = ({(0, y) for y in range(2, 10)} | {(0, 10)}) if mode == "modified" else SERVICE_BAY_STAFF
    return pos in staff_bay


def staff_bay_cleared(agent: Agent, mode: str = "current") -> bool:
    """True once staff have used the passage gap or left the service-bay stack."""
    if agent.kind not in {"custodian", "assistant"}:
        return True
    if agent.bay_passage_cleared:
        return True
    staff_bay = ({(0, y) for y in range(2, 10)} | {(0, 10)}) if mode == "modified" else SERVICE_BAY_STAFF
    return (agent.x, agent.y) not in staff_bay


def staff_bay_waypoint(agent: Agent, mode: str = "current") -> tuple[int, int] | None:
    """Next cell along the sketch path: data rack -> student assistant -> passage -> lab."""
    if agent.kind not in {"custodian", "assistant"} or staff_bay_cleared(agent, mode):
        return None

    x, y = agent.x, agent.y
    bay_col = 0 if mode == "modified" else 7
    passage = (0, 10) if mode == "modified" else SERVICE_BAY_PASSAGE

    if x != bay_col:
        return passage

    if y < 6:
        return (bay_col, y + 1)
    if y == 6:
        return (bay_col, 7)
    if y < 9:
        return (bay_col, y + 1)
    if y == 9:
        return passage
    if (x, y) == passage:
        return (1 if mode == "modified" else 6, passage[1])
    return passage


def make_service_bay_staff_edges(passage_y: int, bay_col: int, lab_col: int) -> set[frozenset[tuple[int, int]]]:
    """Helper to block partition edges outside the passage row."""
    edges: set[frozenset[tuple[int, int]]] = set()
    for y in range(2, 11):
        if y == passage_y:
            continue
        edges.add(frozenset({(bay_col, y), (lab_col, y)}))

    edges.add(frozenset({(bay_col, 0), (lab_col, 0)}))
    edges.add(frozenset({(bay_col, 1), (lab_col, 1)}))
    edges.add(frozenset({(bay_col, 11), (lab_col, 11)}))
    edges.add(frozenset({(bay_col, 1), (bay_col, 2)}))

    for y in range(6, 9):
        edges.add(frozenset({(lab_col, y), (lab_col, y + 1)}))

    edges.add(frozenset({(bay_col, 10), (bay_col, 11)}))
    return edges


def service_bay_staff_edges() -> set[frozenset[tuple[int, int]]]:
    """Backup edge blocks that mirror the sketch — no west exit except at the passage row."""
    return make_service_bay_staff_edges(10, 7, 6)


def is_edge_blocked(
    start: tuple[int, int],
    end: tuple[int, int],
    blocked_edges: set[frozenset[tuple[int, int]]] | None,
) -> bool:
    if not blocked_edges:
        return False
    return frozenset({start, end}) in blocked_edges


def is_obstacle(
    pos: tuple[int, int],
    blocked_cells: set[tuple[int, int]],
    agent_kind: str | None = None,
    staff_fire_passable: tuple[int, int] | None = None,
    workstations_set: set[tuple[int, int]] = WORKSTATIONS_SET,
    staff_bay_cells: set[tuple[int, int]] = SERVICE_BAY_STAFF,
) -> bool:
    x, y = pos
    if not (0 <= x < COLS and 0 <= y < ROWS):
        return True
    if x >= LAB_COLS or pos in {FRONT_EXIT, BACK_EXIT}:
        return False
    if is_service_bay_staff(agent_kind) and pos == staff_fire_passable:
        return False
    if is_service_bay_staff(agent_kind) and pos in staff_bay_cells:
        return False
    return (pos in blocked_cells) and (pos not in workstations_set)


def neighbors(
    pos: tuple[int, int],
    blocked_cells: set[tuple[int, int]],
    agent_kind: str | None = None,
    blocked_edges: set[frozenset[tuple[int, int]]] | None = None,
    staff_fire_passable: tuple[int, int] | None = None,
    workstations_set: set[tuple[int, int]] = WORKSTATIONS_SET,
    staff_bay_cells: set[tuple[int, int]] = SERVICE_BAY_STAFF,
    mode: str = "current",
) -> list[tuple[int, int]]:
    x, y = pos
    workstation_cols = {2, 3, 5, 6} if mode == "modified" else {0, 1, 2, 4, 5, 6}
    staff_col = 1 if mode == "modified" else 6

    if x in workstation_cols:
        candidates = [(x + 1, y), (x - 1, y)]
        if is_service_bay_staff(agent_kind) and x == staff_col and y in {10, 11}:
            candidates.extend([(x, y + 1), (x, y - 1)])
    else:
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return [
        item
        for item in candidates
        if not is_obstacle(item, blocked_cells, agent_kind, staff_fire_passable, workstations_set, staff_bay_cells)
        and not is_edge_blocked(pos, item, blocked_edges)
    ]


def find_path(
    start: tuple[int, int],
    target: tuple[int, int],
    blocked_cells: set[tuple[int, int]],
    agent_kind: str | None = None,
    blocked_edges: set[frozenset[tuple[int, int]]] | None = None,
    staff_fire_passable: tuple[int, int] | None = None,
    workstations_set: set[tuple[int, int]] = WORKSTATIONS_SET,
    staff_bay_cells: set[tuple[int, int]] = SERVICE_BAY_STAFF,
    mode: str = "current",
) -> list[tuple[int, int]]:
    queue = deque([start])
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == target:
            break
        options = sorted(
            neighbors(current, blocked_cells, agent_kind, blocked_edges, staff_fire_passable, workstations_set, staff_bay_cells, mode),
            key=lambda pos: manhattan(pos, target),
        )
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
        self.fire_origin = fire_origin_for(fire_origin, mode)
        
        # Configure layout properties dynamically based on mode
        if mode == "modified":
            self.workstation_rows = (1, 2, 3, 5, 6, 7, 8, 9, 10)
            self.workstations = [(x, y) for y in self.workstation_rows for x in (2, 3, 5, 6)]
            self.workstations_set = set(self.workstations)
            self.data_racks = {(0, y) for y in range(2, 7)}
            self.student_assistant_desk = {(0, y) for y in range(7, 10)}
            self.extra_pcs = {(2, 11), (3, 11), (5, 11)}
            self.shelves = {(7, 10)}
            self.instructor_desk = {(6, 0)}
            self.locker = (7, 10)
            self.partition_wall = self.data_racks | self.student_assistant_desk
            self.service_bay_passage = (0, 10)
            self.service_bay_staff = self.data_racks | self.student_assistant_desk | {self.service_bay_passage}
            self.assistant_aid_posts = {"front": (4, 4), "back": (4, 8)}
            self.extinguisher_professor = (1, 0)
            self.extinguisher_assistant = (1, 9)
            self.extinguisher_shelves = (6, 11)
            self.fire_extinguishers = (self.extinguisher_professor, self.extinguisher_assistant, self.extinguisher_shelves)
            self.extinguisher_exit = self.extinguisher_professor
            self.extinguisher_entrance = None
        else:
            self.workstation_rows = WORKSTATION_ROWS
            self.workstations = WORKSTATIONS
            self.workstations_set = WORKSTATIONS_SET
            self.data_racks = DATA_RACKS
            self.student_assistant_desk = STUDENT_ASSISTANT_DESK
            self.extra_pcs = EXTRA_PCS
            self.shelves = SHELVES
            self.instructor_desk = INSTRUCTOR_DESK
            self.locker = CURRENT_LOCKER
            self.partition_wall = PARTITION_WALL
            self.service_bay_passage = SERVICE_BAY_PASSAGE
            self.service_bay_staff = SERVICE_BAY_STAFF
            self.assistant_aid_posts = ASSISTANT_AID_POSTS
            self.extinguisher_professor = EXTINGUISHER_PROFESSOR
            self.extinguisher_assistant = EXTINGUISHER_ASSISTANT
            self.extinguisher_shelves = EXTINGUISHER_SHELVES
            self.fire_extinguishers = FIRE_EXTINGUISHERS
            self.extinguisher_exit = EXTINGUISHER_EXIT
            self.extinguisher_entrance = EXTINGUISHER_ENTRANCE

        # Precompute static blocked cells set for speed. Lockers are destination
        # cells, so they need to remain pathable for locker-bound agents.
        self.blocked_cells = (
            set(self.data_racks)
            | set(self.student_assistant_desk) | set(self.extra_pcs)
            | HALLWAY_WALL | self.partition_wall
            | {self.fire_origin}
        )
        
        self.time = 0
        self.trips = 0
        self.door_collisions = 0
        self.door_cooldown = {"front": 0, "back": 0}
        self.heatmap: dict[str, int] = {}
        self.rate = [(0, 0)]
        self.events: list[tuple[int, str, str]] = []
        self.completed = False
        self.path_cache: dict[tuple[tuple[int, int], tuple[int, int], str | None], list[tuple[int, int]]] = {}
        self.service_bay_staff_edges = make_service_bay_staff_edges(
            self.service_bay_passage[1],
            0 if self.mode == "modified" else 7,
            1 if self.mode == "modified" else 6
        )
        self.agents = self.make_agents()

    def path_edges_for(
        self,
        agent_kind: str | None,
        bay_passage_cleared: bool = False,
    ) -> set[frozenset[tuple[int, int]]] | None:
        if not is_service_bay_staff(agent_kind):
            return None
        edges = set(self.service_bay_staff_edges)
        if bay_passage_cleared:
            bay_col = 0 if self.mode == "modified" else 7
            lab_col = 1 if self.mode == "modified" else 6
            edges.add(frozenset({self.service_bay_passage, (lab_col, self.service_bay_passage[1])}))
            edges.discard(frozenset({(bay_col, 0), (lab_col, 0)}))
            edges.discard(frozenset({(bay_col, 11), (lab_col, 11)}))
        return edges

    def find_agent_path(
        self,
        start: tuple[int, int],
        target: tuple[int, int],
        agent_kind: str | None,
        agent: Agent | None = None,
    ) -> list[tuple[int, int]]:
        cleared = bool(agent and agent.bay_passage_cleared)
        fire_passable = self.fire_origin if is_service_bay_staff(agent_kind) else None
        return find_path(
            start,
            target,
            self.blocked_cells,
            agent_kind,
            self.path_edges_for(agent_kind, cleared),
            fire_passable,
            self.workstations_set,
            self.service_bay_staff,
            self.mode,
        )

    def make_agents(self) -> list[Agent]:
        agents: list[Agent] = []
        if self.mode == "modified":
            locker_rate = 0.16 if self.panic else 0.08
        else:
            locker_rate = 0.50 if self.panic else 0.34

        for index, seat in enumerate(self.workstations):
            roll = seeded_random(index + 10)
            behavior = "immediate" if roll < 0.25 else "task" if roll < 0.55 else "peer" if roll < 0.78 else "locker"
            if seeded_random(index + 99) < locker_rate:
                behavior = "locker"

            # ── Pack-up delay: every student spends time closing apps / grabbing
            #    a phone before they stand up.  "immediate" is fastest (2-4 steps),
            #    "task" and "peer" are slower (4-9 steps), "locker" is slowest (6-12).
            if behavior == "immediate":
                pack_delay = 2 + int(seeded_random(index + 11) * 3)   # 2-4
            elif behavior in ("task", "peer"):
                pack_delay = 4 + int(seeded_random(index + 21) * 6)   # 4-9
            else:  # locker
                pack_delay = 6 + int(seeded_random(index + 31) * 7)   # 6-12

            agents.append(
                Agent(
                    agent_id=f"S{index + 1:02d}",
                    kind="student",
                    behavior=behavior,
                    x=seat[0],
                    y=seat[1],
                    seed=index + 1,
                    wait_until=pack_delay,
                    target=seat,
                    assigned_exit=None,
                )
            )

        if self.mode == "modified":
            agents.extend(
                [
                    Agent("I01", "instructor", "instructor", 6, 0, 101, wait_until=1, target=(6, 0), phase="waiting"),
                    Agent("PA1", "assistant", "assistant", 0, 8, 102, wait_until=1, target=(0, 8), phase="waiting", assigned_exit="front"),
                    Agent("PA2", "assistant", "assistant", 0, 9, 103, wait_until=1, target=(0, 9), phase="waiting", assigned_exit="back"),
                    Agent("LC1", "custodian", "custodian", 0, 3, 104, wait_until=1, target=(0, 3), phase="waiting", assigned_exit="front"),
                    Agent("LC2", "custodian", "custodian", 0, 5, 105, wait_until=1, target=(0, 5), phase="waiting", assigned_exit="back"),
                ]
            )
        else:
            agents.extend(
                [
                    Agent("I01", "instructor", "instructor", 6, 0, 101, wait_until=1, target=(6, 0), phase="waiting"),
                    Agent("PA1", "assistant", "assistant", 7, 8, 102, wait_until=1, target=(7, 8), phase="waiting", assigned_exit="front"),
                    Agent("PA2", "assistant", "assistant", 7, 9, 103, wait_until=1, target=(7, 9), phase="waiting", assigned_exit="back"),
                    Agent("LC1", "custodian", "custodian", 7, 3, 104, wait_until=1, target=(7, 3), phase="waiting", assigned_exit="front"),
                    Agent("LC2", "custodian", "custodian", 7, 5, 105, wait_until=1, target=(7, 5), phase="waiting", assigned_exit="back"),
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
        if agent.behavior == "locker" and agent.visited_locker:
            preferred = FRONT_EXIT if self.mode == "modified" else BACK_EXIT
            if self.find_agent_path((agent.x, agent.y), preferred, agent.kind, agent):
                return preferred
            return BACK_EXIT if preferred == FRONT_EXIT else FRONT_EXIT

        if agent.assigned_exit == "front":
            preferred = FRONT_EXIT
        elif agent.assigned_exit == "back":
            preferred = BACK_EXIT
        else:
            if self.panic and seeded_random(agent.seed + len(density)) < 0.18:
                preferred = FRONT_EXIT if density.get(FRONT_EXIT, 0) <= density.get(BACK_EXIT, 0) else BACK_EXIT
            else:
                preferred = FRONT_EXIT if manhattan((agent.x, agent.y), FRONT_EXIT) <= manhattan((agent.x, agent.y), BACK_EXIT) else BACK_EXIT

        if self.find_agent_path((agent.x, agent.y), preferred, agent.kind, agent):
            return preferred
        other = BACK_EXIT if preferred == FRONT_EXIT else FRONT_EXIT
        if self.find_agent_path((agent.x, agent.y), other, agent.kind, agent):
            return other
        return preferred

    def target_for(self, agent: Agent, density: dict[tuple[int, int], int]) -> tuple[int, int]:
        if agent.kind == "student":
            if self.time < agent.wait_until:
                return agent.target
            if agent.behavior == "locker" and not agent.visited_locker:
                target_cell = locker_for(self.mode)
            elif agent.behavior == "peer" and agent.phase == "waiting":
                peer_col = 4 if self.mode == "modified" else 3
                return (peer_col, agent.y)
            else:
                target_cell = self.choose_exit(agent, density)
        elif agent.kind == "instructor":
            if agent.phase == "waiting" or self.time < agent.wait_until:
                return agent.target
            if agent.phase in {"to_extinguisher", "retrieving_extinguisher"}:
                return self.extinguisher_exit
            target_cell = self.choose_exit(agent, density)
        elif agent.kind in {"assistant", "custodian"}:
            if self.time < agent.wait_until:
                return agent.target
            bay_step = staff_bay_waypoint(agent, self.mode)
            if bay_step is not None:
                return bay_step

            if agent.kind == "assistant":
                students_left = any(
                    item.kind in {"student", "instructor"} and not item.exited
                    for item in self.agents
                )
                if students_left:
                    return self.assistant_aid_posts[agent.assigned_exit or "back"]

            preferred = FRONT_EXIT if agent.assigned_exit == "front" else BACK_EXIT
            if self.find_agent_path((agent.x, agent.y), preferred, agent.kind, agent):
                target_cell = preferred
            else:
                alternate = BACK_EXIT if preferred == FRONT_EXIT else FRONT_EXIT
                target_cell = (
                    alternate
                    if self.find_agent_path((agent.x, agent.y), alternate, agent.kind, agent)
                    else preferred
                )
        else:
            return agent.target

        if should_route_via_center_aisle(agent, target_cell, self.mode):
            aisle_col = 4 if self.mode == "modified" else 3
            if agent.x != aisle_col:
                target_row = 10 if agent.y == 11 else agent.y
                return (aisle_col, target_row)
            else:
                if target_cell[1] == 0:
                    return (aisle_col, 10) if (aisle_col, 0) == self.fire_origin else (aisle_col, 0)
                else:
                    return (aisle_col, 0) if (aisle_col, 10) == self.fire_origin else (aisle_col, 10)
        return target_cell

    def speed_for(self, agent: Agent, density: dict[tuple[int, int], int]) -> float:
        # Movement budget per step — agents may only ever consume 1.0 per step.
        speed = 0.62 if agent.kind == "student" else 1.10
        crowded = density.get((agent.x, agent.y), 1)

        aisle_col = 4 if self.mode == "modified" else 3
        non_squeeze_cols = {1, 4, 7} if self.mode == "modified" else {3, 7}

        # Row-workstation squeeze: narrow gap between rows slows movement
        if is_lab_cell((agent.x, agent.y)) and agent.x not in non_squeeze_cols:
            speed *= 0.45   # tight row gaps

        # Centre-aisle is the bottleneck corridor
        if agent.x == aisle_col:
            if crowded >= 2:
                speed *= 0.60  # single-file shuffling
            if crowded >= 4:
                speed *= 0.45  # near-crush

        # Heat/smoke zone near fire origin
        if manhattan((agent.x, agent.y), self.fire_origin) <= 3:
            speed *= 0.65

        # General crowd slowdown
        if crowded >= 3:
            speed *= 0.50
        if crowded >= 5:
            speed *= 0.38  # very congested — stampede risk zone

        # Panic does NOT necessarily speed people up — it causes hesitation
        if self.panic:
            speed *= 0.85 if agent.kind in ("student", "assistant") else 0.78

        # Modified layout has clearer pathways and better signage
        if self.mode == "modified":
            speed *= 1.80

        return speed

    def is_adjacent_step(self, start: tuple[int, int], end: tuple[int, int]) -> bool:
        return abs(start[0] - end[0]) + abs(start[1] - end[1]) == 1

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

            if agent.kind in ("student", "assistant") and (agent.y == 0 or agent.y >= 10):
                if agent.behavior != "locker" or agent.visited_locker:
                    agent.reached_corridor = True

            # Phase Recovery & Standing Up Actions
            if agent.kind in ("student", "assistant"):
                if agent.phase == "tripped" and self.time >= agent.trip_until:
                    agent.phase = "evacuating" if agent.kind == "student" else "aiding_students"
                    self.add_event("recover", f"{agent.agent_id} stood back up and resumed egress")
                elif agent.phase == "fainted" and self.time >= agent.trip_until:
                    agent.phase = "evacuating" if agent.kind == "student" else "aiding_students"
                    self.add_event("recover", f"{agent.agent_id} recovered from fainting and stood up")

            if agent.kind == "student":
                if agent.phase == "retrieving_locker" and self.time >= agent.wait_until:
                    agent.phase = "evacuating"
                    self.add_event("move", f"{agent.agent_id} finished locker retrieval and resumed egress")
                elif agent.phase == "peer_wait" and self.time >= agent.wait_until:
                    agent.phase = "evacuating"
                elif agent.phase == "waiting" and self.time >= agent.wait_until:
                    agent.phase = "evacuating"
                elif agent.phase == "hesitating":
                    agent.phase = "evacuating"
            elif agent.kind == "instructor":
                if agent.phase == "waiting" and self.time >= agent.wait_until:
                    agent.phase = "to_extinguisher"
                    self.add_event("move", "Professor alerted — moving to fire extinguisher")
                elif agent.phase == "retrieving_extinguisher" and self.time >= agent.wait_until:
                    agent.phase = "evacuating"
                    self.add_event("move", "Professor retrieved extinguisher and resumed egress")
            elif agent.kind in {"assistant", "custodian"}:
                if agent.phase == "waiting" and self.time >= agent.wait_until:
                    exit_label = "front" if agent.assigned_exit == "front" else "back"
                    if agent.kind == "custodian":
                        agent.phase = "holding_door"
                        self.add_event(
                            "move",
                            f"Custodian {agent.agent_id} moving through the passage to hold the {exit_label} exit",
                        )
                    else:
                        agent.phase = "aiding_students"
                        self.add_event(
                            "move",
                            f"Student assistant {agent.agent_id} moving through the passage to aid students near the {exit_label} aisle",
                        )

            new_target = self.target_for(agent, density)
            if new_target != agent.target:
                agent.target = new_target
                agent.path = []  # Target changed, clear cached path to recalculate

            if self.time < agent.wait_until or self.time < agent.trip_until:
                continue

            # Stampede pin: agent is knocked down by crowd surge
            if agent.kind in ("student", "assistant") and self.time < agent.stamped_until:
                continue

            # Assistant proximity checks for recovery help and smoke fainting prevention
            assistant_near_current = any(
                a.kind == "assistant"
                and a.agent_id != agent.agent_id
                and not a.exited
                and abs(a.x - agent.x) + abs(a.y - agent.y) <= 2
                for a in self.agents
            )

            # Fire smoke/heat proximity fainting check
            fire_dist = manhattan((agent.x, agent.y), self.fire_origin)
            if agent.kind in ("student", "assistant") and fire_dist <= 2:
                faint_smoke_chance = 0.07 if self.panic else 0.03
                if assistant_near_current:
                    faint_smoke_chance *= 0.5
                if seeded_random(self.time * agent.seed + 555) < faint_smoke_chance:
                    # Faint from smoke — longer recovery, agents nearby must step around
                    duration = 6 if self.mode == "modified" else 18
                    if assistant_near_current:
                        duration = max(4, duration // 2)
                    agent.trip_until = self.time + duration
                    agent.phase = "fainted"
                    self.add_event("trip", f"{agent.agent_id} fainted from smoke/heat proximity")
                    continue

            current = (agent.x, agent.y)
            if current == agent.target:
                self.handle_arrival(agent)
                continue

            # Compute/Retrieve static path if empty
            if not agent.path:
                cache_key = (current, agent.target, agent.kind, agent.bay_passage_cleared)
                if cache_key not in self.path_cache:
                    self.path_cache[cache_key] = self.find_agent_path(
                        current, agent.target, agent.kind, agent
                    )
                agent.path = list(self.path_cache[cache_key])

            if not agent.path:
                continue

            agent.speed_bank += self.speed_for(agent, density)
            # Hesitation: panic causes freeze moments (increased frequency)
            if self.panic and agent.kind in ("student", "assistant") and seeded_random(self.time + agent.seed) < 0.055:
                agent.phase = "hesitating"
                continue
            if agent.speed_bank < 1:
                continue

            next_cell = agent.path[0]
            if not self.is_adjacent_step(current, next_cell):
                agent.path = []
                continue
            if is_edge_blocked(
                current,
                next_cell,
                self.path_edges_for(agent.kind, agent.bay_passage_cleared),
            ):
                agent.path = []
                continue

            agent.speed_bank -= 1
            local_density = density.get(next_cell, 0)

            # ── Stampede check ─────────────────────────────────────────────────
            # In the centre aisle high crowd density can trigger a stampede
            # surge: agents at the back get knocked and pinned for several steps.
            aisle_col = 4 if self.mode == "modified" else 3
            if agent.kind in ("student", "assistant") and agent.x == aisle_col and local_density >= 5 and self.panic:
                stamp_roll = seeded_random(self.time * agent.seed + 991)
                if stamp_roll < 0.18:
                    pin_duration = 6 + int(seeded_random(self.time + agent.seed + 3) * 8)  # 6-13 steps
                    agent.stamped_until = self.time + pin_duration
                    agent.phase = "tripped"  # visually show as tripped/knocked down
                    self.add_event("trip", f"{agent.agent_id} knocked down in centre-aisle stampede")
                    continue

            # ── Trip / faint check ────────────────────────────────────────────
            base_trip = 0.065 if local_density >= 3 else 0.022
            trip_chance = base_trip * (1.8 if self.panic else 1.0) * (0.20 if self.mode == "modified" else 1.0)
            
            # Proximity to student assistants reduces tripping chance
            assistant_near_next = any(
                a.kind == "assistant"
                and a.agent_id != agent.agent_id
                and not a.exited
                and abs(a.x - next_cell[0]) + abs(a.y - next_cell[1]) <= 2
                for a in self.agents
            )
            if assistant_near_next:
                trip_chance *= 0.5

            if agent.kind in ("student", "assistant") and seeded_random(self.time * agent.seed + self.trips) < trip_chance:
                self.trips += 1
                faint_roll = seeded_random(self.time * agent.seed + self.trips + 77)
                is_faint = self.panic and faint_roll < 0.22   # higher faint chance
                
                if is_faint:
                    # Fainted: needs to be helped or self-recover — long delay
                    duration = 5 if self.mode == "modified" else 15
                    if assistant_near_next:
                        duration = max(3, duration // 2)
                    agent.trip_until = self.time + duration
                    agent.phase = "fainted"
                    self.add_event("trip", f"{agent.agent_id} fainted due to panic/smoke inhalation")
                else:
                    # Tripped: scrambles back up — moderate delay
                    duration = 3 if self.mode == "modified" else 7
                    if assistant_near_next:
                        duration = max(2, duration - 2)
                    agent.trip_until = self.time + duration
                    agent.phase = "tripped"
                    self.add_event("trip", f"{agent.agent_id} tripped in a congested zone")
                continue

            agent.x, agent.y = next_cell
            bay_passage_exit_cell = (1 if self.mode == "modified" else 6, self.service_bay_passage[1])
            if (
                agent.kind in {"custodian", "assistant"}
                and current == self.service_bay_passage
                and next_cell == bay_passage_exit_cell
            ):
                agent.bay_passage_cleared = True
                agent.path = []
            else:
                agent.path.pop(0)  # Move successful, consume node
            self.handle_arrival(agent)

        evacuated = sum(1 for agent in self.agents if agent.exited)
        self.rate.append((self.time, evacuated))
        if evacuated == len(self.agents) or self.time >= 400:  # extended max steps for realistic slow evacuation
            self.completed = True

    def handle_arrival(self, agent: Agent):
        pos = (agent.x, agent.y)
        if agent.behavior == "locker" and not agent.visited_locker and pos == locker_for(self.mode):
            agent.visited_locker = True
            # Locker retrieval: rummaging through a bag/locker takes significant time
            locker_delay = 3 if self.mode == "modified" else 10 + int(seeded_random(agent.seed + 77) * 6)  # 10-15 steps
            agent.wait_until = self.time + locker_delay
            agent.phase = "retrieving_locker"
            self.add_event("locker", f"{agent.agent_id} retrieved belongings from locker")
            return
        aisle_col = 4 if self.mode == "modified" else 3
        if agent.behavior == "peer" and agent.phase == "waiting" and pos == (aisle_col, agent.y):
            # Peer waits for a friend — realistic social delay
            peer_delay = 3 + int(seeded_random(agent.seed + 44) * 4)  # 3-6 steps
            agent.wait_until = self.time + peer_delay
            agent.phase = "peer_wait"
            return
        if agent.kind == "instructor" and agent.phase == "to_extinguisher" and pos == self.extinguisher_exit:
            agent.phase = "retrieving_extinguisher"
            agent.wait_until = self.time + 4   # realistic extinguisher grab time
            self.add_event("extinguisher", "Professor retrieved fire extinguisher beside the front exit")
            return
        if pos in {FRONT_EXIT, BACK_EXIT}:
            self.try_exit(agent, "front" if pos == FRONT_EXIT else "back")

    def try_exit(self, agent: Agent, door: str):
        if self.time < self.door_cooldown[door]:
            return

        if agent.kind in {"custodian", "assistant"}:
            # Staff members stay at their exit post to hold/guide and only exit at the end
            other_agents_left = any(a.kind not in {"custodian", "assistant"} and not a.exited for a in self.agents)
            if other_agents_left:
                return

        # Check if a custodian is at this exit door holding it
        door_cell = FRONT_EXIT if door == "front" else BACK_EXIT
        custodian_holding = any(
            a.kind == "custodian"
            and (a.x, a.y) == door_cell
            and not a.exited
            for a in self.agents
        )

        if custodian_holding:
            # Door held open — only one person can squeeze through per step
            pressure = 0.0
            self.door_cooldown[door] = self.time + 1  # one-at-a-time throughput
        else:
            # Unmanaged door: high collision chance; people push and create jams
            # Current layout has single-width corridor exits — very congested
            pressure = (0.10 if self.mode == "modified" else 0.40) + (0.18 if self.panic else 0.0) + (0.08 if door == "front" else 0.03)

        if seeded_random(self.time + agent.seed + self.door_collisions) < pressure:
            self.door_collisions += 1
            # Longer door jam: 3-5 steps of blocked exit
            jam_duration = 3 + int(seeded_random(self.time + self.door_collisions) * 3)
            self.door_cooldown[door] = self.time + jam_duration
            self.add_event("door", f"{door.title()} door jam — {jam_duration} step blockage")
            return
        agent.exited = True
        # After each exit, small throughput gap (shoulder-width squeeze)
        if not custodian_holding:
            self.door_cooldown[door] = self.time + 1

    def summary(self) -> dict[str, int]:
        return {
            "time": self.time,
            "evacuated": sum(1 for agent in self.agents if agent.exited),
            "trips": self.trips,
            "door_collisions": self.door_collisions,
            "max_heat": max(self.heatmap.values(), default=0),
        }
