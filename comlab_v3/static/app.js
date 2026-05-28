const COLORS = {
  text: "#edf2f7",
  muted: "#9aa8ba",
  line: "#2d3c50",
  cell: "#111a24",
  hall: "#17212d",
  pc: "#56657a",
  green: "#22c55e",
  amber: "#f59e0b",
  orange: "#f97316",
  red: "#ef4444",
  blue: "#38bdf8",
  purple: "#c084fc",
  yellow: "#facc15",
  assistant: "#14b8a6",
  custodian: "#e879f9"
};

const CELL = 34;
let state = null;
let heatVisible = true;
let panic = true;
let running = false;

const $ = (id) => document.getElementById(id);
const els = {
  map: $("mapCanvas"),
  chart: $("chart"),
  start: $("startBtn"),
  step: $("stepBtn"),
  reset: $("resetBtn"),
  mode: $("modeSelect"),
  panic: $("panicBtn"),
  heat: $("heatBtn"),
  fire: $("fireSelect"),
  speed: $("speedRange"),
  speedText: $("speedText"),
  compare: $("compareBtn"),
  statusDot: $("statusDot"),
  statusText: $("statusText"),
  layoutTitle: $("layoutTitle"),
  layoutNote: $("layoutNote"),
  legend: $("legend"),
  events: $("events"),
  comparison: $("comparison")
};

function config() {
  return {
    mode: els.mode.value,
    panic,
    fireOrigin: els.fire.value,
    speed: Number(els.speed.value)
  };
}

async function post(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  state = await res.json();
  syncFromState();
  draw();
}

async function poll() {
  const res = await fetch("/api/state");
  state = await res.json();
  syncFromState();
  draw();
}

function syncFromState() {
  running = state.running;
  els.start.textContent = running ? "Pause" : "Start";
  els.statusDot.classList.toggle("running", running);
  els.statusText.textContent = running ? "Running" : state.completed ? "Complete" : "Ready";
  els.mode.value = state.mode;
  els.fire.value = state.fireOrigin;
  els.speed.value = state.speed;
  els.speedText.textContent = `${Number(state.speed).toFixed(1)}x`;
  panic = state.panic;
  els.panic.classList.toggle("active", panic);
  els.layoutTitle.textContent = state.mode === "current" ? "Current Layout" : "Modified Layout";
  els.layoutNote.textContent = state.mode === "current"
    ? "Locker near Back-Right exit creates cross-traffic."
    : "Locker is relocated away from the exit path while doors and hallway remain unchanged.";
}

function draw() {
  if (!state) return;
  drawMap();
  drawChart();
  drawMetrics();
  drawLegend();
  drawEvents();
}

function drawMap() {
  const ctx = els.map.getContext("2d");
  const layout = state.layout;
  ctx.clearRect(0, 0, els.map.width, els.map.height);

  for (let y = 0; y < layout.rows; y++) {
    for (let x = 0; x < layout.cols; x++) {
      ctx.fillStyle = x >= layout.labCols ? COLORS.hall : COLORS.cell;
      ctx.fillRect(x * CELL, y * CELL, CELL, CELL);
      ctx.strokeStyle = COLORS.line;
      ctx.strokeRect(x * CELL, y * CELL, CELL, CELL);
    }
  }

  ctx.strokeStyle = "#8795aa";
  ctx.lineWidth = 3;
  ctx.strokeRect(0, 0, layout.labCols * CELL, layout.rows * CELL);
  ctx.lineWidth = 1;

  drawHeatmap(layout);
  layout.workstations.forEach(([x, y]) => cell(ctx, x, y, COLORS.pc, "PC", COLORS.text));
  layout.instructorDesk.forEach(([x, y]) => rect(ctx, x, y, "#334155"));
  text(ctx, 2.5, .55, "Instructor Desk", 8);
  layout.dataRacks.forEach(([x, y]) => cell(ctx, x, y, COLORS.orange, "", COLORS.text));
  text(ctx, 8.5, 5.55, "Data", 8);
  cell(ctx, layout.locker[0], layout.locker[1], COLORS.yellow, "LOCK", "#111827");
  cell(ctx, layout.frontExit[0], layout.frontExit[1], COLORS.green, "EXIT", COLORS.text);
  cell(ctx, layout.backExit[0], layout.backExit[1], COLORS.green, "EXIT", COLORS.text);
  swing(ctx, layout.frontExit);
  swing(ctx, layout.backExit);
  cell(ctx, layout.frontStairs[0], layout.frontStairs[1], "#1f3b50", "STR", COLORS.text, COLORS.blue);
  cell(ctx, layout.emergencyStairs[0], layout.emergencyStairs[1], "#1f3b50", "STR", COLORS.text, COLORS.blue);
  text(ctx, 10.8, .6, "Shared hallway", 10, COLORS.muted);
  smoke(ctx, layout.fireOrigin[0], layout.fireOrigin[1]);
  state.agents.filter((agent) => !agent.exited).forEach((agent) => stick(ctx, agent));
}

