# ComLab V3 Simulation: Presentation & Defense Guide

This guide is explicitly tailored to the **CSE 10/L – Modeling and Simulation Presentation Requirements** rubric provided in your project documents. It provides the explanations, arguments, and data you need to successfully present and defend your simulation.

---

## 1. Introduction of the Project
* **Project Title:** ComLab V3 Emergency Egress Simulation
* **Brief Background:** This project simulates the emergency evacuation (egress) of a university computer laboratory (ComLab V3). It utilizes an Agent-Based Model (ABM) to simulate the individual behaviors of 36 students, 1 instructor, 2 assistants, and 2 custodians during a fire emergency.
* **Importance of the Study:** Evacuation efficiency is a matter of life and death. Traditional static floor plans cannot predict human behavior in a panic. By simulating panic, bottlenecks, and fire spread, we can scientifically validate whether a proposed layout change will actually save lives.

## 2. Problem Definition
* **The Problem Observed:** In the current layout of ComLab V3, student lockers and bag shelves are located near the main exit path (Back-Right). During an emergency, students naturally attempt to retrieve their belongings before evacuating, creating severe cross-traffic and bottlenecks at the most critical choke point in the room. 
* **Why it is Important:** Bottlenecks at exits lead to "crushes" or stampedes. If a fire starts near the exit or spreads quickly, students trapped in the locker queue are at high risk of smoke inhalation or burning.
* **What the Simulation Aims to Analyze:** The simulation tests a hypothesis: *Will moving the lockers away from the exit path to a "Modified" layout significantly reduce total evacuation time and exit queueing?*

## 3. Objectives of the Simulation
1. **Minimize Waiting Time:** Reduce the time agents spend queued at doors or trapped in aisles.
2. **Analyze Queue Performance:** Measure the exact length of queues forming at the front and back exits under panic conditions.
3. **Compare Operational Scenarios:** Directly benchmark the "Current" layout against the "Modified" layout across different fire origins (Data rack, Instructor desk, Television, etc.).
4. **Evaluate Human Factors:** Observe how panic, tripping, and smoke-fainting affect the throughput of the egress system.

## 4. System Model and Design
Our system uses a discrete-space (grid) and discrete-time (ticks) Agent-Based Model.
* **Entities:** The active decision-makers in the system. 
  - Students (with different behaviors: immediate, task-bound, peer-bound, locker-bound)
  - Instructors & Staff (who guide students or fetch extinguishers)
  - The Fire (acts as a spreading entity consuming cells)
* **Events:** Actions occurring at specific ticks.
  - *Fire Spread:* Evaluated every 7 ticks based on fuel weight.
  - *Trips / Faints:* Agents rolling a probability to fall down due to crowd density or smoke.
  - *Door Jams:* Collisions at unmanaged doors causing a temporary blockage.
* **Resources:** 
  - Front and Back Exits (limited capacity).
  - Fire Extinguishers.
  - Aisles / Walkways (spatial resources).
* **Queues:**
  - *Door Queues:* Agents waiting for the door cooldown to expire so they can exit.
  - *Aisle Queues:* Agents slowing down due to crowd congestion in narrow walkways.
* **State Variables:** 
  - `time` (current tick)
  - `agent.phase` (waiting, evacuating, tripped, fainted)
  - `agent.x` and `agent.y` (position)
  - `fire_intensity` and `density_map`

## 5. Assumptions and Input Data
Because real-life fire drills in the lab with actual fire are impossible, we rely on established crowd-dynamics assumptions:
* **Arrival Times (Pack-up Delays):** Instead of "arriving" into the system, agents "wake up" and start moving after a randomized delay. This simulates the time it takes to save work, grab a phone, or pack a bag. "Immediate" agents take 2-4 ticks; "Locker-bound" agents take 6-12 ticks.
* **Service Times (Movement Speed):** Base speed is $0.72$ cells/tick for students and $1.10$ cells/tick for staff. This is heavily constrained by the local `density_map`. If 3 or more agents are in the same cell, speed drops by $50\%$ to $62\%$ to simulate shuffling. 
* **Routing Heuristic:** Agents possess perfect knowledge of the room layout but will dynamically reroute using Manhattan-distance Breadth-First Search if a fire blocks their path.
* **Panic Factor:** Panic does not make people run faster; psychologically, it causes hesitation, pushes (stampedes), and irrational exit choices. We assumed a $43\%$-$61\%$ chance of door jamming if a door is not managed by a staff member and pressure rises.

## 6. Simulation Implementation (For your Demo)
*During your demonstration, make sure to highlight these technical aspects:*
* **Time Progression:** The simulation is tick-based. Explain that clicking "Step" moves time by 1 tick, updating all agent states sequentially.
* **Queue Handling:** Show how agents form a line at the door. Explain that `door_cooldown` prevents multiple agents from exiting simultaneously. If a custodian or assistant stands at the door, they "hold" it, smoothing the queue. If unmanaged, agents push, trigger a "Door Jam" event, and block the door for 3-5 steps.
* **Event Processing:** Show the event log on the UI. Point out when someone trips, faints from smoke, or when the fire spreads. 

## 7. Experimental Results and Analysis
*Memorize these metrics from your benchmarks to confidently answer questions.*
* **Throughput & Processing Time:** 
  - In the **Current** layout (Fire at Data Rack, Panic ON), it takes **180 seconds** to evacuate 41 people. Throughput is ~13.6 people/minute.
  - In the **Modified** layout, it takes only **71 seconds**. Throughput jumps to ~34.6 people/minute.
* **Average Waiting Time:** Dropped from **92.5 seconds** (Current) to **35.5 seconds** (Modified).
* **Trips and Door Hits:** In the current layout, cross-traffic caused by the locker placement led to **29 tripping incidents**. In the modified layout, it dropped to **7 incidents**.

## 8. Conclusion and Recommendations
* **Key Findings:** The simulation mathematically proves that placing lockers near the primary egress path causes severe fatal bottlenecks. Cross-traffic (students walking *against* the flow of traffic to get their bags) is the primary cause of crowd crush and tripping.
* **Insights Gained:** Even if a fire does not block an exit, the *panic* and *congestion* caused by bad furniture placement can delay evacuation long enough for smoke inhalation to become lethal.
* **Recommendations:** 
  1. The university must adopt the "Modified" layout and relocate the lockers away from the rear exit.
  2. Student assistants should be officially trained to "hold" doors during emergencies, as the simulation showed managed doors completely eliminated door jam collisions.

---

### Potential Defense Questions & Answers

**Q: Why did you use an Agent-Based Model (ABM) instead of a Mathematical Equation/System Dynamics?**
> *Answer:* Evacuations are highly dependent on individual spatial interactions. A simple equation can tell us the average flow rate of a door, but it cannot simulate a student walking backward against the crowd to grab their backpack, tripping, and causing a 5-person pileup. ABM allows us to model these emergent, individualized behaviors.

**Q: How do you know your simulation is accurate if you didn't test it with a real fire?**
> *Answer:* We use "Relative Validation." While we can't guarantee a real fire will take exactly 71 seconds to escape, the rules of physics and spatial geometry in our grid remain constant. Because both the Current and Modified layouts were subjected to the *exact same* mathematical rules, the *difference* between them (a 60% reduction in time) is highly reliable and valid for decision-making.

**Q: What pathfinding algorithm did you use?**
> *Answer:* We used a heuristic-driven Breadth-First Search (greedy BFS based on Manhattan distance). We recalculate paths dynamically if an agent encounters a fire or blocked edge, simulating a human's line-of-sight rerouting.
