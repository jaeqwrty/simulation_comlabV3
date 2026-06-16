# Defense Q&A Part 2: Human Factors & Psychology

This section prepares you for questions from panelists focusing on the realism of the human behaviors programmed into your agents.

## 1. Panic and Hesitation

**Q: In your code, you mention that panic makes people slower. Shouldn't panic make people run faster to escape?**
> **Answer:** This is a common Hollywood misconception. In real disaster psychology, panic rarely manifests as sprinting; it usually manifests as "cognitive freeze" or normalcy bias, where people hesitate to accept the danger. In a confined room like a computer lab, if people do try to sprint, they immediately crash into each other. Therefore, our simulation models panic not as increased speed, but as increased *irrationality*: higher chances of door collisions, higher chances of tripping due to pushing, and random hesitation ticks where they simply freeze. 

**Q: How did you determine the "Pack-up delays" before an agent starts moving?**
> **Answer:** In egress studies, this is known as the "pre-movement time." When a fire alarm rings, students do not instantly teleport to the door. They save their code, shut down their PCs, grab their phones, and put on their backpacks. We assigned randomized delays based on behavioral types: "Immediate" agents react in 2-4 ticks. "Locker-bound" agents take 6-12 ticks to retrieve their heavy bags. This stagger is crucial because if everyone moved at tick 0, the bottleneck would be instantaneous. The stagger actually simulates realistic, chaotic human response times.

## 2. Tripping and Stampedes

**Q: You have mechanics for tripping and stampedes. How do you justify the probabilities you set for these events?**
> **Answer:** The probabilities are dynamically linked to crowd density. An agent walking alone in a hallway has near-zero chance of tripping. However, if an agent is in the center aisle, and the local density map shows 4 or 5 agents occupying adjacent spaces (simulating a crowd crush), the trip probability multiplies significantly. If panic is enabled, the chance multiplies again. This directly mirrors real-world physics where high-density crowd pressure causes people to lose their footing, leading to pile-ups.

**Q: Why do agents sometimes "faint" in the simulation?**
> **Answer:** Smoke inhalation is historically the leading cause of death in structural fires, not the flames themselves. Our fire origin radiates heat and smoke. If agents are trapped in a bottleneck within 2 cells of the fire origin for too long, they roll a probability to "faint" from smoke inhalation. This requires other agents to step around them, further slowing the evacuation and punishing layouts that force people to queue near the fire source.

## 3. Staff and Roles

**Q: Why do instructors and student assistants behave differently than students?**
> **Answer:** In emergency protocols, designated staff are trained to manage evacuations. Our simulation reflects this. While students pathfind directly to the exits or lockers, the Instructor is programmed to pathfind to the fire extinguisher. The Student Assistants and Custodians are programmed to move to the doorways to "hold the doors." 

**Q: What is the mechanical effect of a staff member "holding" a door?**
> **Answer:** It drastically changes the flow dynamics. An unmanaged door has a high probability of "Door Jams"—where two or three panicked students try to squeeze through simultaneously, wedging themselves and blocking the exit for 3-5 ticks. If an Assistant is stationed at the door, they enforce single-file movement. The throughput becomes slightly slower but entirely consistent (1 person per tick), eliminating jams completely. This proves the value of trained emergency wardens.
