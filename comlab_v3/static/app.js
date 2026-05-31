const COLORS = {
  text: "#f8fafc",
  muted: "#94a3b8",
  line: "rgba(51, 65, 85, 0.18)",
  cell: "rgba(30, 41, 59, 0.45)",
  hall: "rgba(15, 23, 42, 0.65)",
  
  // Actor colors
  green: "#10b981",    // Immediate egress
  yellow: "#fbbf24",   // Locker retrieving
  blue: "#3b82f6",     // Task-bound
  purple: "#8b5cf6",   // Peer-bound
  orange: "#f97316",   // Instructor
  assistant: "#14b8a6",// Assistant
  custodian: "#d946ef",// Custodian
  red: "#f43f5e"       // Alert / Tripped
};

const CELL = 34;
let state = null;
let heatVisible = true;
let panic = true;
let running = false;
let animationFrameId = null;

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

// High-DPI scaling utility
function getDprContext(canvas, logicalWidth, logicalHeight) {
  const dpr = window.devicePixelRatio || 1;
  const curW = canvas.getAttribute("data-width") || "";
  const curH = canvas.getAttribute("data-height") || "";
  const curD = canvas.getAttribute("data-dpr") || "";
  
  if (curW !== String(logicalWidth) || curH !== String(logicalHeight) || curD !== String(dpr)) {
    canvas.width = logicalWidth * dpr;
    canvas.height = logicalHeight * dpr;
    canvas.style.width = `${logicalWidth}px`;
    canvas.style.height = `${logicalHeight}px`;
    canvas.setAttribute("data-width", logicalWidth);
    canvas.setAttribute("data-height", logicalHeight);
    canvas.setAttribute("data-dpr", dpr);
  }
  
  const ctx = canvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset
  ctx.scale(dpr, dpr);
  return ctx;
}

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
  triggerDraw();
}

async function poll() {
  const res = await fetch("/api/state");
  state = await res.json();
  syncFromState();
  triggerDraw();
}

