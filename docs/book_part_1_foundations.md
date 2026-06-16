# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 1: The Foundations of Agent-Based Modeling (ABM)

### 1.1 Introduction to the V3 Architecture
The Computer Lab Simulation V3 is not merely a pathfinding demo; it is a full-fledged Agent-Based Model (ABM). At its core, an ABM attempts to recreate complex macroscopic phenomena (such as a crowd crush, an orderly evacuation, or a chaotic panic) by defining simple, localized rules for autonomous entities (the "agents"). 

In the context of the Computer Lab Simulation V3, the macro-phenomenon we are studying is the egress behavior of students and a professor during an emergency (a fire). The micro-rules involve:
- Perception (Is there fire nearby? Where is the nearest exit?)
- Movement (Can I step forward? Is my path blocked?)
- State Transitions (Am I panicking? Did I trip? Am I fainted?)

---

### 1.2 Determinism in Simulation
A core design philosophy of V3 is **Determinism**. Unlike stochastic models that rely heavily on random numbers generated at runtime (which makes replicating edge cases incredibly difficult), V3 employs a seeded PRNG (Pseudo-Random Number Generator) approach where each agent carries its own `seed`, and the global state is fully reproducible.
If you run V3 with the exact same initial positions, seed values, and map configuration, you will get the exact same frame-by-frame outcome. This is crucial for:
1. **Validation**: We can confidently state that fixing a bug in the pathfinding actually fixed it, without worrying that random noise masked the bug.
2. **Analysis**: We can measure the exact impact of widening a door by 1 cell, because all other variables remain identical.

---

### 1.3 Time and Space Discretization
To make the computation feasible in real-time within a web environment (and manageable in Python), space and time are discretized:
- **Spatial Discretization**: The environment is broken into a 2D Grid. Each cell typically represents a 0.5m x 0.5m area, which is roughly the shoulder width of a single human. Rather than enforcing rigid blocking where only one person can occupy a cell, V3 uses a density-dependent crowd congestion model. Multiple agents can share a cell, but they suffer severe speed penalties, representing friction and crowding.
- **Temporal Discretization**: Time moves in "ticks" or "frames". Unlike continuous-time simulations that solve differential equations for movement, V3 evaluates the world frame-by-frame. During each frame, agents accrue "speed bank" (representing fractional movement) and execute a step when their bank overflows 1.0.

---

### 1.4 Why Python + Web Stack?
The engine is written in Python, offering rapid iteration, excellent data structure support (dataclasses, typing), and a robust ecosystem for future data analysis. However, Python is not ideal for rendering 60FPS UI directly in a browser. Thus, the V3 architecture introduces a decoupled approach:
- **The Engine (Backend)**: Computes the physics, pathfinding, and states.
- **The API Layer**: Serves the state changes as JSON objects over REST endpoints (served via Python's standard `http.server`).
- **The Frontend (Web)**: Dumbs down the rendering, acting purely as a "dumb terminal" that paints the JSON state onto an HTML5 Canvas.

This separation of concerns ensures that the simulation can be run headlessly on a powerful server for Monte Carlo analysis, while any client can visualize the results.
