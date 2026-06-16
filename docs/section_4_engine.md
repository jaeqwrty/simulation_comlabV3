# Section 4: Simulation Engine & Loop

The core logic of the system lives in the `Simulation` class within `comlab_v3/engine.py`.

## 4.1 Initialization (`__init__`)
When a `Simulation` is instantiated, it configures itself based on `mode` (current/modified) and other variables (panic, fire origin).
- It calculates layout differences (workstation rows, desk placement, extinguisher locations).
- It generates the agent roster (`make_agents`), randomizing parameters like pack-up delay, panic-proneness, mobility factor, and specific target assignments based on seeds to ensure deterministic reproducibility.

## 4.2 The Step Loop (`step`)
Every call to `step()` advances time by 1 tick. During a tick:
1. **Density Calculation:** A `density_map` counts how many agents are on each cell to track congestion.
2. **Fire Spread:** `spread_fire` evaluates adjacent cells to the fire origin. It uses fuel weights (e.g., data racks burn faster than empty lab cells) and congestion to calculate spread probability.
3. **Agent Actions:** Iterates through every active agent.
   - **State Recovery:** Checks if agents have recovered from being "tripped" or "fainted".
   - **Targeting:** `target_for()` dictates their current objective (retrieve locker, wait for peer, aid student, move to exit).
   - **Pathing:** If they don't have a path to their target, one is retrieved from the cache or generated via `find_agent_path`.
   - **Speed / Stamina:** Agents accumulate `speed_bank` points using `speed_for()`. They only move when they accumulate at least `1.0`. Speed is heavily penalized by crowd density, panic, narrow gaps, and smoke proximity.
   - **Panic Mechanics:** High density can trigger a "stampede" (knocking agents down for several ticks) or "tripping". Smoke proximity can cause agents to "faint".
   - **Movement:** If moving is valid, the agent's position updates to the next cell in their path.
4. **Metrics:** The system updates queue lengths, wait times, evacuation rates, and checks if all agents have evacuated.

## 4.3 Door & Exit Mechanics
- **Unmanaged Doors:** Without a staff member holding the door, agents exiting have a high chance to cause a "door collision" (jam), which blocks the exit for several ticks.
- **Managed Doors:** Assistants or Custodians move to exits and act as door holders, drastically reducing jams but creating a smooth, slower single-file bottleneck.

## 4.4 Determinism
Everything relies on pseudo-randomness seeded by agent IDs and tick times (`seeded_random`). This ensures that identical input parameters always result in the exact same evacuation time and statistics, making A/B testing between layouts mathematically sound.
