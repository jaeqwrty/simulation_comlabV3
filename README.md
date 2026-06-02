# ComLab V3 Emergency Egress Simulation

Python-powered agent-based micro-simulation for comparing the current ComLab V3 layout against a safer modified layout.

The browser is only the visual interface. The simulation logic, agents, pathfinding, incidents, metrics, and comparison run in Python.

## Project Structure

```text
ModelandSimulation/
  run.py                    # main launcher
  comlab_v3/
    engine.py               # simulation rules and agent logic
    web.py                  # local Python server and API
    static/
      index.html            # app layout
      app.css               # visual design
      app.js                # canvas drawing and controls
```

## Run In VS Code

Open a terminal in this folder:

```powershell
C:\Users\johnm\Documents\ModelandSimulation
```

Run the app with your virtual environment Python:

```powershell
.\.venv\Scripts\python.exe run.py
```

Then open:

```text
http://127.0.0.1:8000
```

To start the server without automatically opening a browser tab:

```powershell
.\.venv\Scripts\python.exe run.py --no-browser
```

If Python is already added to PATH, this also works:

```powershell
python run.py
```

## What The App Simulates

- 36 student agents with immediate, locker-bound, task-bound, and peer-bound behaviors
- 1 instructor, 2 presiding assistants, and 2 custodians
- Current layout with lockers near the Back-Right exit
- Modified layout with lockers moved away from the exit path
- Door collisions, trips/falls, smoke slowdown, crowd density, and congestion heat
- Total evacuation time, agents still inside, evacuation rate chart, and side-by-side results

## Where To Modify Things

- Change evacuation rules, agents, obstacles, speeds, and layout constants in `comlab_v3/engine.py`.
- Change API behavior or server port in `comlab_v3/web.py`.
- Change the visual design in `comlab_v3/static/app.css`.
- Change drawing or UI interactions in `comlab_v3/static/app.js`.

## Validate And Benchmark

Run the validation tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the scenario validation and benchmark matrix:

```powershell
.\.venv\Scripts\python.exe scripts\validate_benchmark.py --iterations 100
```
