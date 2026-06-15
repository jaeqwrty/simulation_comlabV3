from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Agent:
    agent_id: str
    kind: str
    behavior: str
    x: int
    y: int
    seed: int
    wait_until: int = 0
    phase: str = "waiting"
    target: tuple[int, int] = (0, 0)
    path: list[tuple[int, int]] = field(default_factory=list)
    speed_bank: float = 0.0
    exited: bool = False
    visited_locker: bool = False
    assigned_exit: str | None = None
    trip_until: int = 0
    reached_corridor: bool = False
    stamped_until: int = 0   # pinned by stampede
    packed_up: bool = False  # finished packing belongings before standing up
    bay_passage_cleared: bool = False