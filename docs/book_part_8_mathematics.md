# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 8: Mathematical Formulations and Algorithmic Specifications

This chapter details the mathematical models, formulas, and exact algorithms governing the crowd dynamics, fire propagation, pathfinding heuristics, and physical systems within the V3 Agent-Based Model (ABM).

---

### 8.1 Sinusoidal Pseudo-Random Number Generation (PRNG)

To ensure absolute determinism across simulation runs without relying on system-dependent entropy sources (like Python's `random` or OS-level generators), the simulation implements a custom PRNG. This generator produces a uniform pseudo-random distribution in the interval $[0, 1)$ for any integer seed $S$.

#### 8.1.1 Formulation
Let $S \in \mathbb{Z}$ be the seed value. The random float $R(S)$ is computed as follows:

\[\theta(S) = (S \times 9301 + 49297) \pmod{2\pi}\]
\[V(S) = 233280 \times \sin(\theta(S))\]
\[R(S) = V(S) - \lfloor V(S) \rfloor\]

Where:
- $\sin(\cdot)$ maps the input to a repeating wave in $[-1, 1]$.
- Multiplying by $233280$ scales the amplitude, generating a high-frequency sequence.
- The fractional subtraction $V - \lfloor V \rfloor$ extracts the mantissa (decimal part), guaranteeing $R(S) \in [0, 1)$.

#### 8.1.2 Deterministic Roll Seeds
Every probabilistic event in the engine (e.g., tripping, fainting, fire spreading) constructs a unique seed by combining the current tick $t$, agent properties, and spatial coordinates. For example, the fire propagation roll seed for cell $(x, y)$ at tick $t$ is calculated as:

\[S_{fire} = t \times 1009 + x \times 37 + y \times 101 + |C_{fire}|\]

Where $|C_{fire}|$ is the number of currently active fire cells. This prevents correlations between neighboring cells.

---

### 8.2 Fire Propagation Cellular Automata

Fire spreads through a 2D cellular automaton model where each cell's transition probability is dynamically calculated based on fuel density, local heat, occupant congestion, and suppression levels.

#### 8.2.1 The Probability Equation
At every spread interval ($t \pmod 7 == 0$), the probability $P_{spread}(c)$ of fire spreading to an empty neighbor cell $c = (x, y)$ from an adjacent burning cell is:

\[P_{spread}(c) = \left( \beta \times W_{fuel}(c) + \rho_{congestion}(c) + H_{heat}(c) + B_{wiring}(c) \right) \times \left(1 - \sigma\right) + P_{panic}\]

Where:
- $\beta = 0.016$ is the base propagation coefficient.
- $W_{fuel}(c)$ is the fuel weight coefficient of the target cell type (see Table below).
- $\rho_{congestion}(c) = \min(0.20, D(c) \times 0.04)$ is the congestion factor, representing the increased flammability or obstacle interference from crowd density $D(c)$ (number of agents in cell $c$).
- $H_{heat}(c) = \min(0.18, \frac{Heat(c)}{360})$ is the heat coefficient derived from the cell's historical exposure.
- $B_{wiring}(c) = 0.08$ is a bonus added if the cell contains major electrical wiring (e.g., data racks, workstations).
- $\sigma = \min(0.80, S_{level} \times 0.25)$ is the fire suppression factor, where $S_{level}$ is the number of active first-responders (assistants, custodian, professor) suppressing the fire.
- $P_{panic} = 0.006$ if panic mode is enabled (representing secondary ignitions or chaos), else $0.0$.

#### 8.2.2 Fuel Weights ($W_{fuel}$)
The fuel coefficient is discretized based on the physical furniture mapped to cell $c$:

| Cell Type / Obstacle | Fuel Weight ($W_{fuel}$) | Description |
| :--- | :--- | :--- |
| **Data Racks** | $2.4$ | High density electrical equipment, rapid ignition |
| **Workstations / PCs** | $2.0$ | Plastics, wiring, monitors |
| **Student Assistant Desk**| $1.8$ | Wood, papers, intermediate fuel |
| **Shelves / Lockers** | $1.7$ | Storage materials |
| **Instructor Desk** | $1.5$ | Heavy wood desk |
| **Empty Lab Floor** | $1.0$ | Minimal fuel surface |
| **Other / Corridor** | $0.0$ | Non-flammable / concrete structure |

The final transition fires if:
\[R(S_{fire}) < \min\left(0.34, P_{spread}(c)\right)\]

This ensures that the maximum probability of fire spread per check is capped at $34\%$.

---

### 8.3 Radiant Heat & Smoke Health Decay Model

Agents lose health when they are in proximity to fire cells, with rates scaling non-linearly over time as the fire intensifies. The model incorporates physical shielding from structural walls.

#### 8.3.1 Fire Intensity
The heat and smoke intensity $I(t)$ at tick $t$ is modeled as:

\[I(t) = \min\left(1.0, \frac{|C_{fire}|}{4.0} + \frac{t}{60.0}\right)\]

This represents the thermodynamic build-up: the fire gets deadlier as it spreads (more active fire cells $|C_{fire}|$) and as smoke accumulates over time ($t$).

#### 8.3.2 Heat/Smoke Decay Formulation
Let $d$ be the Manhattan distance from the agent to the nearest active fire cell:
\[d = \min_{f \in C_{fire}} \left( |x_{agent} - x_f| + |y_{agent} - y_f| \right)\]

The health deduction per tick $\Delta H$ is calculated based on shielding:

- **Shielded** (agent is in the service bay and no fire has breached the bay):
  \[
  \Delta H = \begin{cases} 
  -2.0 \times I(t) & \text{if } d \leq 1 \\
  -1.0 \times I(t) & \text{if } d = 2 \\
  0.0 & \text{otherwise}
  \end{cases}
  \]
- **Unshielded** (standard lab/corridor layout):
  \[
  \Delta H = \begin{cases} 
  -15.0 \times I(t) & \text{if } d \leq 1 \\
  -5.0 \times I(t) & \text{if } d = 2 \\
  -2.0 \times I(t) & \text{if } d = 3 \\
  0.0 & \text{otherwise}
  \end{cases}
  \]

When an agent's cumulative health $H \leq 0$, they are flagged as a casualty ($is\_casualty = True$) and become an impassable obstacle on the grid.

---

### 8.4 Density-Dependent Agent Speed Model

To simulate crowd squeezing, physical bottlenecks, and human hesitation without continuous force vectors, V3 uses a density-dependent velocity function. This is a discrete approximation of the fundamental diagram of relation between speed and density.

#### 8.3.1 Speed Calculation Formula
Let $v_{base}$ be the base speed of the agent type ($0.72$ cells/tick for students, $1.10$ cells/tick for staff). The actual speed $v(t)$ is computed multiplicatively:

\[v(t) = v_{base} \times M_{squeeze} \times M_{aisle} \times M_{heat} \times M_{crowd} \times M_{panic} \times M_{layout} \times M_{acceleration}\]

Where:
1. **Row Squeeze Modifier ($M_{squeeze}$)**:
   If the agent is inside the main lab rows (outside the center aisle and corridors):
   \[M_{squeeze} = 0.45\]
   *(Represents maneuvering through tight desk gaps)*
   
2. **Center Aisle Bottleneck ($M_{aisle}$)**:
   If the agent is in the center aisle column:
   \[
   M_{aisle} = \begin{cases} 
   0.60 & \text{if } D_{local} \geq 2 \\
   0.45 & \text{if } D_{local} \geq 4 \\
   1.00 & \text{otherwise}
   \end{cases}
   \]
   *(Models shuffling behavior in the main exit pathway)*

3. **Fire Proximity Slowdown ($M_{heat}$)**:
   If the distance to fire $d \leq 3$:
   \[M_{heat} = 0.65\]
   *(Models disorientation, smoke inhalation, and heat-induced slowing)*

4. **General Crowd Congestion ($M_{crowd}$)**:
   Based on localized cell density $D_{local}$:
   \[
   M_{crowd} = \begin{cases} 
   0.50 & \text{if } D_{local} \geq 3 \\
   0.38 & \text{if } D_{local} \geq 5 \\
   1.00 & \text{otherwise}
   \end{cases}
   \]
   *($D_{local} \geq 5$ represents a critical stampede/crush risk zone)*

5. **Panic Hesitation ($M_{panic}$)**:
   If panic mode is enabled:
   \[
   M_{panic} = \begin{cases} 
   0.85 \times M_{prone} & \text{if Student} \\
   0.95 & \text{if Assistant} \\
   1.00 & \text{otherwise}
   \end{cases}
   \]
   Where $M_{prone} = 0.78$ if the student has the `panic_prone` characteristic.

6. **Layout Signage & Corridor Width ($M_{layout}$)**:
   If the modified layout is active (better exit placements, wider pathways):
   \[M_{layout} = 1.92\]

7. **Egress Acceleration ($M_{acceleration}$)**:
   Students accelerate as time passes due to rising urgency:
   \[
   M_{acceleration} = \begin{cases} 
   2.20 \times \text{mobility\_factor} & \text{if } t > 220 \\
   2.00 \times \text{mobility\_factor} & \text{if } t > 300 \\
   1.00 \times \text{mobility\_factor} & \text{otherwise}
   \end{cases}
   \]
   Where $\text{mobility\_factor}$ is an agent-specific capability multiplier (usually $1.0$).

---

### 8.5 Smoke Inhalation & Tripping Probabilities

#### 8.5.1 Fainting Probability (Smoke/Heat)
For student agents in close proximity to fire ($d \leq 2$), the probability of fainting on any tick is:

\[P_{faint} = P_{faint\_base} \times T_{decay} \times P_{prone\_bonus} \times S_{suppression} \times A_{assistance}\]

Where:
- $P_{faint\_base} = 0.07$ (if panicking) or $0.03$ (if calm).
- $T_{decay} = 0.35$ if $t > 220$, and $T_{decay} = 0.0$ if $t > 320$.
- $P_{prone\_bonus} = 1.55$ if `panic_prone` student, else $1.0$.
- $S_{suppression} = \max(0.25, 1.0 - S_{level} \times 0.35)$ if fire suppression is active.
- $A_{assistance} = 0.25$ if a student assistant or custodian is within a distance of $\leq 2$ (representing active guidance away from smoke).

#### 8.5.2 Tripping Probability (Crowd Congestion)
For students moving through crowded spaces, the probability of tripping on a step is:

\[P_{trip} = P_{trip\_base} \times M_{panic} \times M_{layout} \times M_{decay} \times P_{prone\_bonus} \times A_{assistance}\]

Where:
- $P_{trip\_base} = 0.065$ if local cell density $D_{local} \geq 3$, else $0.022$.
- $M_{panic} = 1.8$ if panicking, else $1.0$.
- $M_{layout} = 0.20$ if modified layout is active (representing clear physical paths), else $1.0$.
- $M_{decay} = 0.35$ if $t > 220$, and $0.0$ if $t > 320$.
- $P_{prone\_bonus} = 1.45$ if `panic_prone` student, else $1.0$.
- $A_{assistance} = 0.35$ if a student assistant is within $\leq 2$ cells.

---

### 8.6 Heuristically-Guided Breadth-First Search (BFS)

The pathfinding algorithm utilizes a queue-based search where neighbor exploration is sorted according to a Manhattan distance heuristic.

Let $p_1 = (x_1, y_1)$ and $p_2 = (x_2, y_2)$. The Manhattan distance heuristic $H(p_1, p_2)$ is defined as:

\[H(p_1, p_2) = |x_1 - x_2| + |y_1 - y_2|\]

During the search from start $S$ to target $T$:
1. A queue $Q$ is initialized with $S$.
2. For each popped cell $u$, neighbors $N(u)$ are retrieved.
3. Neighbors are sorted in ascending order of their distance to the target:
   \[N_{sorted}(u) = \text{sort}\left( \{ v \in N(u) \} \text{ by } H(v, T) \right)\]
4. Sorted neighbors are appended to the FIFO queue.

By sorting neighbors before pushing them to the queue, the search prioritizes directions moving towards the target, resulting in a greedy search behavior that matches realistic egress navigation.
