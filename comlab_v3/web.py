"""Python HTTP server for the ComLab V3 simulation UI."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlparse
import webbrowser

from .engine import (
    BACK_EXIT,
    CELL,
    COLS,
    CURRENT_LOCKER,
    DATA_RACKS,
    EMERGENCY_STAIRS,
    EXTINGUISHER_ASSISTANT,
    EXTINGUISHER_ENTRANCE,
    EXTINGUISHER_EXIT,
    EXTINGUISHER_PROFESSOR,
    EXTINGUISHER_SHELVES,
    FIRE_EXTINGUISHERS,
    FIRE_LOCATION_LABELS,
    EXTRA_PCS,
    FRONT_EXIT,
    FRONT_STAIRS,
    HALL_COLS,
    HALLWAY_WALL,
    INSTRUCTOR_DESK,
    LAB_COLS,
    MODIFIED_LOCKER,
    PARTITION_WALL,
    ROWS,
    SERVICE_BAY_PASSAGE,
    SHELVES,
    STUDENT_ASSISTANT_DESK,
    WORKSTATION_ROWS,
    WORKSTATIONS,
    Simulation,
    fire_origin_for,
    locker_for,
)


HOST = "127.0.0.1"
PORT = 8000
STATIC_DIR = Path(__file__).with_name("static")


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

    def apply_config(self, config: dict | None):
        if not config:
            return
        self.mode = config.get("mode", self.mode)
        self.panic = bool(config.get("panic", self.panic))
        self.fire_origin = config.get("fireOrigin", self.fire_origin)
        self.speed = float(config.get("speed", self.speed))
        
        if hasattr(self, "sim") and self.sim:
            self.sim.panic = self.panic

    def reset(self, config: dict | None = None):
        with self.lock:
            self.apply_config(config)
            self.running = False
            self.sim = Simulation(self.mode, self.panic, self.fire_origin)
            return self.state()

    def control(self, action: str, config: dict | None = None):
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
                "target": agent.target,
                "phase": agent.phase,
                "exited": agent.exited,
                "stamped_until": agent.stamped_until,
            }
            for agent in sim.agents
        ]
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
            "agents": agents,
            "heatmap": sim.heatmap,
            "rate": sim.rate[-120:],
            "events": sim.events[:40],
            "layout": layout_payload(self.mode, self.fire_origin),
        }


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
        "frontStairs": FRONT_STAIRS,
        "emergencyStairs": EMERGENCY_STAIRS,
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


SERVICE = SimulationService()


def role_for_agent(agent) -> str:
    roles = {
        "I01": "Professor / extinguisher lead",
        "PA1": "Front exit door holder",
        "PA2": "Back exit door holder",
        "LC1": "Fire response / front student aide",
        "LC2": "Fire response / back student aide",
    }
    return roles.get(agent.agent_id, agent.behavior)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request_path = urlparse(self.path).path
        if request_path == "/":
            self.send_static("index.html", "text/html; charset=utf-8")
        elif request_path == "/app.css":
            self.send_static("app.css", "text/css; charset=utf-8")
        elif request_path == "/app.js":
            self.send_static("app.js", "text/javascript; charset=utf-8")
        elif request_path == "/api/state":
            self.send_json(SERVICE.state())
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = {}
        if length:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))

        if self.path == "/api/control":
            self.send_json(SERVICE.control(payload.get("action", "pause"), payload.get("config")))
        elif self.path == "/api/reset":
            self.send_json(SERVICE.reset(payload))
        elif self.path == "/api/compare":
            self.send_json(SERVICE.compare())
        else:
            self.send_error(404)

    def send_json(self, data):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_static(self, filename: str, content_type: str):
        path = STATIC_DIR / filename
        encoded = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_):
        return


def create_server(host: str = HOST, port: int = PORT):
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Run the ComLab V3 simulation app.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true", help="Start the server without opening a browser tab.")
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port)
    url = f"http://{args.host}:{args.port}"
    print(f"ComLab V3 Python simulation running at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
