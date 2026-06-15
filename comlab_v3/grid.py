from __future__ import annotations
import math
from .agents import Agent

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

MODIFIED_LOCKER = (7, 11)

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

HALLWAY_WALL = {(8, y) for y in range(ROWS)} - {FRONT_EXIT, BACK_EXIT}

PARTITION_WALL = DATA_RACKS | STUDENT_ASSISTANT_DESK

SERVICE_BAY_PASSAGE = (7, 10)

SERVICE_BAY_STAFF = DATA_RACKS | STUDENT_ASSISTANT_DESK | {SERVICE_BAY_PASSAGE}

ASSISTANT_AID_POSTS = {"front": (3, 4), "back": (3, 8)}

EXTINGUISHER_PROFESSOR = (7, 0)

EXTINGUISHER_ASSISTANT = (6, 9)

EXTINGUISHER_SHELVES = (6, 11)

FIRE_EXTINGUISHERS = (EXTINGUISHER_PROFESSOR, EXTINGUISHER_ASSISTANT, EXTINGUISHER_SHELVES)

EXTINGUISHER_EXIT = EXTINGUISHER_PROFESSOR

EXTINGUISHER_ENTRANCE = None

def seeded_random(seed: int) -> float:
    value = math.sin(seed * 9301 + 49297) * 233280
    return value - math.floor(value)

def cell_key(pos: tuple[int, int]) -> str:
    return f"{pos[0]},{pos[1]}"

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
        elif origin in {"tv", "locker", "shelves"}:
            return MODIFIED_TELEVISION
        else:  # "data"
            return (0, 4)
    else:
        if origin == "desk":
            return (6, 0)
        elif origin == "workstation":
            return (2, 5)
        elif origin in {"tv", "locker", "shelves"}:
            return TELEVISION
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
