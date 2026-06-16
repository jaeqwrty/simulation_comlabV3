# Section 3: Pathfinding & Navigation

Pathfinding logic is highly deterministic and acts as the brain behind agent movement. It is defined in `comlab_v3/pathfinding.py` and deeply integrated into `engine.py`.

## 3.1 Algorithm
The primary algorithm is a heuristic-driven **Breadth-First Search (BFS)**, technically a greedy BFS since it sorts neighbors by Manhattan distance to the target at each step.
- `manhattan(a, b)`: Used as the heuristic to prefer neighbors closer to the target.
- It finds paths cell-by-cell avoiding dynamic and static obstacles.

## 3.2 Obstacle Detection (`is_obstacle`)
A cell is impassable if it meets any of these conditions:
1. It is outside the grid bounds.
2. It's not a valid lab or hallway cell.
3. It exists in the `blocked_cells` set (which contains data racks, tables, walls, and fire origins).
4. Staff bypass: Staff agents like custodians and assistants are granted exceptions to walk through the "service bay" and specific fire origin points if necessary to aid others.

## 3.3 Dynamic Edges (`is_edge_blocked`)
Unlike simple grid pathfinding where cells are either blocked or open, the simulation supports **edge blocking**.
- For example, partitions that visually separate the service bay from the lab do not consume entire cells. Instead, they block the *edge* between two adjacent cells.
- The `make_service_bay_staff_edges` function dynamically constructs these impassable edges based on the layout mode (`current` vs `modified`). Staff can cross at specific "passage" gaps.

## 3.4 Dynamic Behavior
- **Caching:** Calculated paths are cached in `self.path_cache` to drastically improve performance (since BFS is called often).
- **Target Recalculation:** If an agent's path is invalidated (e.g., by a fire spreading or a door blocking), the cache is cleared and a new path is generated.
- **Center Aisle Routing:** `should_route_via_center_aisle` forces students in narrow gaps to route towards the primary center aisle rather than attempting to slip through cramped desk columns, simulating realistic crowd flow.
