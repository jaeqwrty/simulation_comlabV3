# ComLab V3 Emergency Egress Simulation

Agent-based micro-simulation for the revised ComLab V3 evacuation proposal.

The model represents:

- 36 students in a 6-row workstation layout
- 1 instructor
- 2 presiding assistants
- 2 lab custodians
- locker detours near the back-right exit
- task and peer delays
- smoke slowdown from Data Communications racks
- trip/fall blockages in tight rows
- outward-swinging door conflicts
- hallway backpressure from nearby laboratories and two staircase directions

## Files

- `comlab_v3_sim.py` - reusable simulation engine
- `ComLab_V3_Evacuation_Simulation.ipynb` - Google Colab-ready notebook
- `requirements.txt` - Python package list for local/Colab use

## Run Locally

```powershell
python comlab_v3_sim.py
```

If Python is not on your PATH, run it in Google Colab by uploading the notebook and module.

## Main Scenarios

- `orderly_fire_drill`
- `panicked_electrical_fire`
- `no_locker_detour`
- `assigned_exits`
- `custodians_hold_doors`

Each scenario reports evacuation time, bottleneck density, trip count, door collision count, and instructor extinguisher retrieval time.

## 2D Agent-Based View

Watch one layout:

```powershell
python run_2d_simulation.py --layout current
python run_2d_simulation.py --layout modified
```

Compare current vs modified layout side by side:

```powershell
python compare_layouts.py
```

Save the comparison as a GIF:

```powershell
python compare_layouts.py --save layout_comparison.gif
```
