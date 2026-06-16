# Defense Q&A Part 1: Core Methodology & Architecture

This section covers questions panelists will ask to verify you understand the computer science fundamentals behind your simulation approach.

## 1. Choice of Simulation Model

**Q: Why did you choose an Agent-Based Model (ABM) over a System Dynamics (SD) or Mathematical Flow model?**
> **Answer:** System Dynamics models are excellent for macro-level flow—treating people like water in a pipe. However, in an emergency egress scenario within a confined room, micro-level interactions are the primary cause of bottlenecks. An ABM allows us to simulate individual heterogeneity: one student running for the exit, another student walking backwards against the flow to grab their backpack from a locker, and another student hesitating in panic. Mathematical flow models cannot capture the emergent chaos of cross-traffic and tripping, which ABMs handle perfectly.

**Q: Could you have used a Continuous Space model (like a 3D physics engine) instead of a Discrete Grid? Why use a grid?**
> **Answer:** We could have, but it would be computationally inefficient and wouldn't significantly improve the accuracy of our specific metrics. A discrete grid where each cell represents a $0.5\text{m} \times 0.5\text{m}$ area perfectly maps to the physical shoulder width of a standing human. A grid-based approach is an industry-standard in egress simulation because it drastically reduces pathfinding complexity while still producing highly accurate queueing and bottleneck behavior.

---

## 2. Pathfinding and Algorithms

**Q: Explain your pathfinding algorithm. Why Breadth-First Search (BFS) with Manhattan distance?**
> **Answer:** Our agents need to navigate a 2D grid with obstacles and dynamic threats (fire). Because the edge weights are uniform (moving from one cell to an adjacent cell always costs 1 step), Dijkstra's algorithm degrades into BFS. We use a greedy BFS sorted by Manhattan distance because agents cannot move diagonally through desks. A* could be used, but since our distances are extremely short (max 15-20 cells) and the heuristic is perfectly admissible, our greedy BFS is mathematically equivalent and highly optimized for Python to recalculate paths dynamically on the fly.

**Q: What happens if the fire blocks the only path to the exit? Does your algorithm crash?**
> **Answer:** No. When an agent's intended path is blocked by a new fire cell, the simulation invalidates their cached path. The BFS algorithm will attempt to find an alternate route. If no route exists (all exits are cut off), the algorithm returns an empty path. The agent will then remain stationary, and if the fire overtakes them, they become a casualty. The algorithm is robust against impossible paths.

---

## 3. The "Deterministic" Approach & Collision Resolution

**Q: You mentioned your simulation uses seeds and is "deterministic." Doesn't that mean your results are fixed and therefore not representative of random real-world chaos?**
> **Answer:** Determinism is a requirement for strict scientific comparison, not a flaw. Chaos is still present—agents have randomized panic, randomized pack-up delays, and randomized trip chances. However, by using a pseudo-random number generator bound to specific *seeds*, we ensure that if we run the simulation on the "Current" layout, and then run it on the "Modified" layout, the exact same students will trip or panic at the exact same statistical intervals. This isolates the variable: any change in the evacuation time is *100% caused by the layout change*, not by a lucky or unlucky random dice roll. To get a holistic view, we run the simulation over multiple replications with different seeds (Monte Carlo method).

**Q: How do you handle multiple agents trying to move into the same cell at the exact same tick?**
> **Answer:** The engine iterates through the agents sequentially based on their initialization order. To prevent lock-ups on a discrete grid, the simulation permits multiple agents to occupy the same cell coordinate. However, crowd crowding is mathematically penalized: the engine checks local cell density, and if a cell contains multiple agents, their movement speed budget (`speed_bank` accrual) drops significantly (down to $38\%$ speed for density $\ge 5$). Tripping and smoke-fainting chances also scale up with density. This density-dependent velocity function naturally forms physical queues and exit bottlenecks without requiring complex collision physics.
