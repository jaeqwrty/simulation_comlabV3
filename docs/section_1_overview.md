# Section 1: Overview & Architecture

## 1.1 Project Purpose
The `simulation_comlabV3` project is a Python-powered agent-based micro-simulation. It evaluates the emergency egress (evacuation) procedures of a computer lab ("ComLab V3") by comparing two layouts:
- **Current Layout**: Lockers and obstacles are near the main exit path, which could cause bottlenecks.
- **Modified Layout**: Lockers and obstacles are moved to reduce bottlenecks during emergencies.

It simulates agents (students, instructors, assistants, custodians) pathfinding under pressure (panic, fire incidents, smoke slowdowns, trips, door collisions) to measure evacuation efficiency.

## 1.2 Technology Stack
- **Simulation Engine:** Pure Python. Uses object-oriented models and deterministic logic (important for validation and benchmarking).
- **Web Server:** Python server (using `ThreadingHTTPServer`) serving local requests and a serverless version for Vercel.
- **Frontend / Visualization:** HTML Canvas driven by Vanilla JavaScript and CSS (`public/` and `comlab_v3/static/`).
- **Deployment:** Vercel serverless functions (`vercel.json` and `api/index.py`).

## 1.3 Execution Flow
1. **Local Launch:** `run.py` acts as the entry point, starting the web server defined in `comlab_v3/web.py`.
2. **Frontend Initialization:** The browser loads `index.html` and initializes the Canvas via `app.js`.
3. **Simulation Loop:** The frontend makes API requests (e.g., `/api/control` to step or start) to the Python backend. The backend advances the simulation state in `comlab_v3/engine.py` by one or more ticks and returns the updated state (agent positions, fire spread, heatmaps).
4. **Rendering:** The frontend renders agents, fires, and statistical charts based on the JSON payload.

## 1.4 Directory Structure
- `comlab_v3/` - Core Python package containing the simulation engine and models.
- `public/` - Static assets for Vercel deployments.
- `api/` - Contains `index.py` for Serverless HTTP handling on Vercel.
- `scripts/` - Benchmarking and validation scripts.
- `tests/` - Deterministic unit tests.
- `run.py` - Standard local entry point.
- `vercel.json` - Vercel deployment rewrites.
