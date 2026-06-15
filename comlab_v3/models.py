"""Pydantic models for API request/response validation."""

from pydantic import BaseModel
from typing import Optional, Dict, List, Any

class SimulationConfig(BaseModel):
    mode: Optional[str] = None
    panic: Optional[bool] = None
    fireOrigin: Optional[str] = None
    speed: Optional[float] = None

class ControlAction(BaseModel):
    action: str
    config: Optional[SimulationConfig] = None

class ResetRequest(BaseModel):
    config: Optional[SimulationConfig] = None
