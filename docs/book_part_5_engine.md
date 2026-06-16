# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 5: The Simulation Engine - The Heartbeat of V3

### 5.1 The `Simulation` Class Lifecycle
The `Simulation` class in `comlab_v3/engine.py` manages the main loop of the Agent-Based Model (ABM). Rather than managing visual rendering, it processes the physics, kinematics, and logical steps of time.

The lifecycle of a single "tick" or "frame" inside the `step()` method executes the following stages:
1. **Time Advancement**: Increment simulation time `self.time`.
2. **Density Mapping**: Compute the spatial distribution of agents on the grid using `density_map()`, updating the heat map.
3. **Fire Progression**: `spread_fire` evaluates burning cells and propagates fire to adjacent cells every $7$ ticks, based on suppression levels and fuel weights.
4. **Health Decay**: Proximity to fire (Manhattan distance $\le 3$) inflicts health penalties on agents, flagging them as casualties if health drops to $\le 0$.
5. **State Recovery**: Students tripped or fainted check if their immobilizing timers have expired to stand back up.
6. **Role Actions**: Instructors, assistants, and custodians progress their unique task sequences (retrieving extinguishers, holding doors, aiding students).
7. **Target & Path updates**: Verify if agent targets have changed, and compute paths for agents without cached moves.
8. **Egress Step execution**: Iterate through all active agents to accumulate speed bank, roll for tripping/fainting risks, and update coordinates to their next step.
9. **Exit evaluation**: Move agents who reached the exit into the evacuated state, handle door jams, and verify if the simulation has completed.

---

### 5.2 Agent Roster & Sequential Step Processing
All agents are initialized at the start of the simulation by `self.make_agents()`. **There is no dynamic spawning during the simulation run.** 

During step execution, agents are processed sequentially in a simple loop:
- The order of movement is dictated by their position in the `self.agents` roster list (seeded by layout workstations).
- Rather than a complex simultaneous conflict resolution engine, V3 relies on **sequential step updates**:
  - An agent moves into `next_cell` if they have speed budget, popping the coordinate.
  - Squeezing multiple agents into the same cell is physically permitted by the grid but penalized mathematically: local congestion decreases movement speed and increases tripping/fainting chances during their sequential evaluation.

---

### 5.3 Benchmarking and Headless Execution
Because the engine is entirely decoupled from the UI, it can be run "headlessly" in a `while` loop until all agents exit. 
A simulation that takes 3 minutes to watch in the browser might complete in 0.5 seconds headlessly. This allows the researchers to run the simulation 10,000 times overnight with different random seeds to generate statistically significant data (mean evacuation time, variance, standard deviation) rather than relying on a single anecdotal run.
