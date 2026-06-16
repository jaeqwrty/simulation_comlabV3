# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 2: The World Representation - Grids and Spatial Dynamics

### 2.1 The `Grid` Architecture
The physical world of V3 is governed by the matrix definitions inside `comlab_v3/engine.py` (with helpers in `comlab_v3/grid.py`). This grid maps out the physical reality of the computer lab. It is a 2D matrix where each cell has coordinates `(x, y)`.

#### 2.1.1 Cell Types and Layout
Cells have semantic classifications defined by static sets:
- **Corridors and Hallways**: Traversable areas.
- **Walls**: Impassable structural boundaries (`HALLWAY_WALL`).
- **Exits**: Passable targets (`FRONT_EXIT`, `BACK_EXIT`).
- **Desks / Obstacles**: Impassable furniture (`WORKSTATIONS`, `DATA_RACKS`, `INSTRUCTOR_DESK`, `STUDENT_ASSISTANT_DESK`).

When the simulation is initialized, it sets up these blocked coordinate sets depending on the mode (`current` vs `modified`). Lockers and fire origins are mapped dynamically based on the active layout.

---

### 2.2 Crowd Congestion & Overlap Modeling
In physical reality, two human beings cannot occupy the exact same spot. However, rather than enforcing rigid, absolute grid mutual exclusion (which would cause lock-ups on a discrete grid), V3 models crowd dynamics through a **Density-Dependent Congestion Model**:

1. **Cell Overlapping**: Multiple agents *can* occupy the same `(x, y)` coordinate.
2. **Speed Penalty**: The engine tracks local crowd density using a `density_map()`. If a cell is crowded, any agent standing in or entering it suffers a severe speed reduction (`speed_for` multiplier is halved for density $\ge 3$, and reduced to $38\%$ for density $\ge 5$).
3. **Tripping and Stampede Risk**: Squeezing many agents into a single corridor cell increases the probability of tripping, fainting, or entering a knocked-down "stampede pin" state.

#### 2.2.1 The Bottleneck Effect
Even though physical exclusion is not strictly blocked at the grid level, realistic bottlenecks naturally emerge. If a cell contains a dense cluster of agents, they all slow to a crawl, creating a shockwave bottleneck that propagates backward. This closely mirrors real-world crowd flow where high-density packing leads to slow, shuffling movement near exit doors.

---

### 2.3 The Cellular Automata of Fire
Fire is a dynamic, spreading entity governed by Cellular Automata (CA) principles:
- **Evaluation Interval**: Fire updates every $7$ ticks.
- **Neighbor Expansion**: It spreads cardinally (up, down, left, right) to adjacent lab cells.
- **Calculated Probability**: The spread is a function of fuel density (wooden desks and data racks ignite faster than floors), heat history, occupant congestion, and suppression levels.

#### 2.3.1 Smoke and Heat Exposure
The simulation accumulates a historical heatmap of agent densities and fire presence. Proximity to fire (Manhattan distance $\le 3$) reduces agent speed and exposes them to smoke inhalation, causing health decay and potential fainting.
When fire spreads, the global path cache is cleared to force agents to re-evaluate their egress routes.
