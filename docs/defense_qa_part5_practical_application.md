# Defense Q&A Part 5: Practical Applications & Limitations

Panelists want to see the real-world value of your research and whether you understand the limits of what you have built.

## 1. Recommendations and Real-World Impact

**Q: Okay, you've proved the lockers should be moved. What are your specific, actionable recommendations for the university?**
> **Answer:** We have three distinct recommendations:
> 1. **Physical:** Relocate the lockers from the rear exit to the front wall or hallway immediately. Our data shows this single change saves over 100 seconds in a panic scenario.
> 2. **Protocol:** Instructors must formally assign Student Assistants to be "Door Holders" during an emergency. The simulation showed that managed doors eliminate the door jam probability (which is $43\%$-$61\%$ under panic conditions without door-holders), smoothing the queue and preventing pile-ups.
> 3. **Awareness:** Use the visual playback of our simulation to train students during orientation, showing them exactly how crowding the rear door leads to danger, encouraging use of the front exit.

**Q: Could this simulation engine be used for other rooms in the university?**
> **Answer:** Absolutely. The engine was designed with a decoupled architecture. The core logic (`engine.py`) is completely independent of the visual UI. By simply altering the coordinate definitions inside `engine.py`, this exact engine can simulate different room configurations.

---

## 2. Limitations

**Q: What is the biggest weakness of your simulation?**
> **Answer:** The biggest weakness is the lack of physical mass and shoving dynamics. Because it is a grid-based model, multiple agents can mathematically occupy the same cell coordinate (suffering speed and safety penalties) but we do not physically simulate the kinetic friction and physical force of bodies pressing against one another. In real life, three panicked people might wedge their physical bodies into a doorway, causing a structural arch that requires immense physical force to break. We abstract this using random "door jam" cooldown ticks, but we do not physically simulate the kinetic friction of bodies. 

**Q: You assumed that people will go to their lockers. What if the fire alarm is so loud they just run?**
> **Answer:** That is a valid behavioral variable. If 100% of students ignore their bags, the Current Layout performs slightly better than our worst-case scenario. However, post-incident analyses of school emergencies consistently show that a significant percentage of students *will* attempt to retrieve their phones and bags, regardless of alarms. Our simulation includes a randomized parameter (`locker_rate`) that assigns this behavior to only a percentage of students. Even if only 30% of students go to the lockers, the cross-traffic they create is enough to disrupt the entire evacuation flow. 

**Q: Your layout is 2D. Does it account for stairs?**
> **Answer:** Currently, the simulation terminates when an agent successfully reaches the hallway exit node. We do not simulate the vertical descent down the stairwells, which is a known secondary bottleneck. Future iterations of this project could expand the grid to include stairwell speed penalties and merging traffic from other floors.
