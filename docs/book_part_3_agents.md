# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 3: The Actors - Human Behavior and Agents

### 3.1 The `Agent` Dataclass
The `Agent` in V3 is implemented as a detailed Python `dataclass` in `comlab_v3/engine.py`. This object stores the physical and psychological state of a single human being in the simulation.

Key attributes include:
- `agent_id`: A unique identifier (e.g., `"S01"` for student, `"I01"` for instructor).
- `kind`: The role of the agent (`"student"`, `"instructor"`, `"assistant"`, `"custodian"`).
- `behavior`: The psychological movement profile. For students, this can be `"immediate"`, `"task"`, `"peer"`, or `"locker"`. For staff, it is set to their corresponding `kind`.
- `x`, `y`: Current 2D integer coordinates on the grid.
- `seed`: Integer seed for reproducible random events.
- `speed_bank`: The accumulator for fractional frame-rate movement.
- `phase`: The state in the agent's state machine (e.g., `"waiting"`, `"evacuating"`, `"tripped"`, `"fainted"`, `"hesitating"`, `"panic_freeze"`, `"to_extinguisher"`, `"suppressing_fire"`, `"holding_door"`, `"aiding_students"`).
- `panic_prone`: A boolean flag representing higher sensitivity to panic-induced freezing, tripping, and smoke-induced fainting.
- `mobility_factor`: A speed multiplier representing physical capability differences.

---

### 3.2 The Kinematics of Movement (`speed_bank`)
Rather than moving agents a full cell every frame (which would make movement unrealistically fast), V3 implements a **Speed Bank** accumulator. 

During the movement phase of each simulation tick:
1. The engine calculates the agent's velocity $v$ for the tick via `self.speed_for(agent, density)`.
2. This value is added to the agent's accumulator:
   ```python
   agent.speed_bank += self.speed_for(agent, density)
   ```
3. If the accumulator is less than $1.0$, the agent cannot step and is skipped:
   ```python
   if agent.speed_bank < 1:
       continue
   ```
4. If the accumulator is $\ge 1.0$, the agent steps to the first coordinate in their path, and the accumulator is decremented by $1.0$:
   ```python
   next_cell = agent.path[0]
   agent.speed_bank -= 1
   agent.x, agent.y = next_cell
   agent.path.pop(0)
   ```

---

### 3.3 The Psychological State Machine
Agents transition through several states during an evacuation:

1. **Waiting / Packing Up**: When the alarm sounds, agents stay in the `"waiting"` phase until `self.time >= agent.wait_until`. This delay represents their "pre-movement time" (gathering belongings, saving files). 
2. **Evacuating**: Once the delay expires, their phase changes to `"evacuating"` (or corresponding staff behaviors) and they target their destination.
3. **Hesitation / Freezing**: In panic mode, students have a tick-by-tick chance to freeze, entering the `"hesitating"` or `"panic_freeze"` phase, halting progress.
4. **Tripping (`trip_until`)**: Congested cells (density $\ge 3$) trigger a tripping chance. Tripped agents transition to the `"tripped"` phase, setting `trip_until = self.time + duration`, making them obstacles.
5. **Fainting / Casualties**: Extreme heat/smoke proximity can cause an agent to faint (`"fainted"` phase), or die (`is_casualty = True`), making them permanent obstacles on the grid.

---

### 3.4 Heterogeneous Populations
By varying class attributes, V3 models distinct behaviors:
- **Students**: Move at a base speed of $0.72$. A subset ($28\%$) are flagged as `panic_prone`, making them slower under panic, more likely to trip, and $55\%$ more likely to faint from smoke. Individual student speeds are scaled by `mobility_factor` (ranging randomly from $0.78$ to $1.10$).
- **Instructors (Professors)**: Wait for a delay, transition to `"to_extinguisher"` to retrieve a fire extinguisher, stand near the fire origin in `"suppressing_fire"` phase to increase the global `suppression_level` (which reduces fire spread rates), and then evacuate.
- **Assistants / Custodians**: Move through the service bay passage shortcut (`bay_passage_cleared`) to reach and hold the exits (`"holding_door"`), or enter `"aiding_students"` phase. While nearby (Manhattan distance $\le 2$), they reduce the tripping and fainting probabilities of students by $65\%$ and $75\%$, respectively.
