# Defense Q&A Part 3: Fire & Environment Dynamics

This section covers the physical environment of ComLab V3, including fire physics, grid layout, and furniture placement.

## 1. Fire Simulation Physics

**Q: You use a Cellular Automata approach for fire spread. How does the fire know where to spread?**
> **Answer:** Fire spread is calculated every 7 ticks using a combination of adjacent cell availability and "fuel weights." Different furniture in the room has different combustibility. For instance, the data rack (full of servers and wires) has a fuel weight of 2.4, while an empty tile is 1.0. The probability of the fire expanding to a neighboring cell is a mathematical formula combining the fuel weight, the current heat of the room (tracked via a heatmap), and the suppression level if an extinguisher is being used.

**Q: In real life, smoke rises and fills a room, blocking visibility. Does your 2D grid account for 3D smoke dynamics?**
> **Answer:** No, our simulation is strictly 2D and does not calculate volumetric fluid dynamics or thermal stratification (smoke pooling at the ceiling). This is a limitation of our model. However, to compensate, we implemented a "heat/smoke proximity penalty." Agents within a certain Manhattan distance of the fire suffer severe speed penalties, simulating the difficulty of breathing and seeing through smoke, even if we aren't rendering the smoke in 3D.

## 2. Layout and The "Engineers" Question

**Q: As asked earlier: The original room layout was designed by engineers. Who are you to say it's wrong?**
> **Answer:** (Expanded) Building codes dictate minimums, not maximum efficiency. An engineer ensures a door is 36 inches wide to pass code. However, interior designers or IT staff often place furniture *after* the room is built. Placing student lockers next to the primary exit door creates an interactive hazard that engineers cannot predict on a blank blueprint. Our simulation doesn't critique the structural engineering; it critiques the *spatial utilization* and the interactive human behavior it triggers. We prove mathematically that moving the lockers resolves a deadly human-factors bottleneck.

**Q: In your Modified Layout, you placed the lockers at the front of the room. Why there?**
> **Answer:** Our data shows that cross-traffic (agents moving against the flow of the crowd to reach their lockers) is the primary cause of tripping and congestion. By moving the lockers to the front or sides, away from the primary egress funnel, students can retrieve their bags *before* merging into the main exit stream. This changes the traffic from conflicting cross-streams into a smooth, unified flow.

**Q: Does the size of your grid cells perfectly match reality?**
> **Answer:** We use an abstraction where 1 cell roughly equates to the personal space bubble of a moving human (around 0.5 to 0.8 square meters). While it is not millimeter-perfect, topological relationships matter more than exact measurements in ABMs. The fact that the aisle is 1 cell wide, and desks are blocks of cells, accurately replicates the restricted movement choices a human faces in the physical lab.