function syncFromState() {
  running = state.running;
  
  // Dynamic play/pause button state with SVG
  const playIcon = `<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>`;
  const pauseIcon = `<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`;
  els.start.innerHTML = running ? `${pauseIcon}<span>Pause</span>` : `${playIcon}<span>Start</span>`;
  
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

function triggerDraw() {
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  animationFrameId = requestAnimationFrame(draw);
}

function draw() {
  if (!state) return;
  drawMap();
  drawChart();
  drawMetrics();
  drawLegend();
  drawEvents();
  
  // Continuously request animation frames if running or glowing pulsing fire needs redrawing
  if (running || state.fireOrigin) {
    animationFrameId = requestAnimationFrame(draw);
  }
}

// ENVIRONMENT blueprint drawers
function drawWorkstationBlueprint(ctx, x, y) {
  const px = x * CELL;
  const py = y * CELL;
  
  // Subtle desk backplate
  ctx.fillStyle = "rgba(30, 41, 59, 0.4)";
  ctx.strokeStyle = "rgba(71, 85, 105, 0.4)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(px + 4, py + 4, CELL - 8, CELL - 8, 4);
  ctx.fill();
  ctx.stroke();
  
  // Monitor line in glowing blue/cyan
  ctx.strokeStyle = "rgba(56, 189, 248, 0.75)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(px + 10, py + CELL - 8);
  ctx.lineTo(px + CELL - 10, py + CELL - 8);
  ctx.stroke();
  
  // Computer keyboard/base
  ctx.strokeStyle = "rgba(100, 116, 139, 0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(px + 13, py + CELL - 5);
  ctx.lineTo(px + CELL - 13, py + CELL - 5);
  ctx.stroke();
}

function drawInstructorDeskBlueprint(ctx, x, y, index) {
  const px = x * CELL;
  const py = y * CELL;
  
  ctx.fillStyle = "rgba(51, 65, 85, 0.55)";
  ctx.strokeStyle = "rgba(100, 116, 139, 0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  
  // Unified contiguous look: curve start/end edges
  if (index === 0) {
    ctx.roundRect(px + 4, py + 6, CELL - 4, CELL - 12, { tl: 4, bl: 4, tr: 0, br: 0 });
  } else if (index === 2) {
    ctx.roundRect(px, py + 6, CELL - 4, CELL - 12, { tl: 0, bl: 0, tr: 4, br: 4 });
  } else {
    ctx.rect(px, py + 6, CELL, CELL - 12);
  }
  ctx.fill();
  ctx.stroke();
  
  // Put a tech device silhouette on the center block
  if (index === 1) {
    ctx.fillStyle = "rgba(56, 189, 248, 0.1)";
    ctx.strokeStyle = "rgba(56, 189, 248, 0.7)";
    ctx.beginPath();
    ctx.roundRect(px + 9, py + 9, CELL - 18, 9, 2);
    ctx.fill();
    ctx.stroke();
  }
}

function drawServerRackBlueprint(ctx, x, y) {
  const px = x * CELL;
  const py = y * CELL;
  
  ctx.fillStyle = "rgba(249, 115, 22, 0.12)";
  ctx.strokeStyle = "rgba(249, 115, 22, 0.65)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(px + 4, py + 4, CELL - 8, CELL - 8, 4);
  ctx.fill();
  ctx.stroke();
  
  // Horizontal slots
  ctx.strokeStyle = "rgba(249, 115, 22, 0.3)";
  for (let offset = 8; offset < CELL - 6; offset += 5) {
    ctx.beginPath();
    ctx.moveTo(px + 8, py + offset);
    ctx.lineTo(px + CELL - 8, py + offset);
    ctx.stroke();
  }
}

function drawStaircaseBlueprint(ctx, x, y) {
  const px = x * CELL;
  const py = y * CELL;
  
  ctx.fillStyle = "rgba(30, 41, 59, 0.55)";
  ctx.strokeStyle = "rgba(59, 130, 246, 0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(px + 3, py + 3, CELL - 6, CELL - 6, 2);
  ctx.fill();
  ctx.stroke();
  
  // Stair treads lines
  ctx.strokeStyle = "rgba(59, 130, 246, 0.35)";
  for (let i = 7; i < CELL - 4; i += 4) {
    ctx.beginPath();
    ctx.moveTo(px + i, py + 6);
    ctx.lineTo(px + i, py + CELL - 6);
    ctx.stroke();
  }
  
  // Escaping directional indicator arrow
  ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(px + 10, py + CELL / 2);
  ctx.lineTo(px + CELL - 10, py + CELL / 2);
  ctx.lineTo(px + CELL - 14, py + CELL / 2 - 4);
  ctx.moveTo(px + CELL - 10, py + CELL / 2);
  ctx.lineTo(px + CELL - 14, py + CELL / 2 + 4);
  ctx.stroke();
}

function drawLockerBlueprint(ctx, x, y) {
  const px = x * CELL;
  const py = y * CELL;
  
  ctx.fillStyle = "rgba(245, 158, 11, 0.12)";
  ctx.strokeStyle = "rgba(245, 158, 11, 0.75)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.roundRect(px + 4, py + 4, CELL - 8, CELL - 8, 4);
  ctx.fill();
  ctx.stroke();
  
  // Drawer padlock graphic or clean letter
  ctx.fillStyle = "rgba(245, 158, 11, 0.85)";
  ctx.font = "800 8.5px var(--font-sans)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("LOCK", px + CELL / 2, py + CELL / 2);
}

function drawExitDoorBlueprint(ctx, x, y) {
  const px = x * CELL;
  const py = y * CELL;
  
  ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
  ctx.strokeStyle = "rgba(16, 185, 129, 0.8)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.roundRect(px + 4, py + 4, CELL - 8, CELL - 8, 4);
  ctx.fill();
  ctx.stroke();
  
  ctx.fillStyle = "#10b981";
  ctx.font = "800 9px var(--font-sans)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("EXIT", px + CELL / 2, py + CELL / 2);
}

function drawDoorSwingBlueprint(ctx, exitCell) {
  const px = exitCell[0] * CELL;
  const py = exitCell[1] * CELL;
  
  ctx.strokeStyle = "rgba(16, 185, 129, 0.4)";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.arc((exitCell[0] + 1) * CELL, (exitCell[1] + 0.5) * CELL, CELL * 0.58, -Math.PI / 2, Math.PI / 2);
  ctx.stroke();
  ctx.setLineDash([]);
  
  // Solid door frame leaf angle
  ctx.strokeStyle = "rgba(16, 185, 129, 0.8)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo((exitCell[0] + 1) * CELL, (exitCell[1] + 0.5) * CELL);
  ctx.lineTo((exitCell[0] + 1) * CELL + CELL * 0.42, (exitCell[1] + 0.5) * CELL - CELL * 0.42);
  ctx.stroke();
}

function drawMap() {
  const ctx = getDprContext(els.map, 442, 408);
  const layout = state.layout;
  ctx.clearRect(0, 0, 442, 408);

  // 1. Grid Background
  for (let y = 0; y < layout.rows; y++) {
    for (let x = 0; x < layout.cols; x++) {
      ctx.fillStyle = x >= layout.labCols ? COLORS.hall : COLORS.cell;
      ctx.fillRect(x * CELL, y * CELL, CELL, CELL);
      ctx.strokeStyle = COLORS.line;
      ctx.lineWidth = 1;
      ctx.strokeRect(x * CELL, y * CELL, CELL, CELL);
    }
  }

  // 2. Blueprint outline for Classroom lab bounds
  ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
  ctx.lineWidth = 2.5;
  ctx.strokeRect(0, 0, layout.labCols * CELL, layout.rows * CELL);
  ctx.lineWidth = 1;

  // 3. Thermal Heatmap Congestion Bloom
  drawHeatmap(ctx, layout);

  // 4. Blueprint elements
  layout.workstations.forEach(([x, y]) => drawWorkstationBlueprint(ctx, x, y));
  layout.instructorDesk.forEach(([x, y], idx) => drawInstructorDeskBlueprint(ctx, x, y, idx));
  layout.dataRacks.forEach(([x, y]) => drawServerRackBlueprint(ctx, x, y));
  
  drawLockerBlueprint(ctx, layout.locker[0], layout.locker[1]);
  drawExitDoorBlueprint(ctx, layout.frontExit[0], layout.frontExit[1]);
  drawExitDoorBlueprint(ctx, layout.backExit[0], layout.backExit[1]);
  
  drawDoorSwingBlueprint(ctx, layout.frontExit);
  drawDoorSwingBlueprint(ctx, layout.backExit);
  
  drawStaircaseBlueprint(ctx, layout.frontStairs[0], layout.frontStairs[1]);
  drawStaircaseBlueprint(ctx, layout.emergencyStairs[0], layout.emergencyStairs[1]);
  
  // 5. pulsing fire smoke plume
  drawFireSmoke(ctx, layout.fireOrigin[0], layout.fireOrigin[1]);
  
  // 6. Agents avatars
  state.agents.filter((agent) => !agent.exited).forEach((agent) => drawAgent(ctx, agent));
}

function drawHeatmap(ctx, layout) {
  if (!heatVisible) return;
  const max = Math.max(1, state.maxHeat);
  
  ctx.save();
  ctx.globalCompositeOperation = "screen";
  
  Object.entries(state.heatmap).forEach(([key, value]) => {
    const [x, y] = key.split(",").map(Number);
    if (x >= layout.labCols) return;
    
    const cx = (x + 0.5) * CELL;
    const cy = (y + 0.5) * CELL;
    const intensity = Math.min(0.65, value / max);
    
    const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, CELL * 1.35);
    grad.addColorStop(0, `rgba(249, 115, 22, ${intensity})`);
    grad.addColorStop(0.4, `rgba(239, 68, 68, ${intensity * 0.4})`);
    grad.addColorStop(1, "rgba(239, 68, 68, 0)");
    
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, CELL * 1.35, 0, Math.PI * 2);
    ctx.fill();
  });
  
  ctx.restore();
}

