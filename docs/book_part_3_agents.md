# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 3: The Actors - Human Behavior and Agents

### 3.1 The `Agent` Dataclass
The `Agent` in V3 is implemented as a highly detailed Python `dataclass`. This object stores the entire physical and psychological state of a single human being in the simulation.

Key attributes include:
- `x, y`: Current spatial coordinates.
- `kind`: The role of the agent (e.g., 'student', 'professor', 'pwd').
- `behavior`: The psychological profile (e.g., 'calm', 'panicky', 'heroic').
- `speed_bank`: The accumulator for fractional frame-rate movement.
- `phase`: The current state in the State Machine ('waiting', 'moving', 'tripped', 'exited').

### 3.2 The Kinematics of Movement (`speed_bank`)
How do we represent someone walking 1.2 meters per second on a grid where each cell is 0.5 meters, updating 60 times a second?
If we just moved them 1 cell per frame, they would move incredibly fast. V3 solves this using a **Speed Bank**.

Every frame, the agent's base speed is added to the `speed_bank`. 
```python
agent.speed_bank += agent.speed_per_frame
if agent.speed_bank >= 1.0:
    agent.move()
    agent.speed_bank -= 1.0
```
This elegant mechanism ensures mathematically precise movement speeds over time while keeping the actual position strictly locked to discrete integer grid coordinates.

### 3.3 The Psychological State Machine
Agents are not mindless path-followers; they have a psychological lifecycle.

1. **Packing Up**: When the alarm rings, agents don't immediately bolt. They have a `packed_up` boolean and a `wait_time`. This represents the delay of realizing there is a fire, grabbing laptops, and standing up.
2. **Moving**: The agent requests a path and begins stepping toward the exit.
3. **Tripping (`trip_until`)**: In dense crowds, there is a probability of tripping. If an agent trips, their phase changes, and a `trip_until` timer is set. They become an obstacle for others, drastically increasing the chance of a fatal bottleneck.
4. **Stampeding (`stamped_until`)**: If an agent is tripped and others attempt to walk over them, they enter a stampeded state, simulating injury.
5. **Fainting**: Prolonged exposure to the grid's smoke/heat map causes exhaustion. If health reaches zero, the agent faints, becoming a permanent obstacle.

### 3.4 Heterogeneous Populations
Not all agents are identical. By tweaking the parameters of the `Agent` class, V3 supports:
- **Athletic Students**: High base speed, low trip probability.
- **Elderly/PWD**: Lower base speed, higher sensitivity to smoke.
- **Professors**: May have a programmed delay to ensure students evacuate first, or act as 'attractors' that guide confused students.

This heterogeneity is what makes the V3 ABM powerful enough to model complex, real-world university environments.
