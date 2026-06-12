import sys
sys.path.insert(0, '.')
from comlab_v3.engine import Simulation

sim = Simulation(mode="current", panic=True, fire_origin="data")
for step in range(1, 240):
    if sim.completed:
        break
    prev_pos = {a.agent_id: (a.x, a.y) for a in sim.agents}
    sim.step()
    for a in sim.agents:
        if a.exited:
            continue
        px, py = prev_pos[a.agent_id]
        # Check if student moved vertically (py != a.y) outside the center aisle (x not in {3, 8, 9, 10, 11, 12})
        if a.kind == "student" and py != a.y and a.x in {4, 5, 6, 7}:
            print(f"Step {sim.time}: Student {a.agent_id} moved vertically from ({px}, {py}) to ({a.x}, {a.y}) (target={a.target}, behavior={a.behavior}, phase={a.phase})")
