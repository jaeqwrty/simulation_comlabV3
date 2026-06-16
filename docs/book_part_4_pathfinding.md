# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 4: The Pathfinding - Algorithms and Evacuation Routing

### 4.1 The Role of the `Pathfinder`
In an emergency, human beings rarely calculate the mathematically perfect shortest path. However, in an ABM, we must provide agents with a baseline intention. The `Pathfinder` class is responsible for computing the route an agent wishes to take from their current `(x, y)` to an `Exit`.

### 4.2 Greedy BFS vs A*
V3 utilizes a combination of pathfinding algorithms, depending on the computational budget and the agent's state:
1. **Greedy Best-First Search (BFS)**: This is heavily used because it is fast. It uses a heuristic (usually Manhattan distance or Euclidean distance to the door) to guess the best next step. It operates under the assumption that agents "greedily" step towards the door. While it can get stuck in U-shaped concave obstacles, computer labs usually have rectangular desks where Greedy BFS performs exceptionally well.
2. **A* Search (A-Star)**: For agents that are completely blocked by a complex arrangement of fire and debris, the engine can fall back to A*. A* guarantees the shortest path by balancing the distance already traveled ($g(n)$) and the heuristic distance to the goal ($h(n)$). It is computationally heavier but ensures agents don't walk into dead ends if a path exists.

### 4.3 Dynamic Recalculation
Pathfinding in V3 is not a one-and-done operation. 
If an agent computes a path at Tick 1, by Tick 50, a fire might have spread across that path, or a group of students might have tripped, creating a human barricade.

V3 handles this through **Path Invalidation**:
- As an agent steps forward, it looks at the next $N$ steps of its cached path.
- It checks the `Grid` to see if those cells are now categorized as `FIRE` or `BLOCKED`.
- If blocked, the agent discards its cached path and triggers a recalculation.
- To prevent CPU spikes (where 50 agents all recalculate A* on the exact same frame), the engine queues these recalculations or applies a small heuristic jitter.

### 4.4 The "Doorway Funnel" Algorithm Challenge
The most difficult aspect of simulation pathfinding is the doorway. When 30 agents all target a single 1-cell wide door, their paths converge. 
If they simply follow shortest-path, they will all try to enter the exact same cell simultaneously. The V3 engine resolves this via strict queueing (discussed in Part 5), but the Pathfinder helps by sometimes targeting "Doorway Adjacent" cells—creating a natural semi-circle funnel rather than a straight line of blocked agents.
