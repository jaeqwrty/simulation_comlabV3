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
MODIFIED_LOCKER = (6, 0)
DATA_RACKS = {(7, y) for y in range(2, 7)}
STUDENT_ASSISTANT_DESK = {(7, y) for y in range(7, 10)}
EXTRA_PCS = {(x, 11) for x in range(4)}
SHELVES = {(7, 11)}
INSTRUCTOR_DESK = {(6, 0)}
TELEVISION = (4, 0)
MODIFIED_TELEVISION = (5, 0)
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

FIRE_LOCATION_LABELS = {
    "data": "Data / communication rack",
    "desk": "Instructor desk",
    "workstation": "Student workstation row",
    "tv": "Television",
    "locker": "Television",
    "shelves": "Television",
    "assistant": "Student assistant bay",
}



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
    panic_prone: bool = False
    mobility_factor: float = 1.0
    wait_time: int = 0
    exit_time: int | None = None
    health: float = 100.0
    is_casualty: bool = False



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


def storage_for(mode: str) -> tuple[int, int]:
    """Unified locker + bag-shelf cell for the active layout."""
    return MODIFIED_LOCKER if mode == "modified" else CURRENT_LOCKER


def locker_for(mode: str) -> tuple[int, int]:
    return storage_for(mode)


def fire_origin_for(origin: str, mode: str = "current") -> tuple[int, int]:
    if mode == "modified":
        if origin == "desk":
            return (6, 0)
        elif origin == "workstation":
            return (2, 5)
        elif origin in {"tv", "locker", "shelves"}:
            return MODIFIED_TELEVISION
        elif origin == "assistant":
            return (4, 11)
        else:  # "data"
            return (1, 11)
    else:
        if origin == "desk":
            return (6, 0)
        elif origin == "workstation":
            return (2, 5)
        elif origin in {"tv", "locker", "shelves"}:
            return TELEVISION
        elif origin == "assistant":
            return (7, 8)
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
    staff_bay = {(x, 11) for x in range(7)} if mode == "modified" else SERVICE_BAY_STAFF
    return pos in staff_bay


def staff_bay_cleared(agent: Agent, mode: str = "current") -> bool:
    """True once staff have used the passage gap or left the service-bay stack."""
    if agent.kind not in {"custodian", "assistant"}:
        return True
    if agent.bay_passage_cleared:
        return True
    staff_bay = {(x, 11) for x in range(7)} if mode == "modified" else SERVICE_BAY_STAFF
    return (agent.x, agent.y) not in staff_bay


def staff_bay_waypoint(agent: Agent, mode: str = "current") -> tuple[int, int] | None:
    """Next cell along the sketch path: data rack -> student assistant -> passage -> lab."""
    if agent.kind not in {"custodian", "assistant"} or staff_bay_cleared(agent, mode):
        return None

    x, y = agent.x, agent.y
    if mode == "modified":
        passage = (6, 11)
        if (x, y) == passage:
            return (6, 10)
        if y == 11:
            if x < passage[0]:
                return (x + 1, y)
            if x > passage[0]:
                return (x - 1, y)
        return passage

    bay_col = 7
    passage = SERVICE_BAY_PASSAGE

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


def rear_service_bay_staff_edges() -> set[frozenset[tuple[int, int]]]:
    """Block the rear service band except at the center passage."""
    edges: set[frozenset[tuple[int, int]]] = set()
    for x in range(7):
        if x == 6:
            continue
        edges.add(frozenset({(x, 10), (x, 11)}))
    return edges


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
    passable_workstations: set[tuple[int, int]] | None = None,
) -> bool:
    x, y = pos
    if not (0 <= x < COLS and 0 <= y < ROWS):
        return True
    if pos in {FRONT_EXIT, BACK_EXIT}:
        return pos in blocked_cells
    if x >= LAB_COLS:
        return pos in blocked_cells
    if is_service_bay_staff(agent_kind) and pos == staff_fire_passable:
        return False
    if is_service_bay_staff(agent_kind) and pos in staff_bay_cells:
        return False
    table_egress = passable_workstations or set()
    return pos in blocked_cells or (pos in workstations_set and pos not in table_egress)


