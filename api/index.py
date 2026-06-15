"""Vercel serverless API for the ComLab V3 simulation."""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from comlab_v3.engine import (
    BACK_EXIT,
    CELL,
    COLS,
    CURRENT_LOCKER,
    FIRE_LOCATION_LABELS,
    FRONT_EXIT,
    HALL_COLS,
    HALLWAY_WALL,
    LAB_COLS,
    MODIFIED_LOCKER,
    ROWS,
    Simulation,
)


class VercelSimulationService:
    """Request-driven simulation state for serverless deployments."""

    def __init__(self):
        self.lock = RLock()
        self.mode = "current"
        self.panic = True
        self.fire_origin = "data"
        self.speed = 1.5
        self.running = False
        self.last_tick = time.monotonic()
        self.sim = Simulation(self.mode, self.panic, self.fire_origin)

    def apply_config(self, config: dict[str, Any] | None):
        if not config:
            return
        self.mode = config.get("mode", self.mode)
        self.panic = bool(config.get("panic", self.panic))
        self.fire_origin = config.get("fireOrigin", self.fire_origin)
        self.speed = float(config.get("speed", self.speed))
        self.sim.panic = self.panic

    def tick(self):
        if not self.running or self.sim.completed:
            self.last_tick = time.monotonic()
            return

        now = time.monotonic()
        interval = max(0.035, 0.34 / max(0.1, self.speed))
        steps = min(12, int((now - self.last_tick) / interval))
        if steps <= 0:
            return

        for _ in range(steps):
            if self.sim.completed:
                break
            self.sim.step()
        self.last_tick = now

    def reset(self, config: dict[str, Any] | None = None):
        with self.lock:
            self.apply_config(config)
            self.running = False
            self.last_tick = time.monotonic()
            self.sim = Simulation(self.mode, self.panic, self.fire_origin)
            return self.state()

    def control(self, action: str, config: dict[str, Any] | None = None):
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
            self.last_tick = time.monotonic()
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
        self.tick()
        sim = self.sim
        active = sum(1 for agent in sim.agents if not agent.exited)
        summary = sim.summary()
        return {
            "running": self.running,
            "mode": self.mode,
            "panic": self.panic,
            "fireOrigin": self.fire_origin,
            "fireCells": sorted(sim.active_fire_cells),
            "speed": self.speed,
            "time": sim.time,
            "active": active,
            "inside": active,
            "evacuated": len(sim.agents) - active,
            "casualties": summary.get("casualties", 0),
            "totalAgents": len(sim.agents),
            "trips": sim.trips,
            "doorCollisions": sim.door_collisions,
            "fireDamage": sim.fire_damage,
            "maxHeat": summary["max_heat"],
            "avgWait": summary["average_wait_time"],
            "avgQueueLength": summary["average_queue_length"],
            "throughputPerMinute": summary["throughput_per_minute"],
            "exitUtilizationPercent": summary["exit_utilization_percent"],
            "processingTime": summary["processing_time"],
            "completed": sim.completed,
            "agents": [
                {
                    "id": agent.agent_id,
                    "kind": agent.kind,
                    "behavior": agent.behavior,
                    "role": role_for_agent(agent),
                    "x": agent.x,
                    "y": agent.y,
                    "target": agent.target,
                    "phase": agent.phase,
                    "exited": agent.exited,
                    "stamped_until": agent.stamped_until,
                }
                for agent in sim.agents
            ],
            "heatmap": sim.heatmap,
            "rate": sim.rate[-120:],
            "events": sim.events[:40],
            "layout": layout_payload(self.mode, self.fire_origin),
        }


SERVICE = VercelSimulationService()


def role_for_agent(agent) -> str:
    roles = {
        "I01": "Professor / extinguisher lead",
        "PA1": "Front exit door holder",
        "PA2": "Back exit door holder",
        "LC1": "Fire response / front student aide",
        "LC2": "Fire response / back student aide",
    }
    return roles.get(agent.agent_id, agent.behavior)


def layout_payload(mode: str, fire_origin: str):
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
        "storage": sim.storage,
        "frontExit": FRONT_EXIT,
        "backExit": BACK_EXIT,
        "frontStairs": None,
        "emergencyStairs": None,
        "currentLocker": CURRENT_LOCKER,
        "modifiedLocker": MODIFIED_LOCKER,
        "locker": sim.locker,
        "fireOrigin": sim.fire_origin,
        "fireCells": sorted(sim.active_fire_cells),
        "fireLocations": FIRE_LOCATION_LABELS,
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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/api", "/api/", "/api/state"}:
            self.send_json(SERVICE.state())
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self.read_json()

        if path == "/api/control":
            self.send_json(SERVICE.control(payload.get("action", "pause"), payload.get("config")))
        elif path == "/api/reset":
            self.send_json(SERVICE.reset(payload))
        elif path == "/api/compare":
            self.send_json(SERVICE.compare())
        else:
            self.send_error(404)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, data):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
