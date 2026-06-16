# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 5: The Simulation Engine - The Heartbeat of V3

### 5.1 The `SimulationEngine` Lifecycle
The `SimulationEngine` is the conductor of the orchestra. It does not contain the logic for how a person moves (that's the `Agent`), nor does it store the physical walls (that's the `Grid`). Instead, it iterates through time and forces all systems to update.

The lifecycle of a single "tick" or "frame" looks like this:
1. **Spawn Phase**: (If applicable) inject new agents into the simulation.
2. **Fire Update**: The cellular automata rules for fire spread are calculated and applied.
3. **Agent Intention Phase**: Every agent calculates its desired next move (adds to `speed_bank`, requests pathing).
4. **Conflict Resolution Phase**: The engine looks at all requested moves.
5. **Commit Phase**: Moves are finalized, grid state is updated, agents enter/exit the lab.
6. **Data Collection**: Metrics (evacuated count, casualties, average exit time) are recorded.

### 5.2 Conflict Resolution: The Collision Engine
Step 4 is the most crucial part of the engine. Suppose Agent A and Agent B both want to move into Cell (5, 5). Who wins?

If V3 simply processed agents in a list sequentially (`for agent in agents: agent.move()`), the agent at index 0 would always win. This creates a severe bias based on memory allocation order, entirely ruining the physical realism.

Instead, V3 uses a **Simultaneous Resolution** approach:
- All agents submit their "desired next cell".
- The engine groups these requests by target cell.
- If a cell has 1 requester, the move is approved.
- If a cell has >1 requesters, a deterministic conflict resolution fires. This might be based on:
  - Momentum (who is moving faster?)
  - Random Seed (deterministic tie-breaker).
  - Push Dynamics (can they squeeze? In V3, usually one is denied and stays in place).

### 5.3 Benchmarking and Headless Execution
Because the engine is entirely decoupled from the UI, it can be run "headlessly" in a `while` loop until all agents exit. 
A simulation that takes 3 minutes to watch in the browser might complete in 0.5 seconds headlessly. This allows the researchers to run the simulation 10,000 times overnight with different random seeds to generate statistically significant data (mean evacuation time, variance, standard deviation) rather than relying on a single anecdotal run.