def neighbors(
    pos: tuple[int, int],
    blocked_cells: set[tuple[int, int]],
    agent_kind: str | None = None,
    blocked_edges: set[frozenset[tuple[int, int]]] | None = None,
    staff_fire_passable: tuple[int, int] | None = None,
    workstations_set: set[tuple[int, int]] = WORKSTATIONS_SET,
    staff_bay_cells: set[tuple[int, int]] = SERVICE_BAY_STAFF,
    mode: str = "current",
    passable_workstations: set[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    x, y = pos
    workstation_cols = {0, 1, 2, 5, 6, 7} if mode == "modified" else {0, 1, 2, 4, 5, 6}
    vertical_lanes = {3, 4} if mode == "modified" else {3}
    staff_col = 6 if mode == "modified" else 6

    if pos in workstations_set:
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    elif x in workstation_cols and 1 <= y <= 8:
        candidates = [(x + 1, y), (x - 1, y)]
        if x in vertical_lanes or (is_service_bay_staff(agent_kind) and x == staff_col and y in {9, 10, 11}):
            candidates.extend([(x, y + 1), (x, y - 1)])
    else:
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return [
        item
        for item in candidates
        if not is_obstacle(item, blocked_cells, agent_kind, staff_fire_passable, workstations_set, staff_bay_cells, passable_workstations)
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
    passable_workstations: set[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    queue = deque([start])
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == target:
            break
        options = sorted(
            neighbors(current, blocked_cells, agent_kind, blocked_edges, staff_fire_passable, workstations_set, staff_bay_cells, mode, passable_workstations),
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
            self.workstation_rows = (1, 2, 4, 5, 7, 8)
            self.workstations = [
                (x, y)
                for y in self.workstation_rows
                for x in (0, 1, 2, 5, 6, 7)
            ]
            self.workstations_set = set(self.workstations)
            self.table_cells = {cell for cell in self.workstations_set if cell[0] != 4}
            self.data_racks = {(0, 11), (1, 11), (2, 11)}
            self.student_assistant_desk = {(3, 11), (4, 11), (5, 11)}
            self.extra_pcs = set()
            self.storage = storage_for(mode)
            self.locker = self.storage
            self.shelves = {self.storage}
            self.instructor_desk = {(0, 11)}
            self.partition_wall = self.data_racks | self.student_assistant_desk
            self.service_bay_passage = (6, 11)
            self.service_bay_staff = self.data_racks | self.student_assistant_desk | {self.service_bay_passage}
            self.assistant_aid_posts = {"front": FRONT_EXIT, "back": BACK_EXIT}
            self.extinguisher_professor = (7, 0)
            self.extinguisher_assistant = (2, 10)
            self.extinguisher_shelves = (6, 10)
            self.fire_extinguishers = (self.extinguisher_professor, self.extinguisher_assistant, self.extinguisher_shelves)
            self.extinguisher_exit = self.extinguisher_professor
            self.extinguisher_entrance = None
        else:
            self.workstation_rows = WORKSTATION_ROWS
            self.workstations = WORKSTATIONS
            self.workstations_set = WORKSTATIONS_SET
            self.table_cells = self.workstations_set
            self.data_racks = DATA_RACKS
            self.student_assistant_desk = STUDENT_ASSISTANT_DESK
            self.extra_pcs = EXTRA_PCS
            self.storage = storage_for(mode)
            self.locker = self.storage
            self.shelves = {self.storage}
            self.instructor_desk = INSTRUCTOR_DESK
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
        if self.fire_origin_name == "data":
            if self.mode == "modified":
                self.active_fire_cells = {(1, 11)}
                self.fire_intensity = {(1, 11): 50.0}
            else:
                self.active_fire_cells = {self.fire_origin}
                self.fire_intensity = {self.fire_origin: 50.0}
        else:
            self.active_fire_cells = {self.fire_origin}
            self.fire_intensity = {self.fire_origin: 50.0}
        self.time = 0
        self.trips = 0
        self.door_collisions = 0
        self.fire_damage = 0
        self.suppression_level = 0
        self.door_cooldown = {"front": 0, "back": 0}
        self.heatmap: dict[str, int] = {}
        self.queue_lengths: list[int] = []
        self.rate = [(0, 0)]
        self.events: list[tuple[int, str, str]] = []
        self.completed = False
        self.path_cache: dict[tuple[tuple[int, int], tuple[int, int], str | None], list[tuple[int, int]]] = {}
        self.service_bay_staff_edges = (
            rear_service_bay_staff_edges()
            if self.mode == "modified"
            else make_service_bay_staff_edges(self.service_bay_passage[1], 7, 6)
        )
        self.agents = self.make_agents()

    def fire_fuel_weight(self, pos: tuple[int, int]) -> float:
        if pos in self.data_racks:
            return 2.4
        if pos in self.workstations_set or pos in self.extra_pcs:
            return 2.0
        if pos in self.student_assistant_desk:
            return 1.8
        if pos in self.shelves or pos == self.locker:
            return 1.7
        if pos in self.instructor_desk:
            return 1.5
        if is_lab_cell(pos):
            return 1.0
        return 0.0

    def fire_neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = pos
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [
            item
            for item in candidates
            if is_lab_cell(item) and item not in {FRONT_EXIT, BACK_EXIT}
        ]

    def spread_fire(self, density: dict[tuple[int, int], int]):
        if not self.active_fire_cells:
            return

        spread_interval = 7
        if self.time % spread_interval != 0:
            return

        suppression = min(0.80, self.suppression_level * 0.25)
        max_cells = 16
        if len(self.active_fire_cells) >= max_cells:
            return

        new_cells: set[tuple[int, int]] = set()
        for source in sorted(self.active_fire_cells):
            for candidate in self.fire_neighbors(source):
                if candidate in self.active_fire_cells:
                    continue

                fuel = self.fire_fuel_weight(candidate)
                if fuel <= 0:
                    continue

                congestion = min(0.20, density.get(candidate, 0) * 0.04)
                heat = min(0.18, self.heatmap.get(cell_key(candidate), 0) / 360)
                wiring_bonus = 0.08 if candidate in self.workstations_set | self.data_racks | self.extra_pcs else 0.0
                base = 0.016
                chance = (base * fuel + congestion + heat + wiring_bonus) * (1 - suppression)
                if self.panic:
                    chance += 0.006

                roll_seed = self.time * 1009 + candidate[0] * 37 + candidate[1] * 101 + len(self.active_fire_cells)
                if seeded_random(roll_seed) < min(0.34, chance):
                    new_cells.add(candidate)

        if new_cells:
            room_left = max_cells - len(self.active_fire_cells)
            added = set(sorted(new_cells)[:room_left])
            self.active_fire_cells.update(added)
            self.add_event("extinguisher", f"Fire spread to {len(self.active_fire_cells)} lab cells")
            self.path_cache.clear()

    def distance_to_fire(self, pos: tuple[int, int]) -> int:
        return min((manhattan(pos, fire_cell) for fire_cell in self.active_fire_cells), default=99)

    def path_edges_for(
        self,
        agent_kind: str | None,
        bay_passage_cleared: bool = False,
    ) -> set[frozenset[tuple[int, int]]] | None:
        if not is_service_bay_staff(agent_kind):
            return None
        edges = set(self.service_bay_staff_edges)
        if bay_passage_cleared:
            if self.mode == "modified":
                edges.add(frozenset({self.service_bay_passage, (6, 10)}))
            else:
                bay_col = 7
                lab_col = 6
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
        blocked_cells = self.blocked_cells
        passable_workstations: set[tuple[int, int]] = set()
        if self.mode == "modified":
            passable_workstations.update(
                cell for cell in self.workstations_set if cell[0] == 4
            )
        if agent_kind == "student":
            blocked_cells = set(self.blocked_cells) | (self.active_fire_cells - {start, target})
            if self.mode == "modified" and target != BACK_EXIT:
                blocked_cells.add(BACK_EXIT)
            if start in self.workstations_set:
                if self.mode == "modified":
                    table_cols = {0, 1, 2, 3} if start[0] <= 3 else {5, 6, 7}
                else:
                    table_cols = {0, 1, 2} if start[0] <= 2 else {4, 5, 6}
                passable_workstations.update({
                    cell
                    for cell in self.workstations_set
                    if cell[1] == start[1] and cell[0] in table_cols
                })
        path = find_path(
            start,
            target,
            blocked_cells,
            agent_kind,
            self.path_edges_for(agent_kind, cleared),
            fire_passable,
            self.table_cells,
            self.service_bay_staff,
            self.mode,
            passable_workstations,
        )
        if path or agent_kind != "student":
            return path
        if self.mode == "modified":
            return []
        return find_path(
            start,
            target,
            self.blocked_cells,
            agent_kind,
            self.path_edges_for(agent_kind, cleared),
            fire_passable,
            self.table_cells,
            self.service_bay_staff,
            self.mode,
            passable_workstations,
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

            panic_prone = seeded_random(index + 201) < 0.28
            mobility_factor = 0.78 + seeded_random(index + 301) * 0.32
            if self.panic and panic_prone:
                pack_delay += 1 + int(seeded_random(index + 401) * 3)
                mobility_factor *= 0.85

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
                    panic_prone=panic_prone,
                    mobility_factor=mobility_factor,
                )
            )

        def make_staff(aid: str, kind: str, x: int, y: int, seed: int, exit_assign: str | None = None) -> Agent:
            if kind == "instructor":
                delay = 3 + int(seeded_random(seed) * 5)
            elif kind == "assistant":
                delay = 2 + int(seeded_random(seed) * 4)
            else: # custodian
                delay = 1 + int(seeded_random(seed) * 3)
            
            panic_prone = seeded_random(seed + 201) < 0.20
            mobility_factor = 0.80 + seeded_random(seed + 301) * 0.30
            
            if self.panic and panic_prone:
                delay += 1 + int(seeded_random(seed + 401) * 3)
                mobility_factor *= 0.85

            return Agent(aid, kind, kind, x, y, seed, wait_until=delay, target=(x, y), phase="waiting", assigned_exit=exit_assign, panic_prone=panic_prone, mobility_factor=mobility_factor)

        if self.mode == "modified":
            agents.extend(
                [
                    make_staff("I01", "instructor", 6, 0, 101),
                    make_staff("PA1", "assistant", 3, 11, 102, exit_assign="front"),
                    make_staff("PA2", "assistant", 4, 11, 103, exit_assign="back"),
                    make_staff("LC1", "custodian", 0, 10, 104, exit_assign="front"),
                    make_staff("LC2", "custodian", 2, 10, 105, exit_assign="back"),
                ]
            )
        else:
            agents.extend(
                [
                    make_staff("I01", "instructor", 6, 0, 101),
                    make_staff("PA1", "assistant", 7, 8, 102, exit_assign="front"),
                    make_staff("PA2", "assistant", 7, 9, 103, exit_assign="back"),
                    make_staff("LC1", "custodian", 7, 3, 104, exit_assign="front"),
                    make_staff("LC2", "custodian", 7, 5, 105, exit_assign="back"),
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

    def queue_length(self) -> int:
        aisle_col = 4 if self.mode == "modified" else 3
        queue_cells = {(aisle_col, y) for y in range(ROWS)}
        queue_cells.update({FRONT_EXIT, BACK_EXIT, (7, 0), (7, 1), (7, 10), (7, 11)})
        return sum(
            1
            for agent in self.agents
            if not agent.exited and (agent.x, agent.y) in queue_cells
        )

    def choose_exit(self, agent: Agent, density: dict[tuple[int, int], int]) -> tuple[int, int]:
        if agent.behavior == "locker" and agent.visited_locker:
            preferred = BACK_EXIT
            if self.find_agent_path((agent.x, agent.y), preferred, agent.kind, agent):
                return preferred
            return FRONT_EXIT

        if agent.assigned_exit == "front":
            preferred = FRONT_EXIT
        elif agent.assigned_exit == "back":
            preferred = BACK_EXIT
        else:
            if self.panic and seeded_random(agent.seed + len(density)) < 0.18:
                preferred = FRONT_EXIT if density.get(FRONT_EXIT, 0) <= density.get(BACK_EXIT, 0) else BACK_EXIT
            else:
                preferred = FRONT_EXIT if manhattan((agent.x, agent.y), FRONT_EXIT) <= manhattan((agent.x, agent.y), BACK_EXIT) else BACK_EXIT

        other = BACK_EXIT if preferred == FRONT_EXIT else FRONT_EXIT
        if self.distance_to_fire(preferred) <= 2 and self.distance_to_fire(other) > self.distance_to_fire(preferred):
            preferred = other

        if self.find_agent_path((agent.x, agent.y), preferred, agent.kind, agent):
            return preferred
        if self.find_agent_path((agent.x, agent.y), other, agent.kind, agent):
            return other
        return preferred

    def emergency_extinguisher_for(self, agent: Agent) -> tuple[int, int]:
        options = sorted(
            self.fire_extinguishers,
            key=lambda pos: (manhattan((agent.x, agent.y), pos), manhattan(pos, self.fire_origin)),
        )
        for option in options:
            if self.find_agent_path((agent.x, agent.y), option, agent.kind, agent):
                return option
        return options[0]

    def distressed_student_target(self, agent: Agent) -> tuple[int, int] | None:
        distressed = [
            item
            for item in self.agents
            if item.kind == "student"
            and not item.exited
            and item.phase in {"tripped", "fainted", "hesitating", "panic_freeze"}
        ]
        if not distressed:
            return None
        nearest = min(distressed, key=lambda item: manhattan((agent.x, agent.y), (item.x, item.y)))
        return (nearest.x, nearest.y)

    def target_for(self, agent: Agent, density: dict[tuple[int, int], int]) -> tuple[int, int]:
        if agent.kind == "student":
            if self.time < agent.wait_until:
                return agent.target
            if agent.behavior == "locker" and not agent.visited_locker:
                locker_cell = locker_for(self.mode)
                locker_safe = (
                    self.distance_to_fire(locker_cell) > 2
                    and len(self.active_fire_cells) < 8
                    and self.fire_damage < 900
                    and not (self.mode == "modified" and self.fire_origin_name == "assistant")
                )
                if locker_safe and self.find_agent_path((agent.x, agent.y), locker_cell, agent.kind, agent):
                    target_cell = locker_cell
                else:
                    agent.visited_locker = True
                    if agent.phase in {"waiting", "retrieving_locker"}:
                        agent.phase = "evacuating"
                    target_cell = self.choose_exit(agent, density)
            elif agent.behavior == "peer" and agent.phase == "waiting":
                peer_col = 4 if self.mode == "modified" else 3
                return (peer_col, agent.y)
            else:
                target_cell = self.choose_exit(agent, density)
        elif agent.kind == "instructor":
            if agent.phase == "waiting" or self.time < agent.wait_until:
                return agent.target
            if agent.phase in {"to_extinguisher", "retrieving_extinguisher"}:
                return agent.target if agent.target in self.fire_extinguishers else self.emergency_extinguisher_for(agent)
            target_cell = self.choose_exit(agent, density)
        elif agent.kind in {"assistant", "custodian"}:
            if self.time < agent.wait_until:
                return agent.target
            bay_step = staff_bay_waypoint(agent, self.mode)
            if bay_step is not None:
                return bay_step

            if agent.kind == "assistant":
                preferred = FRONT_EXIT if agent.assigned_exit == "front" else BACK_EXIT
                if (agent.x, agent.y) == preferred or self.find_agent_path((agent.x, agent.y), preferred, agent.kind, agent):
                    return preferred
                return BACK_EXIT if preferred == FRONT_EXIT else FRONT_EXIT

            if agent.phase in {"to_extinguisher", "suppressing_fire"}:
                return agent.target if agent.target in self.fire_extinguishers else self.emergency_extinguisher_for(agent)

            students_left = any(item.kind == "student" and not item.exited for item in self.agents)
            if students_left:
                distressed_target = self.distressed_student_target(agent)
                if distressed_target is not None:
                    return distressed_target
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
            rear_waypoint_row = 9 if self.mode == "modified" else 10
            if target_cell[1] == 0 and agent.y == 0:
                return target_cell
            if target_cell[1] == 11 and agent.y >= rear_waypoint_row:
                return target_cell
            if agent.x != aisle_col:
                target_row = rear_waypoint_row if agent.y >= rear_waypoint_row else agent.y
                waypoint = (aisle_col, target_row)
                if self.distance_to_fire(waypoint) <= 1:
                    return (aisle_col, 0 if target_row >= rear_waypoint_row else rear_waypoint_row)
                return waypoint
            else:
                if target_cell[1] == 0:
                    if agent.y == 0:
                        return target_cell
                    if self.distance_to_fire((aisle_col, 0)) <= 1:
                        return BACK_EXIT if self.find_agent_path((agent.x, agent.y), BACK_EXIT, agent.kind, agent) else (aisle_col, rear_waypoint_row)
                    return (aisle_col, 0)
                else:
                    if agent.y >= rear_waypoint_row:
                        return target_cell
                    if self.distance_to_fire((aisle_col, rear_waypoint_row)) <= 1:
                        return FRONT_EXIT if self.find_agent_path((agent.x, agent.y), FRONT_EXIT, agent.kind, agent) else (aisle_col, 0)
                    return (aisle_col, rear_waypoint_row)
        return target_cell

    def speed_for(self, agent: Agent, density: dict[tuple[int, int], int]) -> float:
        # Movement budget per step — agents may only ever consume 1.0 per step.
        speed = 0.72 if agent.kind == "student" else 1.10
        crowded = density.get((agent.x, agent.y), 1)

        aisle_col = 4 if self.mode == "modified" else 3
        non_squeeze_cols = {3, 4, 7} if self.mode == "modified" else {3, 7}

        # Row-workstation squeeze: narrow gap between rows slows movement
        if is_lab_cell((agent.x, agent.y)) and agent.x not in non_squeeze_cols:
            speed *= 0.45   # tight row gaps

        # Centre-aisle is the bottleneck corridor
        if agent.x == aisle_col:
            if crowded >= 2:
                speed *= 0.60  # single-file shuffling
            if crowded >= 4:
                speed *= 0.45  # near-crush

        # Heat/smoke zone near any active fire cell
        if self.distance_to_fire((agent.x, agent.y)) <= 3:
            speed *= 0.65

        # General crowd slowdown
        if crowded >= 3:
            speed *= 0.50
        if crowded >= 5:
            speed *= 0.38  # very congested — stampede risk zone

        # Panic does NOT necessarily speed people up — it causes hesitation
        if self.panic:
            if agent.kind == "student":
                speed *= 0.85
            elif agent.kind == "assistant":
                speed *= 0.95
            if agent.kind == "student" and agent.panic_prone:
                speed *= 0.78

        # Modified layout has clearer pathways and better signage
        if self.mode == "modified":
            speed *= 1.92

        if agent.kind == "student":
            speed *= agent.mobility_factor
            if self.time > 220:
                speed *= 2.20
            if self.time > 300:
                speed *= 2.00

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
        previous_positions = {
            agent.agent_id: ((agent.x, agent.y), agent.exited)
            for agent in self.agents
        }

        suppressors = sum(
            1
            for agent in self.agents
            if agent.kind in {"instructor", "custodian"}
            and agent.phase in {"retrieving_extinguisher", "suppressing_fire", "aiding_students"}
            and not agent.exited
            and manhattan((agent.x, agent.y), self.fire_origin) <= 6
        )
        self.suppression_level = suppressors
        self.spread_fire(density)
        self.fire_damage += max(0, 2 + len(self.active_fire_cells) - suppressors * 3)

        for agent in self.agents:
            if agent.exited or agent.is_casualty:
                continue

            dist_to_fire = self.distance_to_fire((agent.x, agent.y))
            
            # Fire starts weak and grows stronger over time and as it spreads
            intensity = min(1.0, (len(self.active_fire_cells) / 4.0) + (self.time / 60.0))

            # Agents behind the partition wall are shielded from direct radiant heat
            # unless the fire has breached the service bay itself.
            is_shielded = (agent.x, agent.y) in self.service_bay_staff and not any(f in self.service_bay_staff for f in self.active_fire_cells)

            if is_shielded:
                if dist_to_fire <= 1:
                    agent.health -= (2.0 * intensity)
                elif dist_to_fire == 2:
                    agent.health -= (1.0 * intensity)
            else:
                if dist_to_fire <= 1:
                    agent.health -= (15.0 * intensity)
                elif dist_to_fire == 2:
                    agent.health -= (5.0 * intensity)
                elif dist_to_fire == 3:
                    agent.health -= (2.0 * intensity)
                
            if agent.health <= 0:
                agent.is_casualty = True
                self.add_event("casualty", f"{agent.agent_id} succumbed to smoke/fire and became a casualty")
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
                elif agent.phase in {"hesitating", "panic_freeze"}:
                    agent.phase = "evacuating"
            elif agent.kind == "instructor":
                if agent.phase == "waiting" and self.time >= agent.wait_until:
                    agent.phase = "to_extinguisher"
                    agent.target = self.emergency_extinguisher_for(agent)
                    agent.path = []
                    self.add_event("move", "Professor alerted — moving to fire extinguisher")
                elif agent.phase == "retrieving_extinguisher" and self.time >= agent.wait_until:
                    agent.phase = "suppressing_fire"
                    agent.wait_until = self.time + 3
                    self.add_event("extinguisher", "Professor used extinguisher to slow the fire spread")
                elif agent.phase == "suppressing_fire" and self.time >= agent.wait_until:
                    agent.phase = "evacuating"
                    self.add_event("move", "Professor finished fire response and resumed egress")
            elif agent.kind in {"assistant", "custodian"}:
                if agent.phase == "waiting" and self.time >= agent.wait_until:
                    exit_label = "front" if agent.assigned_exit == "front" else "back"
                    if agent.kind == "custodian":
                        agent.phase = "to_extinguisher"
                        agent.target = self.emergency_extinguisher_for(agent)
                        agent.path = []
                        self.add_event(
                            "move",
                            f"Custodian {agent.agent_id} moving through the passage to reduce fire damage and assist students",
                        )
                    else:
                        agent.phase = "holding_door"
                        self.add_event(
                            "move",
                            f"Student assistant {agent.agent_id} moving through the passage to hold the {exit_label} exit",
                        )
                elif agent.kind == "custodian" and agent.phase == "suppressing_fire" and self.time >= agent.wait_until:
                    agent.phase = "aiding_students"
                    self.add_event("move", f"Custodian {agent.agent_id} finished first-response fire control and began assisting students")

            new_target = self.target_for(agent, density)
            if new_target != agent.target:
                agent.target = new_target
                agent.path = []  # Target changed, clear cached path to recalculate

            if self.time < agent.wait_until or self.time < agent.trip_until:
                continue

            # Stampede pin: agent is knocked down by crowd surge
            if agent.kind == "student" and self.time < agent.stamped_until:
                continue

            # Assistant proximity checks for recovery help and smoke fainting prevention
            assistant_near_current = any(
                (a.kind == "assistant" or (a.kind == "custodian" and a.phase == "aiding_students"))
                and a.agent_id != agent.agent_id
                and not a.exited
                and abs(a.x - agent.x) + abs(a.y - agent.y) <= 2
                for a in self.agents
            )

            # Fire smoke/heat proximity fainting check
            fire_dist = self.distance_to_fire((agent.x, agent.y))
            if agent.kind == "student" and fire_dist <= 2:
                faint_smoke_chance = 0.07 if self.panic else 0.03
                if self.time > 220:
                    faint_smoke_chance *= 0.35
                if self.time > 320:
                    faint_smoke_chance = 0.0
                if agent.kind == "student" and agent.panic_prone:
                    faint_smoke_chance *= 1.55
                if self.suppression_level:
                    faint_smoke_chance *= max(0.25, 1 - self.suppression_level * 0.35)
                if assistant_near_current:
                    faint_smoke_chance *= 0.25
                if seeded_random(self.time * agent.seed + 555) < faint_smoke_chance:
                    # Faint from smoke — longer recovery, agents nearby must step around
                    duration = 5 if self.mode == "modified" else 9
                    if assistant_near_current:
                        duration = max(2, duration // 3)
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
            hesitation_chance = 0.040
            if agent.kind == "student" and agent.panic_prone:
                hesitation_chance = 0.10
            if self.panic and agent.kind == "student" and seeded_random(self.time + agent.seed) < hesitation_chance:
                agent.phase = "panic_freeze" if agent.panic_prone else "hesitating"
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
            if agent.kind == "student" and agent.x == aisle_col and local_density >= 5 and self.panic:
                stamp_roll = seeded_random(self.time * agent.seed + 991)
                if stamp_roll < 0.18:
                    pin_duration = 3 + int(seeded_random(self.time + agent.seed + 3) * 4)  # 3-6 steps
                    agent.stamped_until = self.time + pin_duration
                    agent.phase = "tripped"  # visually show as tripped/knocked down
                    self.add_event("trip", f"{agent.agent_id} knocked down in centre-aisle stampede")
                    continue

            # ── Trip / faint check ────────────────────────────────────────────
            base_trip = 0.065 if local_density >= 3 else 0.022
            trip_chance = base_trip * (1.8 if self.panic else 1.0) * (0.20 if self.mode == "modified" else 1.0)
            if self.time > 220:
                trip_chance *= 0.35
            if self.time > 320:
                trip_chance = 0.0
            if agent.kind == "student" and agent.panic_prone:
                trip_chance *= 1.45
            
            # Proximity to student assistants reduces tripping chance
            assistant_near_next = any(
                (a.kind == "assistant" or (a.kind == "custodian" and a.phase == "aiding_students"))
                and a.agent_id != agent.agent_id
                and not a.exited
                and abs(a.x - next_cell[0]) + abs(a.y - next_cell[1]) <= 2
                for a in self.agents
            )
            if assistant_near_next:
                trip_chance *= 0.35

            if agent.kind == "student" and seeded_random(self.time * agent.seed + self.trips) < trip_chance:
                self.trips += 1
                faint_roll = seeded_random(self.time * agent.seed + self.trips + 77)
                is_faint = self.panic and faint_roll < 0.22   # higher faint chance
                
                if is_faint:
                    # Fainted: needs to be helped or self-recover — long delay
                    duration = 4 if self.mode == "modified" else 8
                    if assistant_near_next:
                        duration = max(2, duration // 3)
                    agent.trip_until = self.time + duration
                    agent.phase = "fainted"
                    self.add_event("trip", f"{agent.agent_id} fainted due to panic/smoke inhalation")
                else:
                    # Tripped: scrambles back up — moderate delay
                    duration = 2 if self.mode == "modified" else 4
                    if assistant_near_next:
                        duration = max(1, duration - 3)
                    agent.trip_until = self.time + duration
                    agent.phase = "tripped"
                    self.add_event("trip", f"{agent.agent_id} tripped in a congested zone")
                continue

            agent.x, agent.y = next_cell
            bay_passage_exit_cell = (6, 10) if self.mode == "modified" else (6, self.service_bay_passage[1])
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
        non_support_left = any(
            agent.kind not in {"assistant", "custodian"} and not agent.exited
            for agent in self.agents
        )
        if not non_support_left:
            for agent in self.agents:
                if agent.kind in {"assistant", "custodian"} and not agent.exited:
                    agent.exited = True
            evacuated = len(self.agents)
        for agent in self.agents:
            previous_pos, was_exited = previous_positions[agent.agent_id]
            if not was_exited and not agent.exited and (agent.x, agent.y) == previous_pos:
                agent.wait_time += 1
        self.queue_lengths.append(self.queue_length())
        self.rate.append((self.time, evacuated))
        if evacuated == len(self.agents) or self.time >= 400:  # extended max steps for realistic slow evacuation
            self.completed = True

    def handle_arrival(self, agent: Agent):
        pos = (agent.x, agent.y)
        if agent.behavior == "locker" and not agent.visited_locker and pos == locker_for(self.mode):
            if self.time > 180 or len(self.active_fire_cells) >= 8 or self.fire_damage >= 900:
                agent.visited_locker = True
                if self.mode == "modified":
                    agent.assigned_exit = "back"
                agent.phase = "evacuating"
                self.add_event("locker", f"{agent.agent_id} skipped locker retrieval as fire conditions escalated")
                return
            agent.visited_locker = True
            if self.mode == "modified":
                agent.assigned_exit = "back"
            # Locker retrieval: rummaging through a bag/locker takes significant time
            locker_delay = 10 + int(seeded_random(agent.seed + 77) * 6)  # 10-15 steps
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
        if agent.kind == "instructor" and agent.phase == "to_extinguisher" and pos == agent.target:
            agent.phase = "retrieving_extinguisher"
            agent.wait_until = self.time + 4   # realistic extinguisher grab time
            self.add_event("extinguisher", "Professor retrieved the nearest reachable fire extinguisher")
            return
        if agent.kind == "custodian" and agent.phase == "to_extinguisher" and pos == agent.target:
            agent.phase = "suppressing_fire"
            agent.wait_until = self.time + 5
            self.add_event("extinguisher", f"Custodian {agent.agent_id} started reducing fire damage")
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

        # Check if a student assistant is at this exit door holding it
        door_cell = FRONT_EXIT if door == "front" else BACK_EXIT
        assistant_holding = any(
            a.kind == "assistant"
            and (a.x, a.y) == door_cell
            and not a.exited
            for a in self.agents
        )

        if assistant_holding:
            # Door held open — only one person can squeeze through per step
            pressure = 0.0
            self.door_cooldown[door] = self.time + 1  # one-at-a-time throughput
        else:
            # Unmanaged door: high collision chance; people push and create jams
            # Current layout has single-width corridor exits — very congested
            pressure = 0.40 + (0.18 if self.panic else 0.0) + (0.08 if door == "front" else 0.03)

        if seeded_random(self.time + agent.seed + self.door_collisions) < pressure:
            self.door_collisions += 1
            # Longer door jam: 3-5 steps of blocked exit
            jam_duration = 3 + int(seeded_random(self.time + self.door_collisions) * 3)
            self.door_cooldown[door] = self.time + jam_duration
            self.add_event("door", f"{door.title()} door jam — {jam_duration} step blockage")
            return
        agent.exited = True
        agent.exit_time = self.time
        # After each exit, small throughput gap (shoulder-width squeeze)
        if not assistant_holding:
            self.door_cooldown[door] = self.time + 1

    def summary(self) -> dict[str, int | float]:
        total_agents = len(self.agents)
        evacuated = sum(1 for agent in self.agents if agent.exited)
        casualties = sum(1 for agent in self.agents if getattr(agent, 'is_casualty', False))
        average_wait = (
            sum(agent.wait_time for agent in self.agents) / total_agents
            if total_agents
            else 0
        )
        average_queue = (
            sum(self.queue_lengths) / len(self.queue_lengths)
            if self.queue_lengths
            else 0
        )
        throughput_per_minute = (evacuated / self.time * 60) if self.time else 0
        exit_utilization = (evacuated / (self.time * 2) * 100) if self.time else 0
        return {
            "time": self.time,
            "evacuated": evacuated,
            "casualties": casualties,
            "trips": self.trips,
            "door_collisions": self.door_collisions,
            "max_heat": max(self.heatmap.values(), default=0),
            "fire_damage": self.fire_damage,
            "average_wait_time": round(average_wait, 2),
            "average_queue_length": round(average_queue, 2),
            "throughput_per_minute": round(throughput_per_minute, 2),
            "exit_utilization_percent": round(exit_utilization, 2),
            "processing_time": self.time,
        }
