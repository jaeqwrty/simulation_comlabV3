# Comprehensive Defense Questions & Answers

Panelists during a thesis or project defense will often try to challenge your assumptions, your methodology, and the real-world applicability of your simulation. Below are the most likely and challenging questions you might face, along with strong, academic ways to answer them.

---

## 1. Layout & Architecture Justification

**Q: "The original room layout was likely designed by professional architects or engineers following building codes. What gives you the authority to say it's wrong or inefficient?"**
> **Answer:** Building codes and architects design primarily for *daily utility, capacity, and spatial efficiency*, ensuring the room meets the minimum legal exit requirements. However, standard building codes do not account for behavioral psychology—specifically, the fact that students in a computer lab will universally attempt to retrieve their belongings from the locker area before fleeing. Our simulation doesn't claim the engineers built an illegal room; it proves that the *interaction* between the furniture placement (lockers near the exit) and *human behavior* creates an unpredicted bottleneck that severely compromises safety.

**Q: "If you move the lockers to the front or side of the room (Modified Layout), won't that just create a bottleneck *entering* the room during normal day-to-day operations?"**
> **Answer:** That is a valid tradeoff. Moving the lockers might make the start of a class slightly more congested as students put their bags away. However, in day-to-day operations, there is no lethal threat, no panic, and time is not a matter of life and death. We are prioritizing emergency egress efficiency over minor daily convenience.

---

## 2. Model Validity & Assumptions

**Q: "How can you prove your evacuation times (e.g., 71 seconds vs 180 seconds) are accurate if you haven't burned down a room or conducted a real-life panic drill?"**
> **Answer:** This is a classic challenge in simulation modeling. We rely on **Relative Validation** rather than Absolute Validation. While we cannot guarantee that a real-life evacuation will take exactly 71.0 seconds, both the Current and Modified layouts were evaluated using the exact same mathematical rules, speeds, and panic variables. Because the environmental rules are constant, the *drastic difference* (over a 60% reduction in evacuation time and a 75% reduction in tripping incidents) is scientifically valid proof that the modified layout is vastly superior, regardless of whether the baseline time is perfectly true to life.

**Q: "Why did you choose a grid-based Cellular/Agent-Based Model instead of a continuous 3D physics engine (like Unity)?"**
> **Answer:** For macro-level crowd dynamics and pathfinding, continuous 3D physics engines are overly computationally expensive and introduce unnecessary complexities (like polygon clipping). A discrete grid-based ABM (where 1 cell = $0.5\text{m} \times 0.5\text{m}$) is the industry standard for egress modeling (similar to software like Pathfinder or FDS+Evac). It perfectly captures the critical metrics we need: spatial occupation, bottlenecks, and queueing theory, without the overhead of rendering 3D physics.

**Q: "Where did you get your data for agent speed, pack-up delays, and tripping probabilities?"**
> **Answer:** These parameters are inspired by established crowd-dynamics literature. Standard walking speed in egress models is often set around 1.2 to 1.5 m/s, which we map to our grid ticks (base speed of $0.72$ cells/tick for students and $1.10$ cells/tick for staff). Pack-up delays reflect psychological "pre-movement times" observed in fire safety studies. We used educated heuristic estimates to represent relative delays. The exact milliseconds matter less than the *distribution* of delays—some people react immediately, some hesitate, and some must pack up, creating realistic stagger in crowd flow.

---

## 3. Agent Behavior & AI

**Q: "Why do you use Manhattan Distance for pathfinding instead of a more advanced algorithm like A* or Dijkstra's?"**
> **Answer:** In a discrete grid where agents can only move in 4 cardinal directions (Up, Down, Left, Right) and edge weights are uniform, a greedy Breadth-First Search (BFS) using Manhattan distance is mathematically identical in outcome to A*, but computationally lighter. Since we have dozens of agents recalculating paths dynamically as the fire spreads, BFS provides the perfect balance of realistic "line-of-sight" human pathfinding and computational efficiency.

**Q: "Do your agents know where the fire is? Because in real life, a student in the back might not see a fire starting in a data rack."**
> **Answer:** Our agents do have immediate awareness of the fire once it starts, acting as if someone shouted "Fire!" or an alarm went off. However, their pathfinding is realistic—they don't automatically know the perfect route out. If a fire blocks their intended path, they hit the obstacle and their path recalculates. We also simulate "smoke proximity": if they get too close to the fire, their speed drops and they have a high chance of fainting, accurately modeling the danger of smoke inhalation even if they know the fire is there.

**Q: "Why do some agents just stand there or 'hesitate' while a fire is spreading?"**
> **Answer:** This accurately models human psychology during emergencies. Studies on disaster response show that panic does not always result in immediate running; it often causes "normalcy bias" or "cognitive freeze." Our simulation specifically assigns a `panic_prone` boolean to a subset of agents, making them occasionally skip their movement turns (hesitation) or take longer to pack up, making the simulation highly realistic compared to models where everyone acts like a perfect robot.

---

## 4. Systems and Architecture

**Q: "Your simulation is deterministic (using seeds). Doesn't that mean the results are rigged to be the same every time?"**
> **Answer:** Determinism in modeling is a feature, not a bug. By using fixed random seeds, we ensure that the simulation is 100% reproducible. If we change a layout rule and see the evacuation time drop, we know with absolute certainty that the *layout change* caused the improvement, not just a lucky random dice roll. If we want to see different outcomes, we simply run a batch of tests with different seeds (a Monte Carlo simulation approach) to find the average.

**Q: "What are the limitations of your study? What does your simulation fail to account for?"**
> **Answer:** 
> 1. The simulation operates in 2D, so it cannot account for vertical smoke stratification (smoke rising to the ceiling before descending).
> 2. We assume a static fire fuel weight based on furniture. A real fire's spread is heavily influenced by HVAC systems and airflow, which our grid model does not calculate.
> 
> *Note:* However, we successfully modeled individual physical mobility limitations by assigning each student a randomized `mobility_factor` (between $0.78$ and $1.10$) that scales their base speed.
