import sys
sys.path.insert(0, '.')
from comlab_v3.engine import Simulation

sim = Simulation(mode="modified", panic=True, fire_origin="data")
for step in range(1, 240):
    sim.step()
    for a in sim.agents:
        if a.agent_id == "S01":
            print(f"Step {sim.time}: S01 at ({a.x}, {a.y}), target={a.target}, path_len={len(a.path)}, exited={a.exited}, wait={a.wait_until}, trip={a.trip_until}, speed_bank={a.speed_bank:.3f}")
            density = sim.density_map()
            print(f"  choose_exit={sim.choose_exit(a, density)}, should_route={sim.target_for(a, density)}")