function drawFireSmoke(ctx, x, y) {
  const cx = (x + 0.5) * CELL;
  const cy = (y + 0.5) * CELL;
  
  // Pulse dynamics
  const pulse = Math.sin(Date.now() / 240);
  const smokeRadius = CELL * (1.8 + 0.15 * pulse);
  
  // Smoke plume gradient
  const smokeGrad = ctx.createRadialGradient(cx, cy, CELL * 0.3, cx, cy, smokeRadius);
  smokeGrad.addColorStop(0, "rgba(244, 63, 94, 0.28)");
  smokeGrad.addColorStop(0.4, "rgba(249, 115, 22, 0.12)");
  smokeGrad.addColorStop(1, "rgba(148, 163, 184, 0)");
  
  ctx.fillStyle = smokeGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, smokeRadius, 0, Math.PI * 2);
  ctx.fill();
  
  // Dashed hazard outline
  ctx.strokeStyle = "rgba(244, 63, 94, 0.35)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.arc(cx, cy, smokeRadius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);
  
  // Core hazard fire core
  const fireGrad = ctx.createRadialGradient(cx, cy, 1, cx, cy, 10);
  fireGrad.addColorStop(0, "#ffffff");
  fireGrad.addColorStop(0.35, "#facc15");
  fireGrad.addColorStop(0.7, "#f97316");
  fireGrad.addColorStop(1, "rgba(239, 68, 68, 0)");
  
  ctx.fillStyle = fireGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, 12, 0, Math.PI * 2);
  ctx.fill();
}

