# Defense Q&A Part 4: Validation & Results

Panelists will scrutinize your results to ensure you didn't just invent numbers to prove your point.

## 1. Benchmarking and Metrics

**Q: You claim the Modified Layout is 60% faster. How do you know this isn't just an outlier from one lucky run?**
> **Answer:** We built a dedicated benchmarking script (`validate_benchmark.py`) that runs a matrix of scenarios headless (without the UI). We ran the simulation across multiple fire origins (Data rack, TV, Desk) and toggled Panic ON and OFF. Across all permutations, the Modified Layout consistently outperformed the Current Layout. Because the results hold true across dozens of varied parametric scenarios, we can confidently state it is a statistically significant improvement, not an outlier.

**Q: What is "Throughput" in your results, and why is it important?**
> **Answer:** Throughput is measured in "evacuated persons per minute." While total evacuation time is important, throughput tells us the efficiency of the exits. In the Current layout, throughput was roughly 13 persons/minute because people kept jamming the door. In the Modified layout, it reached 34 persons/minute. This metric isolates the performance of the door funnel itself, proving that the bottleneck was relieved.

**Q: What does the "Heatmap" metric track? Are you tracking literal fire heat?**
> **Answer:** We track two types of heat. "Fire intensity" tracks the actual hazard. But our "Heatmap" metric primarily tracks **Crowd Congestion Intensity**. Every tick, we add the density of a cell to its heatmap value. If a cell reaches a value of 900, it means an agent stood there for 900 ticks (or 9 agents stood there for 100 ticks). High heatmap numbers at the Back-Right door mathematically prove exactly where the crowd crushes are occurring.

## 2. Model Verification

**Q: How did you verify that your code works properly and has no bugs that skew the results?**
> **Answer:** We implemented **Verification** through automated unit testing (`test_engine.py`). Because the engine is deterministic, we wrote tests that run the simulation for a specific number of steps and assert that agent X is at exactly coordinate (Y, Z). If we change a core rule and it unintentionally breaks agent routing, the tests fail immediately. This guarantees that our pathfinding, door locking, and queueing logic work exactly as mathematically intended.

**Q: What is the difference between Verification and Validation in your study?**
> **Answer:** **Verification** asks "Did we build the model right?" We proved this via our unit tests and ensuring the Python code executes without bugs. **Validation** asks "Did we build the right model?" We validated the model by comparing its emergent behaviors (queues forming, bottlenecks at choke points, slower speeds in high density) against known real-world crowd dynamics principles. Since our simulated crowds behave like real crowds, the model is relatively valid.
