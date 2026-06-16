# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 2: The World Representation - Grids and Spatial Dynamics

### 2.1 The `Grid` Architecture
The physical world of V3 is governed by the `Grid` class. This class acts as the ultimate arbiter of physical reality. It is a 2D array matrix where each cell has coordinates `(x, y)`.

#### 2.1.1 Cell Types and Enums
Cells are not merely empty or full; they carry semantic meaning. A cell can be:
- `EMPTY`: A traversable space.
- `WALL`: An impassable structural boundary.
- `DOOR`: A traversable space that represents an exit or transition.
- `DESK` / `CHAIR`: Impassable obstacles that dictate the layout of the lab.

When the grid is initialized, it reads a layout definition (often a 2D array of integers or a string map) and populates its internal matrix. This matrix is heavily queried every frame by every agent, making its lookup efficiency ($O(1)$) critical.

### 2.2 Collision Detection and Mutual Exclusion
In physical reality, two human beings cannot occupy the same 0.5m x 0.5m square. The `Grid` enforces this via an agent-mapping layer. While the static grid holds the walls, a dynamic map tracks which agent is in which cell.

When an agent attempts to move from `(x1, y1)` to `(x2, y2)`, the engine queries the grid:
1. Is `(x2, y2)` a Wall or Desk? If yes, movement rejected.
2. Is `(x2, y2)` occupied by another Agent? If yes, movement rejected (or handled as a collision).

#### 2.2.1 The Queueing Effect
Because of this strict mutual exclusion, crowd dynamics naturally emerge without complex flocking algorithms (like Boids). If an agent stops in a 1-cell-wide corridor, the agent behind them cannot step into their cell. That agent stops. The agent behind *them* stops. This creates a shockwave queue, identical to real-world traffic jams or doorway crushes during a fire.

### 2.3 The Cellular Automata of Fire
Fire is not static in V3; it is a dynamic, spreading entity governed by Cellular Automata (CA) principles. 
Every few ticks, the fire evaluates its neighbors (up, down, left, right). Based on the flammability of the neighboring cell (e.g., a wooden desk vs an empty floor) and a propagation probability, the fire expands.

#### 2.3.1 Smoke and Heat Maps
Beyond the immediate flames, the grid also manages invisible "fields":
- **Heat Maps**: Cells adjacent to fire increase in heat.
- **Smoke Maps**: Smoke propagates faster than fire and can reduce agent visibility. 

When an agent requests a path to the exit, it isn't just looking for the shortest distance; it queries the grid's heat map to avoid pathing directly through an inferno, forcing agents to dynamically reroute as the fire spreads.
