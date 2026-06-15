"""FastAPI server for the ComLab V3 simulation UI."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .engine import Simulation
from .grid import (
    BACK_EXIT, CELL, COLS, CURRENT_LOCKER, DATA_RACKS, EMERGENCY_STAIRS,
    EXTINGUISHER_ASSISTANT, EXTINGUISHER_ENTRANCE, EXTINGUISHER_EXIT,
    EXTINGUISHER_PROFESSOR, EXTINGUISHER_SHELVES, FIRE_EXTINGUISHERS,
    EXTRA_PCS, FRONT_EXIT, FRONT_STAIRS, HALL_COLS, HALLWAY_WALL,
    INSTRUCTOR_DESK, LAB_COLS, MODIFIED_LOCKER, ROWS,
    SERVICE_BAY_PASSAGE, SHELVES, STUDENT_ASSISTANT_DESK,
)
from .models import ControlAction, ResetRequest


STATIC_DIR = Path(__file__).parent / "static"


def role_for_agent(agent) -> str:
    roles = {
        "I01": "Professor / extinguisher lead",
        "PA1": "Front aisle student aide",
        "PA2": "Back aisle student aide",
        "LC1": "Front exit door holder",
        "LC2": "Back exit door holder",
    }
    return roles.get(agent.agent_id, agent.behavior)


def layout_payload(mode: str, fire_origin: str) -> dict[str, Any]:
    sim = Simulation(mode, fire_origin=fire_origin)
    return {
        "rows": ROWS,
        "cols": COLS,
        "labCols": LAB_COLS,
        "hallCols": HALL_COLS,
        "workstations": sim.workstations,
        "workstationRows": sim.workstation_rows,
        "instructorDesk": sorted(sim.instructor_desk),
        "dataRacks": sorted(sim.data_racks),
        "studentAssistantDesk": sorted(sim.student_assistant_desk),
        "extraPcs": sorted(sim.extra_pcs),
        "shelves": sorted(sim.shelves),
        "frontExit": FRONT_EXIT,
        "backExit": BACK_EXIT,
        "frontStairs": FRONT_STAIRS,
        "emergencyStairs": EMERGENCY_STAIRS,
        "currentLocker": CURRENT_LOCKER,
        "modifiedLocker": MODIFIED_LOCKER,
        "locker": sim.locker,
        "fireOrigin": sim.fire_origin,
        "cell": CELL,
        "hallwayWall": sorted(HALLWAY_WALL),
        "partitionWall": sorted(sim.partition_wall),
        "serviceBayPassage": sim.service_bay_passage,
        "extinguisherExit": sim.extinguisher_exit,
        "extinguisherEntrance": sim.extinguisher_entrance,
        "extinguisherProfessor": sim.extinguisher_professor,
        "extinguisherAssistant": sim.extinguisher_assistant,
        "extinguisherShelves": sim.extinguisher_shelves,
        "fireExtinguishers": list(sim.fire_extinguishers),
    }


class SimulationService:
    """Thread-safe wrapper around the simulation engine."""

    def __init__(self):
        self.lock = threading.RLock()
        self.mode = "current"
        self.panic = True
        self.fire_origin = "data"
        self.speed = 1.5
        self.running = False
        self.sim = Simulation(self.mode, self.panic, self.fire_origin)
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def _loop(self):
        while True:
            with self.lock:
                should_step = self.running and not self.sim.completed
                speed = self.speed
            if should_step:
                with self.lock:
                    self.sim.step()
                time.sleep(max(0.035, 0.34 / speed))
            else:
                time.sleep(0.08)

    def apply_config(self, config):
        if not config:
            return
        self.mode = config.mode if config.mode is not None else self.mode
        self.panic = config.panic if config.panic is not None else self.panic
        self.fire_origin = config.fireOrigin if config.fireOrigin is not None else self.fire_origin
        self.speed = config.speed if config.speed is not None else self.speed
        
        if hasattr(self, "sim") and self.sim:
            self.sim.panic = self.panic

    def reset(self, config=None):
        with self.lock:
            self.apply_config(config)
            self.running = False
            self.sim = Simulation(self.mode, self.panic, self.fire_origin)
            return self.state()

    def control(self, action: str, config=None):
        with self.lock:
            self.apply_config(config)
            if action == "start":
                self.running = True
            elif action == "pause":
                self.running = False
            elif action == "step":
                self.running = False
                self.sim.step()
            elif action == "reset":
                self.running = False
                self.sim = Simulation(self.mode, self.panic, self.fire_origin)
            return self.state()

    def compare(self):
        with self.lock:
            panic = self.panic
            fire_origin = self.fire_origin

        result = {}
        for mode in ("current", "modified"):
            sim = Simulation(mode, panic, fire_origin)
            while not sim.completed:
                sim.step()
            result[mode] = sim.summary()
        return result

    def state(self):
        sim = self.sim
        agents = [
            {
                "id": agent.agent_id,
                "kind": agent.kind,
                "behavior": agent.behavior,
                "role": role_for_agent(agent),
                "x": agent.x,
                "y": agent.y,
                "phase": agent.phase,
                "exited": agent.exited,
                "stamped_until": agent.stamped_until,
            }
            for agent in sim.agents
        ]
        active = sum(1 for agent in sim.agents if not agent.exited)
        return {
            "running": self.running,
            "mode": self.mode,
            "panic": self.panic,
            "fireOrigin": self.fire_origin,
            "speed": self.speed,
            "time": sim.time,
            "active": active,
            "evacuated": len(sim.agents) - active,
            "totalAgents": len(sim.agents),
            "trips": sim.trips,
            "doorCollisions": sim.door_collisions,
            "maxHeat": max(sim.heatmap.values(), default=0),
            "completed": sim.completed,
            "agents": agents,
            "heatmap": sim.heatmap,
            "rate": sim.rate[-120:],
            "events": sim.events[:40],
            "layout": layout_payload(self.mode, self.fire_origin),
        }


SERVICE = SimulationService()

app = FastAPI(title="ComLab V3 Simulation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/state")
def get_state():
    return SERVICE.state()

@app.post("/api/control")
def post_control(payload: ControlAction):
    return SERVICE.control(payload.action, payload.config)

@app.post("/api/reset")
def post_reset(payload: ResetRequest):
    return SERVICE.reset(payload.config)

@app.post("/api/compare")
def post_compare():
    return SERVICE.compare()

# Static file routing
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_index():
    return FileResponse(STATIC_DIR / "index.html")

