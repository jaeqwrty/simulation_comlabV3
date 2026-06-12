import sys
sys.path.insert(0, '.')
from comlab_v3.engine import Simulation

def trace_sim(mode):
    sim = Simulation(mode=mode, panic=False, fire_origin="desk")
    evac_times = {}
    while not sim.completed:
        sim.step()
        for a in sim.agents:
            if a.exited and a.agent_id not in evac_times:
                evac_times[a.agent_id] = sim.time
    return sim.time, evac_times

current_time, current_evac = trace_sim("current")
modified_time, modified_evac = trace_sim("modified")

print(f"Current Time: {current_time}s")
print(f"Modified Time: {modified_time}s")
print("\nEvacuation times comparison (Agent: Current -> Modified):")
all_ids = sorted(list(current_evac.keys() | modified_evac.keys()))
for aid in all_ids:
    c_t = current_evac.get(aid, "N/A")
    m_t = modified_evac.get(aid, "N/A")
    diff = ""
    if isinstance(c_t, int) and isinstance(m_t, int):
        diff = f" ({m_t - c_t:+}s)"
    print(f"Agent {aid}: {c_t}s -> {m_t}s{diff}")
