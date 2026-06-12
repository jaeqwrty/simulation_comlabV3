from comlab_v3.engine import Simulation

for mode in ("current", "modified"):
    sim = Simulation(mode, panic=False, fire_origin="desk")
    print(f"\n--- Running {mode} mode ---")
    while not sim.completed:
        sim.step()
    print(f"{mode} layout completed in {sim.time} steps. Total trips: {sim.trips}, Door collisions: {sim.door_collisions}")
    # Print the last few steps and who was left
    sim = Simulation(mode, panic=False, fire_origin="desk")
    for _ in range(240):
        active = [a for a in sim.agents if not a.exited]
        if sim.time >= 20:
            print(f"[{mode}] Step {sim.time} ({len(active)} active): {[f'{a.agent_id} ({a.kind}, {a.behavior}) at ({a.x},{a.y}) to {a.target} (wait={a.wait_until})' for a in active]}")
        if sim.completed:
            break
        sim.step()
    print(f"Final Step {sim.time}")
