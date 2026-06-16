# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 4: The Pathfinding - Algorithms and Evacuation Routing

### 4.1 Heuristically-Ordered BFS
In an emergency, human beings rarely calculate the mathematically perfect shortest path. In V3, pathfinding is implemented as a module-level function `find_path` inside `comlab_v3/engine.py` (with structural helpers in `comlab_v3/pathfinding.py`). 

The engine uses a **Heuristically-Ordered Breadth-First Search (BFS)**:
1. It initializes a standard FIFO double-ended queue (`deque`) starting with the agent's current position.
2. When expanding a node's neighbors, it sorts them in ascending order of their Manhattan distance to the destination target:
   \[H(v, T) = |x_v - x_T| + |y_v - y_T|\]
3. The sorted list of neighbors is appended to the queue.

This sorting forces the search to explore pathways heading towards the exit first, creating a greedy search behavior that matches realistic human egress navigation while remaining complete.

---

### 4.2 Dynamic Target Selection
Pathfinding is guided by dynamic targets returned by the `target_for()` method every step:
- **Students**: Target their lockers if safe and behavior dictates it. Once locker retrieval is complete (or if the locker is blocked by fire), they select an exit using `choose_exit()` based on local densities.
- **Instructors**: Target the professor's fire extinguisher first, move to the fire origin to suppress it, and then switch targets to the exits.
- **Assistants / Custodians**: Navigate to exit doors to hold them, or move to distressed (tripped/fainted) students to assist them.

---

### 4.3 Path Caching & Fire Invalidation
Because running BFS for dozens of agents every frame is computationally expensive, V3 implements a global path cache:

*   **Caching (`path_cache`)**: Paths are stored using the tuple `(start, target, kind, bay_passage_cleared)` as a key. If another agent of the same kind needs to navigate between the same cells, it retrieves the path in $O(1)$ time.
*   **Cache Clearing**: When fire spreads, the entire `self.path_cache` is cleared. The next time an agent needs to move, if they do not have a path cached on their agent instance, they compute a new route using `find_agent_path` which treats active fire cells as blocked obstacles.
*   **Tunnel Vision**: If an agent already has a computed path stored on their instance (`agent.path`), they will continue following it even if fire spreads across it, unless their target changes or they recalculate. This simulates realistic panic-induced tunnel vision.

---

### 4.4 Center Aisle Waypoint Routing
To prevent agents from getting stuck in U-shaped workspace layouts, the engine implements center aisle waypoint routing:
- If `should_route_via_center_aisle` evaluates to `True`, the agent does not path directly to the exit.
- Instead, they route to a waypoint column (the center aisle: $x = 3$ or $x = 4$ depending on mode).
- Once they reach the center aisle, they proceed directly to their exit target, simulating a structured egress flow out of workstation bays.
