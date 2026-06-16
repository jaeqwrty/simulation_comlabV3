# Section 5: Web API & Frontend Integration

The backend must communicate its state to the frontend (canvas visualizer). The codebase supports two distinct ways of running the server: local threading and serverless (Vercel).

## 5.1 Local Server (`comlab_v3/web.py`)
- **Server:** Runs a standard `ThreadingHTTPServer`.
- **`SimulationService` Thread:** Spawns a daemon thread (`_loop`) that continuously calls `sim.step()` when `running` is True. This decouples the simulation ticks from HTTP requests, allowing the simulation to run smoothly at a set `speed` in the background.
- **Endpoints:**
  - `GET /api/state`: Returns the entire state payload (agent positions, heatmaps, charts).
  - `POST /api/control`: Used to `start`, `pause`, or `step` the simulation.
  - `POST /api/reset`: Resets the board.
  - `POST /api/compare`: Runs an instant headless simulation of both layouts and returns the statistical summary for the frontend's side-by-side view.
  - **Static File Serving:** Custom handling to serve `index.html`, `app.css`, and `app.js`.

## 5.2 Serverless / Vercel API (`api/index.py`)
- Because serverless functions cannot run infinite background threads (they sleep between requests), `VercelSimulationService` works differently.
- **Time-based Catchup:** It records `self.last_tick`. On every incoming request to `/api/state`, it calculates how much real time has passed since the last request, and runs a `for` loop to execute the exact number of `sim.step()` calls required to catch up to real-time.
- **Stateless Illusion:** This makes the simulation feel like it's running live on a server, even though it's technically only progressing in bursts when the frontend polls it.

## 5.3 The Payload
The `state()` method serializes the Python simulation into a massive JSON dictionary.
- **Dynamic Data:** `time`, `active`, `evacuated`, `casualties`, `trips`, `agents` (array of dicts with x, y, phase, target), `heatmap`.
- **Layout Data:** `layout_payload` is generated once and passed along, telling the frontend exactly where to draw walls, desks, exits, and fire extinguishers so the frontend doesn't need hardcoded layout logic.

## 5.4 Frontend
Though not written in Python, the Javascript frontend (`app.js`) sits in a loop requesting `/api/state` every ~100ms. It uses HTML5 Canvas to iterate over the `agents` list and draw circles at their `(x, y)` coordinates, coloring them based on their `kind` and `phase`.