function drawHeatmap(layout) {
  if (!heatVisible) return;
  const ctx = els.map.getContext("2d");
  const max = Math.max(1, state.maxHeat);
  Object.entries(state.heatmap).forEach(([key, value]) => {
    const [x, y] = key.split(",").map(Number);
    if (x >= layout.labCols) return;
    ctx.fillStyle = `rgba(249, 115, 22, ${Math.min(.7, value / max)})`;
    ctx.fillRect(x * CELL, y * CELL, CELL, CELL);
  });
}

function rect(ctx, x, y, fill) {
  ctx.fillStyle = fill;
  ctx.fillRect(x * CELL + 5, y * CELL + 7, CELL - 10, CELL - 14);
  ctx.strokeStyle = "#94a3b8";
  ctx.strokeRect(x * CELL + 5, y * CELL + 7, CELL - 10, CELL - 14);
}

function cell(ctx, x, y, fill, label, labelColor, stroke = "#94a3b8") {
  ctx.fillStyle = fill;
  ctx.fillRect(x * CELL + 4, y * CELL + 4, CELL - 8, CELL - 8);
  ctx.strokeStyle = stroke;
  ctx.strokeRect(x * CELL + 4, y * CELL + 4, CELL - 8, CELL - 8);
  if (label) text(ctx, x + .5, y + .56, label, 8, labelColor);
}

function text(ctx, x, y, value, size = 9, color = COLORS.text) {
  ctx.fillStyle = color;
  ctx.font = `800 ${size}px Segoe UI`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(value, x * CELL, y * CELL);
}

