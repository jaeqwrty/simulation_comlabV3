from __future__ import annotations
from collections import deque
from .grid import *

def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

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