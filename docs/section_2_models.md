# Section 2: Core Domain Models

The foundation of the simulation consists of the grid layout, the agent models, and API data models. 

## 2.1 The Environment (`comlab_v3/grid.py`)
The simulation operates on a 2D discrete grid system. 
- **Dimensions:** `ROWS = 12`, `COLS = 13` (9 for the Lab + 4 for the Hallway).
- **Locations:** Constants strictly define where everything is. 
  - Exits (`FRONT_EXIT`, `BACK_EXIT`)
  - Fire Extinguishers (`EXTINGUISHER_PROFESSOR`, etc.)
  - Furniture (`WORKSTATIONS`, `DATA_RACKS`, `INSTRUCTOR_DESK`, `CURRENT_LOCKER`, `MODIFIED_LOCKER`).
- **Helpers:** Functions like `is_lab_cell()`, `is_hallway_cell()`, and `should_route_via_center_aisle()` give context to positions dynamically. The `mode` parameter (`current` vs `modified`) alters the coordinates returned for lockers and fire origins.

## 2.2 The Entities (`comlab_v3/agents.py`)
Agents are represented by a dense Python `dataclass` named `Agent`. They hold all state variables for an individual person in the simulation:
- **Identity & Type:** `agent_id`, `kind` (student, instructor, etc.), `behavior` (locker-bound, immediate, etc.).
- **Positional State:** `x`, `y`, `target` (current destination), `path` (list of future coordinate steps).
- **Simulation State:** 
  - `phase`: String tracking their current mind state (e.g., `"waiting"`, `"evacuating"`, `"tripped"`, `"fainted"`).
  - `exited`: Boolean indicating if they have reached safety.
  - `wait_until`, `trip_until`, `stamped_until`: Integers tracking how many ticks the agent is pinned down or waiting.
- **Metrics tracking:** `wait_time`, `exit_time`, `health`.
- **Modifiers:** `panic_prone` and `mobility_factor`.

## 2.3 API Validation Models (`comlab_v3/models.py`)
The server uses **Pydantic** models to validate data flowing from the Javascript frontend to the Python backend:
- `SimulationConfig`: Defines the settings for a scenario (`mode`, `panic`, `fireOrigin`, `speed`).
- `ControlAction`: Tells the backend what to do (e.g., action `"step"`).
- `ResetRequest`: Issues a command to reset the board back to tick 0.
