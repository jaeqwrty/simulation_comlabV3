# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 6: The API and Data Transport Layer

### 6.1 Bridging Python and the Browser
The physics engine is written in Python, but the visualization requires HTML5 Canvas and JavaScript. To bridge this gap, V3 utilizes Python's built-in `http.server` module to run a web server. 

Depending on the environment, V3 runs in two configurations:
1. **Local Server (`comlab_v3/web.py`)**: Spawns a `ThreadingHTTPServer` to handle incoming HTTP requests and run a background daemon thread that steps the simulation in real time.
2. **Serverless Deployment (`api/index.py`)**: Runs on Vercel as serverless functions. Since serverless runs are request-driven and cannot keep background threads alive, the server records the time elapsed between requests and catches up by executing the corresponding number of simulation steps on demand.

---

### 6.2 State Serialization & HTTP Polling
Every tick, the Python engine produces a state description including:
- Time step and overall stats (escaped count, casualty count, trips).
- An array of active agent objects (IDs, current $x$ and $y$, phase, and destination target).
- A heat map of historical agent densities.
- Dynamic layout coordinates (desks, exits, extinguishers) so the frontend does not have to hardcode layout dimensions.

The server serializes this dictionary into a JSON string using `json.dumps()` and serves it over standard HTTP REST. The JavaScript frontend (`app.js`) polls this `/api/state` endpoint every ~100ms, receiving the full payload and redrawing the HTML5 Canvas accordingly.

---

### 6.3 Input Validation Models
To ensure incoming configuration options match the types expected by the engine, the API relies on `Pydantic` models defined in `comlab_v3/models.py`:
- `SimulationConfig`: Validates parameters like the active layout `mode` (`"current"` or `"modified"`), `panic` state, `fireOrigin`, and simulation `speed`.
- `ControlAction`: Validates control state triggers (`"start"`, `"pause"`, `"step"`) along with optional configs.
- `ResetRequest`: Validates reset instructions.

Outgoing simulation states are serialized directly to JSON via Python dictionary mapping rather than Pydantic schemas, minimizing overhead.

---

### 6.4 The Frontend `Canvas`
The frontend is a lightweight visualizer. It receives the JSON array of agents and loops over them, calling `ctx.fillRect()` or painting circular sprites based on the agent's `kind` (e.g. blue for student, red for instructor) and `phase` (e.g. grey for tripped/fainted). 

Because the frontend performs no physics math or pathfinding calculations, it remains highly responsive and runs smoothly on both desktop and mobile web browsers.