function smoke(ctx, x, y) {
  ctx.strokeStyle = "rgba(148, 163, 184, .45)";
  ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.arc((x + .5) * CELL, (y + .5) * CELL, CELL * 2.1, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = COLORS.orange;
  ctx.beginPath();
  ctx.arc((x + .5) * CELL, (y + .5) * CELL, 9, 0, Math.PI * 2);
  ctx.fill();
}

function swing(ctx, exitCell) {
  ctx.strokeStyle = COLORS.amber;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc((exitCell[0] + 1) * CELL, (exitCell[1] + .5) * CELL, CELL * .58, -Math.PI / 2, Math.PI / 2);
  ctx.stroke();
  ctx.lineWidth = 1;
}

function stick(ctx, agent) {
  const cx = (agent.x + .5) * CELL;
  const cy = (agent.y + .5) * CELL;
  const color = agent.kind === "student"
    ? { immediate: COLORS.green, locker: COLORS.yellow, task: COLORS.blue, peer: COLORS.purple }[agent.behavior]
    : { instructor: COLORS.orange, assistant: COLORS.assistant, custodian: COLORS.custodian }[agent.kind];

  ctx.strokeStyle = COLORS.text;
  ctx.lineWidth = 2;
  ctx.lineCap = "round";
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(cx, cy - 8, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  line(ctx, cx, cy - 4, cx, cy + 7);
  line(ctx, cx - 7, cy, cx + 7, cy);
  line(ctx, cx, cy + 7, cx - 6, cy + 14);
  line(ctx, cx, cy + 7, cx + 6, cy + 14);
  ctx.fillStyle = COLORS.text;
  ctx.beginPath();
  ctx.moveTo(cx, cy - 17);
  ctx.lineTo(cx - 4, cy - 12);
  ctx.lineTo(cx + 4, cy - 12);
  ctx.fill();
}

function line(ctx, x1, y1, x2, y2) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}

function drawMetrics() {
  $("mTime").textContent = `${state.time}s`;
  $("mInside").textContent = state.active;
  $("mEvacuated").textContent = state.evacuated;
  $("mTrips").textContent = state.trips;
  $("mDoors").textContent = state.doorCollisions;
  $("mHeat").textContent = state.maxHeat;
}

function drawChart() {
  const ctx = els.chart.getContext("2d");
  ctx.clearRect(0, 0, els.chart.width, els.chart.height);
  ctx.fillStyle = "#101720";
  ctx.fillRect(10, 24, 320, 88);
  ctx.strokeStyle = "#536276";
  line(ctx, 28, 104, 314, 104);
  line(ctx, 28, 36, 28, 104);
  if (state.rate.length <= 1) return;

  ctx.strokeStyle = COLORS.green;
  ctx.lineWidth = 3;
  ctx.beginPath();
  state.rate.forEach(([_, evacuated], index) => {
    const x = 28 + index / Math.max(1, state.rate.length - 1) * 286;
    const y = 104 - evacuated / state.totalAgents * 68;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.lineWidth = 1;
}

function drawLegend() {
  els.legend.innerHTML = [
    ["Immediate", COLORS.green],
    ["Locker-bound", COLORS.yellow],
    ["Task-bound", COLORS.blue],
    ["Peer-bound", COLORS.purple],
    ["Instructor", COLORS.orange],
    ["Assistant", COLORS.assistant],
    ["Custodian", COLORS.custodian]
  ].map(([label, color]) => `<span><i class="swatch" style="background:${color}"></i>${label}</span>`).join("")
    + `<span><i class="swatch" style="border-radius:4px;background:linear-gradient(90deg,rgba(249,115,22,.15),rgba(239,68,68,.9));border:0"></i>Heatmap intensity</span>`;
}

function drawEvents() {
  els.events.innerHTML = state.events.length
    ? state.events.map(([t, _type, message]) => `<div class="event"><strong>${String(t).padStart(3, "0")}s</strong> ${message}</div>`).join("")
    : "No incidents yet.";
}

function comparisonRow(label, current, modified, suffix = "") {
  const improvement = Number.isFinite(current) && current > 0
    ? `${Math.round((current - modified) / current * 100)}%`
    : "";
  return `<tr><td>${label}</td><td>${current}${suffix}</td><td>${modified}${suffix}</td><td>${improvement}</td></tr>`;
}

els.start.onclick = () => post("/api/control", { action: running ? "pause" : "start", config: config() });
els.step.onclick = () => post("/api/control", { action: "step", config: config() });
els.reset.onclick = () => post("/api/control", { action: "reset", config: config() });
els.mode.onchange = () => post("/api/reset", config());
els.fire.onchange = () => post("/api/reset", config());
els.speed.oninput = () => {
  els.speedText.textContent = `${Number(els.speed.value).toFixed(1)}x`;
  post("/api/control", { action: running ? "start" : "pause", config: config() });
};
els.panic.onclick = () => {
  panic = !panic;
  els.panic.classList.toggle("active", panic);
  post("/api/reset", config());
};
els.heat.onclick = () => {
  heatVisible = !heatVisible;
  els.heat.classList.toggle("active", heatVisible);
  draw();
};
els.compare.onclick = async () => {
  const res = await fetch("/api/compare", { method: "POST" });
  const data = await res.json();
  els.comparison.innerHTML = `<table>
    <thead><tr><th>Metric</th><th>Current</th><th>Modified</th><th>Improvement</th></tr></thead>
    <tbody>
      ${comparisonRow("Total time", data.current.time, data.modified.time, "s")}
      ${comparisonRow("Trips", data.current.trips, data.modified.trips)}
      ${comparisonRow("Door collisions", data.current.door_collisions, data.modified.door_collisions)}
      ${comparisonRow("Max heat", data.current.max_heat, data.modified.max_heat)}
    </tbody>
  </table>`;
};

poll();
setInterval(poll, 180);