function drawAgent(ctx, agent) {
  const cx = (agent.x + 0.5) * CELL;
  const cy = (agent.y + 0.5) * CELL;
  
  let color = COLORS.green;
  if (agent.kind === "student") {
    color = {
      immediate: COLORS.green,
      locker: COLORS.yellow,
      task: COLORS.blue,
      peer: COLORS.purple
    }[agent.behavior] || COLORS.green;
  } else {
    color = {
      instructor: COLORS.orange,
      assistant: COLORS.assistant,
      custodian: COLORS.custodian
    }[agent.kind] || COLORS.blue;
  }
  
  // 1. Tripped agent render
  if (agent.phase === "tripped") {
    const pulse = 1 + 0.18 * Math.sin(Date.now() / 120);
    ctx.fillStyle = "rgba(244, 63, 94, 0.28)";
    ctx.strokeStyle = COLORS.red;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 10.5 * pulse, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    
    ctx.fillStyle = "#ffffff";
    ctx.font = "800 11px var(--font-sans)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("!", cx, cy);
    return;
  }
  
  // 2. Standard circle avatar
  const radius = agent.kind === "student" ? 6 : 8.5;
  
  // Staff member outer double ring
  if (agent.kind !== "student") {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, radius + 3, 0, Math.PI * 2);
    ctx.stroke();
  }
  
  ctx.fillStyle = color;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  
  // Staff role emblem text
  if (agent.kind !== "student") {
    ctx.fillStyle = "#ffffff";
    ctx.font = "800 9px var(--font-sans)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const char = agent.kind === "instructor" ? "I" : agent.kind === "assistant" ? "A" : "C";
    ctx.fillText(char, cx, cy);
  } else {
    // Student egress heading micro arrow dot
    if (agent.target && (agent.target[0] !== agent.x || agent.target[1] !== agent.y)) {
      const dx = agent.target[0] - agent.x;
      const dy = agent.target[1] - agent.y;
      const angle = Math.atan2(dy, dx);
      
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(cx + Math.cos(angle) * (radius + 1.2), cy + Math.sin(angle) * (radius + 1.2), 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawMetrics() {
  $("mTime").textContent = `${state.time}s`;
  $("mInside").textContent = state.active;
  $("mEvacuated").textContent = state.evacuated;
  $("mTrips").textContent = state.trips;
  $("mDoors").textContent = state.doorCollisions;
  $("mHeat").textContent = state.maxHeat;
}

// Rich Analytics Custom Area Line Chart
function drawChart() {
  const ctx = getDprContext(els.chart, 340, 120);
  ctx.clearRect(0, 0, 340, 120);
  
  const padL = 34;
  const padR = 14;
  const padT = 16;
  const padB = 20;
  const chartW = 340 - padL - padR;
  const chartH = 120 - padT - padB;
  
  // Horizontal grid lines and Y-axis labels
  ctx.strokeStyle = "rgba(148, 163, 184, 0.08)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "rgba(148, 163, 184, 0.45)";
  ctx.font = "500 8px var(--font-mono)";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  ticks.forEach(tick => {
    const y = padT + (1 - tick) * chartH;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(340 - padR, y);
    ctx.stroke();
    
    ctx.fillText(`${Math.round(tick * 100)}%`, padL - 6, y);
  });
  
  // Bottom X-axis line
  ctx.strokeStyle = "rgba(148, 163, 184, 0.15)";
  ctx.beginPath();
  ctx.moveTo(padL, padT + chartH);
  ctx.lineTo(340 - padR, padT + chartH);
  ctx.stroke();
  
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText("0s", padL, padT + chartH + 4);
  ctx.fillText("120s", padL + chartW * 0.5, padT + chartH + 4);
  ctx.fillText("240s", padL + chartW, padT + chartH + 4);
  
  if (!state || state.rate.length <= 1) return;
  
  // Map points
  const maxT = 240;
  const points = state.rate.map(([t, evacuated]) => {
    const px = padL + Math.min(1, t / maxT) * chartW;
    const py = padT + (1 - evacuated / state.totalAgents) * chartH;
    return { x: px, y: py };
  });
  
  // 1. Curve Gradient Fill
  const fillGrad = ctx.createLinearGradient(padL, padT, padL, padT + chartH);
  fillGrad.addColorStop(0, "rgba(16, 185, 129, 0.22)");
  fillGrad.addColorStop(1, "rgba(16, 185, 129, 0)");
  
  ctx.fillStyle = fillGrad;
  ctx.beginPath();
  ctx.moveTo(padL, padT + chartH);
  points.forEach(pt => ctx.lineTo(pt.x, pt.y));
  ctx.lineTo(points[points.length - 1].x, padT + chartH);
  ctx.closePath();
  ctx.fill();
  
  // 2. Beautiful Curve Stroke
  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  points.forEach((pt, i) => {
    if (i === 0) ctx.moveTo(pt.x, pt.y);
    else ctx.lineTo(pt.x, pt.y);
  });
  ctx.stroke();
  
  // 3. Glowing Pulse Dot at current peak
  const head = points[points.length - 1];
  const pulse = 1 + 0.2 * Math.sin(Date.now() / 150);
  ctx.fillStyle = "rgba(16, 185, 129, 0.25)";
  ctx.beginPath();
  ctx.arc(head.x, head.y, 6.5 * pulse, 0, Math.PI * 2);
  ctx.fill();
  
  ctx.fillStyle = "#10b981";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(head.x, head.y, 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
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

// Console style Event Logs with severity badges
function drawEvents() {
  if (!state.events.length) {
    els.events.innerHTML = '<div class="event">No incidents yet.</div>';
    return;
  }
  
  els.events.innerHTML = state.events.map(([t, type, message]) => {
    let badgeClass = "badge-default";
    let badgeText = type || "log";
    
    if (type === "trip") badgeClass = "badge-trip";
    else if (type === "door") badgeClass = "badge-door";
    else if (type === "locker") badgeClass = "badge-locker";
    else if (type === "extinguisher") badgeClass = "badge-extinguisher";
    
    return `<div class="event">
      <strong>${String(t).padStart(3, "0")}s</strong>
      <span class="event-badge ${badgeClass}">${badgeText}</span>
      <span>${message}</span>
    </div>`;
  }).join("");
}

function comparisonRow(label, current, modified, suffix = "") {
  const improvement = Number.isFinite(current) && current > 0
    ? (current - modified) / current * 100
    : null;
    
  let badge = "";
  if (improvement !== null) {
    const val = Math.round(improvement);
    if (val > 0) badge = `<span class="improvement-pill">+${val}%</span>`;
    else if (val < 0) badge = `<span class="improvement-pill negative">${val}%</span>`;
    else badge = `<span class="improvement-pill neutral">0%</span>`;
  } else {
    badge = `<span class="improvement-pill neutral">-</span>`;
  }
  
  return `<tr><td>${label}</td><td>${current}${suffix}</td><td>${modified}${suffix}</td><td>${badge}</td></tr>`;
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
  triggerDraw();
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
