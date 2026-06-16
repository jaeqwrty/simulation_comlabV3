# The Complete Guide to Computer Lab Simulation V3: A Deep Dive

## Part 6: The API and Data Transport Layer

### 6.1 Bridging Python and the Browser
The physics engine is written in Python, but the visualization requires HTML5 Canvas and JavaScript. To bridge this gap, V3 utilizes **FastAPI**, a modern, high-performance web framework.

### 6.2 State Serialization
Every frame, the Python engine produces a massive amount of state:
- Where are the 50 agents?
- Which cells are on fire?
- How much smoke is in cell (10, 12)?

Transferring this via REST on every single visual frame (60fps) is highly inefficient. Therefore, V3 uses two main strategies:
1. **Delta Updates (WebSockets)**: Instead of sending the entire grid every frame, the API only sends the *changes* (deltas). If an agent moves from `(2,2)` to `(2,3)`, the server sends `{agent_id: 1, to: [2,3]}`.
2. **Chunked Polling (REST)**: If WebSockets are unavailable, the frontend can poll a `/tick` endpoint which processes $N$ ticks at once on the server and returns the final state, effectively creating a "time-lapse" effect.

### 6.3 Pydantic Schemas
To ensure that the JSON data perfectly matches what the JavaScript frontend expects, the API relies on `Pydantic` models.
For example, the response for an agent looks like:
```python
class AgentResponse(BaseModel):
    id: str
    x: int
    y: int
    phase: str
```
This strict typing ensures that if a backend developer renames `phase` to `status` in the physics engine, the API will immediately throw a validation error, preventing silent failures in the visualization.

### 6.4 The Frontend `Canvas` (Briefly)
While not Python, the frontend is a crucial part of the stack. It receives the JSON array of agents and simply loops over them, calling `ctx.fillRect()` or drawing sprite images. 
Because the frontend does ZERO physics math, it runs incredibly smoothly even on mobile devices. All the heavy lifting is safely contained within the Python backend server.
