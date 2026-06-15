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
const MAP_W = 442;
const MAP_H = 408;
const LAB_LEFT = 0;
const LAB_RIGHT = 360;
const HALL_RIGHT = MAP_W;
const SERVICE_X = 302;
const SERVICE_W = 52;
const WORKSTATION_X = new Map([
  [0, 42],
  [1, 82],
  [2, 122],
  [4, 190],
  [5, 230],
  [6, 270]
]);
const AISLE_X = 156;
const EXIT_X = LAB_RIGHT;
const BASE_ROW_Y = new Map(Array.from({ length: 12 }, (_, y) => [y, y * CELL + CELL / 2]));
const WORKSTATION_ROW_Y = new Map([
  [1, 72],
  [2, 116],
  [4, 160],
  [5, 204],
  [7, 248],
  [8, 292]
]);
let state = null;
let heatVisible = true;
let panic = true;
let running = false;
let animationFrameId = null;
let lastPostTime = 0; // Prevent polling from overwriting user interactions
const agentMotion = new Map();

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

window.addEventListener("error", (event) => {
  const ctx = els.map?.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, els.map.width, els.map.height);
  ctx.fillStyle = "#05070d";
  ctx.fillRect(0, 0, els.map.width, els.map.height);
  ctx.fillStyle = "#f43f5e";
  ctx.font = "16px sans-serif";
  ctx.fillText(`Render error: ${event.message}`, 16, 32);
});

function layoutFor(mode = "current", fireOrigin = "data") {
  const modified = mode === "modified";
  const workstations = [];
  const rows = modified ? [1, 2, 4, 5, 7] : [1, 2, 4, 5, 7, 8];
  if (modified) {
    [1, 2, 4, 5].forEach((y) => {
      [0, 1, 2, 3, 4, 5, 6, 7].forEach((x) => workstations.push([x, y]));
    });
    [4, 5, 6, 7].forEach((x) => workstations.push([x, 7]));
  } else {
    const cols = [0, 1, 2, 4, 5, 6];
    rows.forEach((y) => cols.forEach((x) => workstations.push([x, y])));
  }

  const storage = modified ? [7, 11] : [7, 11];
  const fireOrigins = modified
    ? { data: [1, 11], desk: [6, 0], workstation: [3, 5], locker: storage, shelves: storage, assistant: [4, 11] }
    : { data: [7, 4], desk: [6, 0], workstation: [2, 5], locker: storage, shelves: storage, assistant: [7, 8] };

  return {
    rows: 12,
    cols: 13,
    labCols: 9,
    hallCols: 4,
    workstations,
    workstationRows: rows,
    instructorDesk: [[6, 0]],
    dataRacks: modified ? [[0, 11], [1, 11], [2, 11]] : [[7, 2], [7, 3], [7, 4], [7, 5], [7, 6]],
    studentAssistantDesk: modified ? [[3, 11], [4, 11], [5, 11]] : [[7, 7], [7, 8], [7, 9]],
    extraPcs: modified ? [] : [[0, 11], [1, 11], [2, 11], [3, 11]],
    shelves: [storage],
    storage,
    frontExit: [8, 0],
    backExit: [8, 11],
    frontStairs: [12, 1],
    emergencyStairs: [12, 11],
    locker: storage,
    fireOrigin: fireOrigins[fireOrigin] || fireOrigins.data,
    fireCells: [fireOrigins[fireOrigin] || fireOrigins.data],
    fireLocations: {
      data: "Data / communication rack",
      desk: "Instructor desk",
      workstation: "Student workstation row",
      locker: "Locker / bag shelves",
      assistant: "Student assistant bay"
    },
    cell: CELL,
    hallwayWall: Array.from({ length: 12 }, (_, y) => [8, y]).filter(([x, y]) => !(x === 8 && (y === 0 || y === 11))),
    partitionWall: modified ? [[0, 11], [1, 11], [2, 11], [3, 11], [4, 11], [5, 11]] : [[7, 2], [7, 3], [7, 4], [7, 5], [7, 6], [7, 7], [7, 8], [7, 9]],
    serviceBayPassage: modified ? [6, 11] : [7, 10],
    extinguisherExit: modified ? [4, 0] : [7, 0],
    extinguisherEntrance: null,
    extinguisherProfessor: modified ? [4, 0] : [7, 0],
    extinguisherAssistant: modified ? [6, 10] : [6, 9],
    extinguisherShelves: modified ? [7, 10] : [6, 11],
    fireExtinguishers: modified ? [[4, 0], [6, 10], [7, 10]] : [[7, 0], [6, 9], [6, 11]]
  };
}

function makeFallbackState(mode = els.mode.value || "current") {
  const fireOrigin = els.fire.value || "data";
  const layout = layoutFor(mode, fireOrigin);
  const agents = layout.workstations.map(([x, y], index) => ({
    id: `S${String(index + 1).padStart(2, "0")}`,
    kind: "student",
    behavior: ["immediate", "locker", "task", "peer"][index % 4],
    role: "student",
    x,
    y,
    target: [x, y],
    phase: "waiting",
    exited: false,
    stamped_until: 0
  }));

  return {
    running: false,
    mode,
    panic,
    fireOrigin,
    fireCells: layout.fireCells,
    speed: Number(els.speed.value || 1.5),
    time: 0,
    active: agents.length,
    evacuated: 0,
    totalAgents: agents.length,
    trips: 0,
    doorCollisions: 0,
    fireDamage: 0,
    maxHeat: 0,
    completed: false,
    agents,
    heatmap: {},
    rate: [[0, 0]],
    events: [],
    layout
  };
}

function visualCenter(x, y) {
  if (state && state.mode === "modified") {
    let cx;
    if (x >= 0 && x <= 3) {
      cx = 38 + x * 36; // Left 4-computer table
    } else if (x >= 4 && x <= 7) {
      cx = 218 + (x - 4) * 36; // Right 4-computer table
    } else if (x === 8) {
      cx = EXIT_X;
    } else if (x >= 9) {
      const hallStep = (HALL_RIGHT - LAB_RIGHT) / 4;
      cx = LAB_RIGHT + hallStep * (x - 8.5);
    } else {
      cx = x * CELL + CELL / 2;
    }
    const usesWorkstationLane = (x >= 0 && x <= 7) && y <= 8;
    return {
      x: cx,
      y: (usesWorkstationLane ? WORKSTATION_ROW_Y.get(y) : undefined)
        ?? BASE_ROW_Y.get(y)
        ?? (y * CELL + CELL / 2)
    };
  }

  let cx;
  const serviceBayLane = x === 7;
  const usesWorkstationLane = (WORKSTATION_X.has(x) || x === 3) && !serviceBayLane;
  if (WORKSTATION_X.has(x)) {
    cx = WORKSTATION_X.get(x);
  } else if (x === 3) {
    cx = AISLE_X;
  } else if (x === 7) {
    cx = SERVICE_X + SERVICE_W / 2;
  } else if (x === 8) {
    cx = EXIT_X;
  } else if (x >= 9) {
    const hallStep = (HALL_RIGHT - LAB_RIGHT) / 4;
    cx = LAB_RIGHT + hallStep * (x - 8.5);
  } else {
    cx = x * CELL + CELL / 2;
  }

  return {
    x: cx,
    y: (usesWorkstationLane ? WORKSTATION_ROW_Y.get(y) : undefined)
      ?? BASE_ROW_Y.get(y)
      ?? (y * CELL + CELL / 2)
  };
}

// High-DPI scaling utility
function getDprContext(canvas, logicalWidth, logicalHeight) {
  const dpr = window.devicePixelRatio || 1;
  const curW = canvas.getAttribute("data-width") || "";
  const curH = canvas.getAttribute("data-height") || "";
  const curD = canvas.getAttribute("data-dpr") || "";
  
  if (curW !== String(logicalWidth) || curH !== String(logicalHeight) || curD !== String(dpr)) {
    canvas.width = logicalWidth * dpr;
    canvas.height = logicalHeight * dpr;
    if (canvas.id === "mapCanvas") {
      canvas.style.width = "100%";
      canvas.style.maxWidth = `${logicalWidth}px`;
      canvas.style.height = "auto";
    } else {
      canvas.style.width = `${logicalWidth}px`;
      canvas.style.height = `${logicalHeight}px`;
    }
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

function applyUrlConfig() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  const fire = params.get("fire");
  const speed = params.get("speed");
  const panicParam = params.get("panic");

  if (mode === "current" || mode === "modified") els.mode.value = mode;
  if (fire && [...els.fire.options].some((option) => option.value === fire)) els.fire.value = fire;
  if (speed && !Number.isNaN(Number(speed))) els.speed.value = String(Math.min(3, Math.max(0.5, Number(speed))));
  if (panicParam === "0" || panicParam === "false") panic = false;
  if (panicParam === "1" || panicParam === "true") panic = true;
}

async function post(path, body = {}) {
  lastPostTime = Date.now(); // Record user action timestamp
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state = await res.json();
  } catch (err) {
    state = makeFallbackState(body?.mode || body?.config?.mode || els.mode.value);
    els.statusText.textContent = "Offline preview";
  }
  syncFromState();
  triggerDraw();
}

async function poll() {
  // If user interacted recently, ignore polling state responses to protect local state changes
  if (Date.now() - lastPostTime < 800) return;
  try {
    const res = await fetch("/api/state");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state = await res.json();
    if (Date.now() - lastPostTime < 800) return;
    syncFromState();
    triggerDraw();
  } catch (err) {
    if (!state) {
      state = makeFallbackState();
      syncFromState();
      triggerDraw();
    }
  }
}

function stepDurationMs() {
  const speed = Number(state?.speed || 1.5);
  return Math.max(120, 340 / speed);
}

function syncAgentMotion(agents = state?.agents || []) {
  const now = performance.now();
  const activeIds = new Set();

  agents.filter((agent) => !agent.exited).forEach((agent) => {
    activeIds.add(agent.id);
    const prev = agentMotion.get(agent.id);
    const next = { x: agent.x, y: agent.y };

    if (!prev || prev.to.x !== next.x || prev.to.y !== next.y) {
      agentMotion.set(agent.id, {
        from: prev ? prev.to : next,
        to: next,
        startTime: now
      });
    }
  });

  for (const id of agentMotion.keys()) {
    if (!activeIds.has(id)) {
      agentMotion.delete(id);
    }
  }
}

function agentVisualCenter(agent) {
  const motion = agentMotion.get(agent.id);
  if (!motion) {
    return visualCenter(agent.x, agent.y);
  }

  const duration = stepDurationMs();
  const progress = Math.min(1, (performance.now() - motion.startTime) / duration);
  const from = visualCenter(motion.from.x, motion.from.y);
  const to = visualCenter(motion.to.x, motion.to.y);

  let x = from.x + (to.x - from.x) * progress;
  let y = from.y + (to.y - from.y) * progress;

  const isStaff = agent.kind === "custodian" || agent.kind === "assistant";
  if (isStaff) {
    const passageExit =
      motion.from.x === 7 &&
      motion.to.x === 6 &&
      motion.from.y === 10 &&
      motion.to.y === 10;
    const verticalCol7 = motion.from.x === 7 && motion.to.x === 7;

    if (passageExit) {
      y = from.y;
    } else if (verticalCol7) {
      x = from.x;
    }
  }

  return { x, y };
}

function motionStillAnimating() {
  const duration = stepDurationMs();
  const now = performance.now();
  return [...agentMotion.values()].some((motion) => now - motion.startTime < duration);
}

function syncFromState() {
  running = state.running;
  syncAgentMotion();
  
  // Dynamic play/pause button state with SVG
  const playIcon = `<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>`;
  const pauseIcon = `<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`;
  els.start.innerHTML = running ? `${pauseIcon}<span>Pause</span>` : `${playIcon}<span>Start</span>`;
  
  els.statusDot.classList.toggle("running", running);
  els.statusText.textContent = running ? "Running" : state.completed ? "Complete" : "Ready";
  els.mode.value = state.mode;
  els.fire.value = state.fireOrigin === "shelves" ? "locker" : state.fireOrigin;
  els.speed.value = state.speed;
  els.speedText.textContent = `${Number(state.speed).toFixed(1)}x`;
  panic = state.panic;
  els.panic.classList.toggle("active", panic);
  
  els.layoutTitle.textContent = state.mode === "current" ? "Current Layout" : "Modified Layout";
  els.layoutNote.textContent = state.mode === "current"
    ? "Locker near the Entrance door creates cross-traffic with evacuating agents."
    : "Safer layout: 4-computer student tables, rear staff service zone, unified bag/shelf storage, clear center aisle, and reachable extinguishers.";
}

function triggerDraw() {
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  animationFrameId = null;
  draw();
}

function draw() {
  if (!state) return;
  drawMap();
  drawChart();
  drawMetrics();
  drawLegend();
  drawEvents();
  
  // Keep animating while the sim runs, fire glows, or agents slide between grid cells.
  if (running || state.fireOrigin || motionStillAnimating()) {
    animationFrameId = requestAnimationFrame(draw);
  }
}

// ENVIRONMENT blueprint drawers
function drawWorkstationBlueprint(ctx, x, y) {
  // Render a compact monitor tile similar to the provided reference image
  const { x: cx, y: cy } = visualCenter(x, y);
  const px = cx - CELL / 2;
  const py = cy - CELL / 2;

  // Monitor bezel (rounded square)
  const bw = CELL - 12;
  const bh = CELL - 14;
  const bx = px + 6;
  const by = py + 4;
  ctx.fillStyle = "rgba(8,10,14,0.86)";
  ctx.strokeStyle = "rgba(71,85,105,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(bx, by, bw, bh, 6);
  ctx.fill();
  ctx.stroke();

  // Inner screen subtle gradient
  const screenInset = 6;
  const sx = bx + screenInset / 2;
  const sy = by + screenInset / 2;
  const sw = bw - screenInset;
  const sh = bh - screenInset - 6;
  const grad = ctx.createLinearGradient(sx, sy, sx, sy + sh);
  grad.addColorStop(0, "rgba(10,20,30,0.95)");
  grad.addColorStop(1, "rgba(10,30,40,0.8)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.roundRect(sx, sy, sw, sh, 4);
  ctx.fill();

  // Small channel/LED below screen like the reference (thin cyan strip)
  ctx.fillStyle = "rgba(56,189,248,0.18)";
  const ledW = sw * 0.45;
  const ledH = 3;
  ctx.fillRect(sx + (sw - ledW) / 2, sy + sh + 4, ledW, ledH);

  // Tiny stand base
  ctx.fillStyle = "rgba(148,163,184,0.12)";
  ctx.fillRect(bx + bw / 2 - 6, by + bh + 4, 12, 4);
}

// Draw a single monitor tile at a specified rectangle (used for EXTRA PC areas)
function drawMonitorTile(ctx, x, y, w, h) {
  const safeW = Math.max(2, w);
  const safeH = Math.max(2, h);
  const r = Math.min(8, Math.floor(Math.min(safeW, safeH) / 2));
  // bezel
  ctx.fillStyle = "rgba(8,10,14,0.9)";
  ctx.strokeStyle = "rgba(71,85,105,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  try {
    ctx.roundRect(x, y, safeW, safeH, r);
  } catch(e) {
    ctx.rect(x, y, safeW, safeH);
  }
  ctx.fill();
  ctx.stroke();

  // screen
  const pad = Math.min(4, Math.floor(safeW * 0.12), Math.floor(safeH * 0.12));
  const sx = x + pad;
  const sy = y + pad;
  const sw = Math.max(1, safeW - pad * 2);
  const sh = Math.max(1, safeH - pad * 2 - 2);
  const g = ctx.createLinearGradient(sx, sy, sx, sy + sh);
  g.addColorStop(0, "rgba(10,20,30,0.96)");
  g.addColorStop(1, "rgba(8,18,28,0.8)");
  ctx.fillStyle = g;
  ctx.beginPath();
  try {
    ctx.roundRect(sx, sy, sw, sh, Math.max(0, r - 2));
  } catch(e) {
    ctx.rect(sx, sy, sw, sh);
  }
  ctx.fill();

  // small bright strip
  ctx.fillStyle = "rgba(56,189,248,0.18)";
  ctx.fillRect(sx + sw * 0.25, sy + sh + 1, sw * 0.5, 2);
}

function drawRearFacingMonitorTile(ctx, cx, cy) {
  drawMonitorTile(ctx, cx - 11, cy - 3, 22, 13);

  ctx.save();
  ctx.fillStyle = "rgba(148,163,184,0.24)";
  ctx.fillRect(cx - 7, cy + 12, 14, 3);
  ctx.fillStyle = "rgba(226,232,240,0.22)";
  ctx.fillRect(cx - 10, cy + 17, 20, 4);
  ctx.restore();
}

function drawBlueprintTag(ctx, label, x, y, options = {}) {
  const {
    tone = "blue",
    align = "center",
    size = 6.5,
    paddingX = 5,
    paddingY = 3,
    lineHeight = size + 2,
    alpha = 0.9
  } = options;
  const palette = {
    blue: ["rgba(15, 23, 42, 0.82)", "rgba(96, 165, 250, 0.42)", "rgba(191, 219, 254, 0.92)"],
    teal: ["rgba(6, 78, 59, 0.58)", "rgba(45, 212, 191, 0.42)", "rgba(153, 246, 228, 0.94)"],
    amber: ["rgba(120, 53, 15, 0.58)", "rgba(251, 191, 36, 0.50)", "rgba(254, 243, 199, 0.95)"],
    red: ["rgba(127, 29, 29, 0.58)", "rgba(248, 113, 113, 0.48)", "rgba(254, 202, 202, 0.95)"],
    violet: ["rgba(88, 28, 135, 0.52)", "rgba(217, 70, 239, 0.44)", "rgba(245, 208, 254, 0.95)"],
    slate: ["rgba(15, 23, 42, 0.74)", "rgba(148, 163, 184, 0.35)", "rgba(226, 232, 240, 0.86)"]
  }[tone] || ["rgba(15, 23, 42, 0.80)", "rgba(148, 163, 184, 0.38)", "rgba(226, 232, 240, 0.90)"];
  const lines = String(label).toUpperCase().split("\n");

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.font = `800 ${size}px var(--font-sans)`;
  const textW = Math.max(...lines.map((line) => ctx.measureText(line).width));
  const w = textW + paddingX * 2;
  const h = lines.length * lineHeight + paddingY * 2 - 1;
  let left = x - w / 2;
  if (align === "left") left = x;
  if (align === "right") left = x - w;
  const top = y - h / 2;

  ctx.fillStyle = palette[0];
  ctx.strokeStyle = palette[1];
  ctx.lineWidth = 0.9;
  ctx.beginPath();
  ctx.roundRect(left, top, w, h, 3);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = palette[2];
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  lines.forEach((line, index) => {
    const ty = top + paddingY + lineHeight / 2 + index * lineHeight;
    ctx.fillText(line, left + w / 2, ty);
  });
  ctx.restore();
}

function drawCurrentRearExtraPcArea(ctx, layout) {
  if (!layout.extraPcs || !layout.extraPcs.length) return;

  ctx.save();
  const centers = layout.extraPcs.map(([x, y]) => visualCenter(x, y));
  const left = Math.min(...centers.map((pos) => pos.x)) - 23;
  const right = Math.max(...centers.map((pos) => pos.x)) + 23;
  const centerY = centers[0].y;

  ctx.strokeStyle = "rgba(96, 165, 250, 0.58)";
  ctx.lineWidth = 3.4;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(left, centerY + 3);
  ctx.lineTo(right, centerY + 3);
  ctx.stroke();

  drawBlueprintTag(ctx, "Extra PCs", (left + right) / 2, centerY - 18, { tone: "blue", size: 6.5 });

  centers.forEach((pos) => drawRearFacingMonitorTile(ctx, pos.x, pos.y + 1));
  ctx.restore();
}

// Draw a single large data rack spanning multiple rows (cell-based positioning)
function drawBigDataRack(ctx, cellX, topRow, rowSpan) {
  // compute pixel bounds from cell coordinates
  const top = visualCenter(cellX, topRow).y - CELL / 2;
  const bottom = visualCenter(cellX, topRow + rowSpan - 1).y + CELL / 2;
  const height = bottom - top;
  const center = visualCenter(cellX, topRow + Math.floor(rowSpan / 2));
  const width = CELL - 12;
  const px = center.x - width / 2;
  const py = top + 6;

  // Rack body
  ctx.fillStyle = "rgba(20,20,28,0.96)";
  ctx.strokeStyle = "rgba(71,85,105,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(px, py, width, height - 12, 4);
  ctx.fill();
  ctx.stroke();

  // 1U slots across the rack
  ctx.strokeStyle = "rgba(255,255,255,0.03)";
  const slotH = 8;
  for (let oy = py + 8; oy < py + height - 24; oy += slotH + 4) {
    ctx.fillStyle = "rgba(255,255,255,0.015)";
    ctx.fillRect(px + 6, oy, width - 12, slotH);
    ctx.strokeRect(px + 6, oy, width - 12, slotH);
  }

  // Tall status LED column
  const ledX = px + width - 8;
  for (let i = 0; i < 6; i++) {
    const ly = py + 10 + i * 12;
    ctx.beginPath();
    ctx.fillStyle = i % 3 === 0 ? "#10b981" : i % 3 === 1 ? "#f59e0b" : "#ef4444";
    ctx.arc(ledX, ly, 2.4, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawInstructorDeskBlueprint(ctx, x, y, index) {
  // In the real room, the front wall has a whiteboard, not a big desk.
  // The instructor desk cells just represent the narrow area in front
  // of the whiteboard — render as a subtle floor marker, not a desk block.
  const { x: cx, y: cy } = visualCenter(x, y);
  const px = cx - CELL / 2;
  const py = cy - CELL / 2;
  
  ctx.fillStyle = "rgba(30, 41, 59, 0.15)";
  ctx.strokeStyle = "rgba(71, 85, 105, 0.15)";
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  ctx.roundRect(px + 4, py + 4, CELL - 8, CELL - 8, 3);
  ctx.fill();
  ctx.stroke();
}

function drawWhiteboard(ctx, layout) {
  ctx.save();

  // Board and TV centered on the front wall per the hand-drawn layout.
  const isMod = state && state.mode === "modified";
  const wbW = isMod ? 130 : 170;
  const wbX = LAB_RIGHT / 2 - wbW / 2;
  const wbY = 3;
  const wbH = CELL * 0.48;

  // Whiteboard surface (light panel on dark background)
  ctx.fillStyle = "rgba(220, 230, 240, 0.12)";
  ctx.strokeStyle = "rgba(148, 163, 184, 0.28)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(wbX, wbY, wbW, wbH, 3);
  ctx.fill();
  ctx.stroke();

  // Marker scribbles (subtle, to suggest real content)
  ctx.strokeStyle = "rgba(15,23,42,0.55)";
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 3; i++) {
    ctx.beginPath();
    const sx = wbX + 10 + i * 30;
    ctx.moveTo(sx, wbY + wbH / 2 - 6);
    ctx.quadraticCurveTo(sx + 8, wbY + wbH / 2 - 4 + i, sx + 18, wbY + wbH / 2 + 4 - i);
    ctx.stroke();
  }

  // Narrow wooden ledge below whiteboard
  ctx.fillStyle = "rgba(120, 90, 50, 0.2)";
  ctx.fillRect(wbX, wbY + wbH, wbW, 2.5);

  // TV/Monitor centered on the whiteboard: draw bezel + screen content
  const tvW = CELL * 1.6;
  const tvH = CELL * 0.34;
  const tvX = wbX + wbW / 2 - tvW / 2;
  const tvY = wbY + (wbH - tvH) / 2;

  // Bezel shadow
  ctx.fillStyle = "rgba(5,8,15,0.85)";
  ctx.beginPath();
  ctx.roundRect(tvX - 2, tvY - 2, tvW + 4, tvH + 4, 3);
  ctx.fill();

  // Screen
  const screenGrad = ctx.createLinearGradient(tvX, tvY, tvX, tvY + tvH);
  screenGrad.addColorStop(0, "rgba(10,20,30,0.95)");
  screenGrad.addColorStop(1, "rgba(10,30,40,0.8)");
  ctx.fillStyle = screenGrad;
  ctx.beginPath();
  ctx.roundRect(tvX, tvY, tvW, tvH, 2);
  ctx.fill();

  // Soft indicator text on screen
  ctx.fillStyle = "rgba(191, 219, 254, 0.85)";
  ctx.font = "700 8px var(--font-sans)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("TV", tvX + tvW / 2, tvY + tvH / 2 - 2);

  // Tiny stand below TV
  ctx.fillStyle = "rgba(148,163,184,0.12)";
  ctx.fillRect(tvX + tvW / 2 - 6, tvY + tvH + 3, 12, 3);

  drawBlueprintTag(ctx, "White Board", wbX + 34, wbY + wbH / 2, {
    tone: "slate",
    size: 5.4,
    paddingX: 4,
    paddingY: 2
  });

  ctx.restore();
}

function drawStaircaseBlueprint(ctx, x, y) {
  const { x: cx, y: cy } = visualCenter(x, y);
  const px = cx - CELL / 2;
  const py = cy - CELL / 2;
  
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
}

function storagePos(layout) {
  const raw = layout.storage || layout.locker;
  if (!raw) return null;
  return Array.isArray(raw) ? raw : [raw[0], raw[1]];
}

function drawUnifiedStorageBlueprint(ctx, layout) {
  const storage = storagePos(layout);
  if (!storage) return;

  const isMod = state && state.mode === "modified";
  const label = "BAGS & SHELVES";

  if (isMod) {
    const left = visualCenter(storage[0], storage[1]);
    const x = left.x - CELL / 2 + 4;
    const y = left.y - CELL / 2 + 4;
    const w = CELL * 1.25;
    const h = CELL - 8;

    ctx.save();
    ctx.fillStyle = "rgba(245, 158, 11, 0.10)";
    ctx.strokeStyle = "rgba(251, 191, 36, 0.68)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 4);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = "rgba(203, 213, 225, 0.32)";
    for (let offset = 10; offset <= h - 8; offset += 5) {
      ctx.beginPath();
      ctx.moveTo(x + 6, y + offset);
      ctx.lineTo(x + w - 6, y + offset);
      ctx.stroke();
    }

    drawBlueprintTag(ctx, "Bags\nShelves", x + w / 2, y - 40, {
      tone: "amber",
      size: 5.5,
      paddingX: 3,
      paddingY: 2,
      lineHeight: 6
    });
    ctx.restore();
    return;
  }

  drawStorageBlueprint(ctx, storage, label, "combined");
}

function drawStorageBlueprint(ctx, pos, label, tone = "amber") {
  if (!pos) return;
  const { x: cx, y: cy } = visualCenter(pos[0], pos[1]);
  const px = cx - CELL / 2;
  const py = cy - CELL / 2;
  const isShelf = tone === "shelf";
  const isCombined = tone === "combined";
  const fill = isCombined
    ? "rgba(245, 158, 11, 0.10)"
    : isShelf
      ? "rgba(148, 163, 184, 0.10)"
      : "rgba(245, 158, 11, 0.12)";
  const stroke = isCombined
    ? "rgba(251, 191, 36, 0.68)"
    : isShelf
      ? "rgba(203, 213, 225, 0.54)"
      : "rgba(245, 158, 11, 0.72)";
  const text = isCombined
    ? "rgba(254, 243, 199, 0.94)"
    : isShelf
      ? "rgba(226, 232, 240, 0.86)"
      : "rgba(245, 158, 11, 0.92)";

  ctx.save();
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.roundRect(px + 5, py + 5, CELL - 10, CELL - 10, 4);
  ctx.fill();
  ctx.stroke();

  if (isShelf || isCombined) {
    ctx.strokeStyle = isCombined ? "rgba(203, 213, 225, 0.32)" : "rgba(203, 213, 225, 0.35)";
    for (let offset = 12; offset <= 22; offset += 5) {
      ctx.beginPath();
      ctx.moveTo(px + 9, py + offset);
      ctx.lineTo(px + CELL - 9, py + offset);
      ctx.stroke();
    }
  }
  if (!isShelf) {
    ctx.strokeStyle = isCombined ? "rgba(245, 158, 11, 0.30)" : "rgba(245, 158, 11, 0.35)";
    ctx.beginPath();
    ctx.moveTo(px + CELL / 2, py + 8);
    ctx.lineTo(px + CELL / 2, py + CELL - 8);
    ctx.stroke();
  }

  if (isCombined) {
    drawBlueprintTag(ctx, "Bags\nShelves", px + CELL / 2, py - 1, {
      tone: "amber",
      size: 5.2,
      paddingX: 3,
      paddingY: 2,
      lineHeight: 5.8
    });
  } else {
    ctx.fillStyle = text;
    ctx.font = "800 7.5px var(--font-sans)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(label).toUpperCase(), px + CELL / 2, py + CELL / 2);
  }
  ctx.restore();
}

function drawExitDoorBlueprint(ctx, x, y, label) {
  const { x: cx, y: cy } = visualCenter(x, y);
  const px = cx - CELL / 2;
  const py = cy - CELL / 2;
  
  // Slate blueprint door body
  ctx.fillStyle = "#0f172a";
  ctx.strokeStyle = "rgba(148, 163, 184, 0.8)";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.roundRect(px + 3, py + 3, CELL - 6, CELL - 6, 2.5);
  ctx.fill();
  ctx.stroke();
  
  const displayLabel = label === "ENTR" ? "ENTRANCE" : (label || "EXIT");
  
  // Blue sign board at the top of the door (above the glass window)
  const signW = displayLabel === "ENTRANCE" ? 27 : 21;
  ctx.fillStyle = "#1e40af";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.roundRect(px + CELL / 2 - signW / 2, py + 6, signW, 8, 1);
  ctx.fill();
  ctx.stroke();
  
  // Sign text
  ctx.fillStyle = "#ffffff";
  ctx.font = "800 4.8px var(--font-sans)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(displayLabel, px + CELL / 2, py + 10);

  // Door glass pane window (below the sign) - cyan blueprint glow
  const glassW = 8;
  const glassH = 11;
  const glassX = px + CELL / 2 - glassW / 2;
  const glassY = py + 16;
  ctx.fillStyle = "rgba(56, 189, 248, 0.35)";
  ctx.fillRect(glassX, glassY, glassW, glassH);
  
  // Door knob (small silver circle on the left edge)
  ctx.fillStyle = "#cbd5e1";
  ctx.strokeStyle = "#475569";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.arc(px + 6.5, py + 19, 1.8, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  // If entrance door, draw the tiny yellow warning sign on the glass window
  if (displayLabel === "ENTRANCE") {
    const warnW = 6;
    const warnH = 4.5;
    const warnX = px + CELL / 2 - warnW / 2;
    const warnY = py + 19;
    ctx.fillStyle = "#facc15"; // Yellow
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 0.5;
    ctx.fillRect(warnX, warnY, warnW, warnH);
    ctx.strokeRect(warnX, warnY, warnW, warnH);
    
    // Small black indicator lines on the warning sign
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 0.6;
    ctx.beginPath();
    ctx.moveTo(warnX + 1.2, warnY + 2.2);
    ctx.lineTo(warnX + warnW - 1.2, warnY + 2.2);
    ctx.stroke();
  }
}

function drawDoorSwingBlueprint(ctx, exitCell) {
  const { x: cx, y: cy } = visualCenter(exitCell[0], exitCell[1]);
  
  ctx.strokeStyle = "rgba(16, 185, 129, 0.4)";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.arc(cx + CELL / 2, cy, CELL * 0.58, -Math.PI / 2, Math.PI / 2);
  ctx.stroke();
  ctx.setLineDash([]);
  
  // Solid door frame leaf angle
  ctx.strokeStyle = "rgba(16, 185, 129, 0.8)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx + CELL / 2, cy);
  ctx.lineTo(cx + CELL / 2 + CELL * 0.42, cy - CELL * 0.42);
  ctx.stroke();
}

function drawHallwayWall(ctx, layout) {
  const wallX = LAB_RIGHT;
  ctx.save();
  
  // Solid wall line at lab/hallway boundary (thick concrete wall line)
  ctx.strokeStyle = "rgba(148, 163, 184, 0.75)";
  ctx.lineWidth = 5;
  
  const exitRows = new Set([layout.frontExit[1], layout.backExit[1]]);
  for (let y = 0; y < layout.rows; y++) {
    if (exitRows.has(y)) continue; // Skip door openings
    ctx.beginPath();
    ctx.moveTo(wallX, y * CELL);
    ctx.lineTo(wallX, (y + 1) * CELL);
    ctx.stroke();
  }
  
  // Dark slate wainscoting trim line right next to it (facing the hallway)
  ctx.strokeStyle = "rgba(30, 41, 59, 0.95)";
  ctx.lineWidth = 2;
  for (let y = 0; y < layout.rows; y++) {
    if (exitRows.has(y)) continue;
    ctx.beginPath();
    ctx.moveTo(wallX + 2.5, y * CELL);
    ctx.lineTo(wallX + 2.5, (y + 1) * CELL);
    ctx.stroke();
  }
  
  // Horizontal decorative molding trim line running near the top of the wall (facing the hallway)
  ctx.strokeStyle = "rgba(30, 41, 59, 0.6)";
  ctx.lineWidth = 0.8;
  for (let y = 0; y < layout.rows; y++) {
    if (exitRows.has(y)) continue;
    ctx.beginPath();
    ctx.moveTo(wallX + 1.2, y * CELL);
    ctx.lineTo(wallX + 1.2, (y + 1) * CELL);
    ctx.stroke();
  }
  
  ctx.restore();
}

function drawPartitionWall(ctx, layout) {
  if (!layout.partitionWall) return;
  ctx.save();

  const passageY = (layout.serviceBayPassage || [7, 10])[1];
  const rows = [...new Set(layout.partitionWall.map(([, y]) => y))].sort((a, b) => a - b);

  ctx.strokeStyle = "rgba(148, 163, 184, 0.75)";
  ctx.lineWidth = 3;
  ctx.setLineDash([5, 3]);

  const isMod = state && state.mode === "modified";
  if (isMod) {
    const serviceY = visualCenter(0, passageY).y - CELL / 2 + 2;
    const left = visualCenter(0, passageY).x - CELL / 2 + 6;
    const right = visualCenter(7, passageY).x + CELL / 2 - 6;
    const passage = visualCenter((layout.serviceBayPassage || [6, 10])[0], passageY);

    ctx.beginPath();
    ctx.moveTo(left, serviceY);
    ctx.lineTo(passage.x - 18, serviceY);
    ctx.moveTo(passage.x + 18, serviceY);
    ctx.lineTo(right, serviceY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
    return;
  }

  const wallX = isMod ? 58 : SERVICE_X + 2;
  const col = isMod ? 0 : 7;

  for (const y of rows) {
    if (y === passageY) continue;
    const { y: cy } = visualCenter(col, y);
    ctx.beginPath();
    ctx.moveTo(wallX, cy - CELL / 2 + 2);
    ctx.lineTo(wallX, cy + CELL / 2 - 2);
    ctx.stroke();
  }

  ctx.setLineDash([]);
  ctx.restore();
}

function drawServiceBaySketchPath(ctx, layout) {
  ctx.save();

  const isMod = state && state.mode === "modified";
  const passage = layout.serviceBayPassage || (isMod ? [6, 10] : [7, 10]);
  const passageCenter = visualCenter(passage[0], passage[1]);
  if (isMod) {
    drawBlueprintTag(ctx, "Pass", passageCenter.x, passageCenter.y - 16, {
      tone: "teal",
      size: 5.6,
      paddingX: 4,
      paddingY: 2
    });
    ctx.restore();
    return;
  }

  const rackMid = visualCenter(passage[0], isMod ? 6.5 : 4);
  const assistantMid = visualCenter(passage[0], isMod ? 8.5 : 8);
  const rackBottom = visualCenter(passage[0], isMod ? 7 : 6);
  
  const bayLeft = isMod ? 6 : SERVICE_X;
  const bayRight = isMod ? 58 : SERVICE_X + SERVICE_W - 6;

  // Horizontal divider between custodian/data rack and student assistant (per sketch).
  ctx.strokeStyle = "rgba(148, 163, 184, 0.85)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(bayLeft + 4, rackBottom.y + CELL / 2);
  ctx.lineTo(bayRight, rackBottom.y + CELL / 2);
  ctx.stroke();

  // Sketch egress path: descend rack -> assistant bay -> passage into the lab.
  ctx.strokeStyle = "rgba(59, 130, 246, 0.55)";
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 4]);
  ctx.beginPath();
  ctx.moveTo(rackMid.x, rackMid.y + 8);
  ctx.lineTo(assistantMid.x, assistantMid.y - 6);
  ctx.lineTo(passageCenter.x, passageCenter.y);
  ctx.lineTo(visualCenter(isMod ? 1 : 6, 10).x, passageCenter.y);
  ctx.stroke();
  ctx.setLineDash([]);

  drawBlueprintTag(ctx, "Passage", passageCenter.x, passageCenter.y + 2, {
    tone: "teal",
    size: 5.8,
    paddingX: 4,
    paddingY: 2
  });

  ctx.restore();
}

function drawFireExtinguisherBlueprint(ctx, pos) {
  if (!pos) return;
  const { x: cx, y: cy } = visualCenter(pos[0], pos[1]);
  const isMod = state && state.mode === "modified";
  let iconX = cx;
  let iconY = cy;

  if (isMod) {
    if (pos[0] === 4 && pos[1] === 0) iconX = cx - 14;
    if (pos[0] === 6 && pos[1] === 10) {
      iconX = cx + 18;
      iconY = cy - 8;
    }
    if (pos[0] === 7 && pos[1] === 10) {
      iconX = cx + 12;
      iconY = cy + 10;
    }
  }

  ctx.save();

  ctx.fillStyle = isMod ? "rgba(248, 113, 113, 0.06)" : "rgba(248, 113, 113, 0.10)";
  ctx.strokeStyle = isMod ? "rgba(248, 113, 113, 0.40)" : "rgba(248, 113, 113, 0.55)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(iconX, iconY, isMod ? 8 : 10, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  // Red cylinder body
  ctx.fillStyle = "#f43f5e";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.roundRect(iconX - 2.5, iconY - 5, 5, 10, 1.5);
  ctx.fill();
  ctx.stroke();
  
  // Extinguisher black nozzle head
  ctx.fillStyle = "#475569";
  ctx.beginPath();
  ctx.rect(iconX - 3.5, iconY - 7, 7, 2);
  ctx.fill();

  ctx.fillStyle = "#fff";
  ctx.font = "800 5px var(--font-sans)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("FE", iconX, iconY + 1);

  ctx.restore();
}

function drawClearEgressLanes(ctx, layout) {
  if (!(state && state.mode === "modified")) return;

  ctx.save();
  ctx.fillStyle = "rgba(16, 185, 129, 0.06)";
  ctx.strokeStyle = "rgba(16, 185, 129, 0.22)";
  ctx.lineWidth = 1;
  ctx.setLineDash([7, 5]);

  const centerX = visualCenter(4, 5).x;
  ctx.beginPath();
  ctx.roundRect(centerX - 16, CELL * 0.9, 32, CELL * 10.3, 8);
  ctx.fill();
  ctx.stroke();

  ctx.setLineDash([]);
  ctx.restore();
}

function drawStudentWorkstationAreaLabel(ctx) {
  const isMod = state && state.mode === "modified";
  const x = isMod ? LAB_RIGHT / 2 : 122;
  const y = isMod ? 49 : 49;
  drawBlueprintTag(ctx, isMod ? "Student Workstations\n36 PCs" : "Student Workstations", x, y, {
    tone: "blue",
    size: 5.8,
    paddingX: 5,
    paddingY: 2,
    lineHeight: 6.4,
    alpha: 0.82
  });
}

function drawLabeledBlock(ctx, x, y, w, h, label, fill, stroke, align = "center") {
  ctx.save();
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 4);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "rgba(226, 232, 240, 0.45)"; // Faint text so agents pop
  const isVertical = w < h;
  ctx.font = isVertical ? "800 7.5px var(--font-sans)" : "800 9px var(--font-sans)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  const lines = label.split("\n");
  const spacing = isVertical ? 9 : 10;

  let startY;
  if (align === "top") {
    startY = y + 14;
  } else if (align === "bottom") {
    startY = y + h - (lines.length - 1) * spacing - 14;
  } else {
    startY = y + h / 2 - (lines.length - 1) * (spacing / 2);
  }

  lines.forEach((line, index) => {
    ctx.fillText(line, x + w / 2, startY + index * spacing);
  });
  ctx.restore();
}

function drawTeacherArea(ctx) {
  ctx.save();
  const isMod = state && state.mode === "modified";
  const teacher = visualCenter(isMod ? 6 : 7, 0);
  
  if (isMod) {
    ctx.fillStyle = "rgba(59, 130, 246, 0.16)";
    ctx.strokeStyle = "rgba(59, 130, 246, 0.55)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(teacher.x - 33, teacher.y - 15, 66, 30, 4);
    ctx.fill();
    ctx.stroke();

    drawBlueprintTag(ctx, "Professor", teacher.x, teacher.y - 10, {
      tone: "blue",
      size: 5.5,
      paddingX: 4,
      paddingY: 2
    });
  } else {
    ctx.fillStyle = "rgba(59, 130, 246, 0.16)";
    ctx.strokeStyle = "rgba(59, 130, 246, 0.55)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(teacher.x - 92, teacher.y - 15, 66, 30, 4);
    ctx.fill();
    ctx.stroke();

    drawBlueprintTag(ctx, "Professor", teacher.x - 64, teacher.y - 9, {
      tone: "blue",
      size: 5.5,
      paddingX: 4,
      paddingY: 2
    });
    drawMonitorTile(ctx, teacher.x - 76, teacher.y - 2, 24, 13);
  }
  ctx.restore();
}

function drawWorkstationBenches(ctx, layout) {
  ctx.save();
  ctx.strokeStyle = "rgba(96, 165, 250, 0.55)";
  ctx.lineWidth = 3.4;
  ctx.lineCap = "round";

  if (state && state.mode === "modified") {
    layout.workstationRows.forEach((row) => {
      const y = visualCenter(0, row).y;
      const rowCells = layout.workstations.filter(([, cellY]) => cellY === row);
      const hasLeftTable = rowCells.some(([x]) => x >= 0 && x <= 3);
      const hasRightTable = rowCells.some(([x]) => x >= 4 && x <= 7);

      if (hasLeftTable) {
        ctx.beginPath();
        ctx.moveTo(20, y);
        ctx.lineTo(164, y);
        ctx.stroke();
      }

      if (hasRightTable) {
        ctx.beginPath();
        ctx.moveTo(200, y);
        ctx.lineTo(344, y);
        ctx.stroke();
      }
    });
  } else {
    layout.workstationRows.forEach((row) => {
      const y = visualCenter(0, row).y;
      ctx.beginPath();
      ctx.moveTo(WORKSTATION_X.get(0) - 20, y);
      ctx.lineTo(WORKSTATION_X.get(2) + 20, y);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(WORKSTATION_X.get(4) - 20, y);
      ctx.lineTo(WORKSTATION_X.get(6) + 20, y);
      ctx.stroke();
    });
  }

  ctx.restore();
}

function drawRearServiceBayBlueprint(ctx, layout) {
  ctx.save();

  const serviceLeft = visualCenter(0, 11);
  const serviceRight = visualCenter(5, 11);
  const serviceX = serviceLeft.x - CELL / 2 + 4;
  const serviceY = serviceLeft.y - CELL / 2 + 4;
  const serviceW = serviceRight.x + CELL / 2 - serviceX - 4;
  const serviceH = CELL - 8;
  const dividerX = (visualCenter(2, 11).x + visualCenter(3, 11).x) / 2;

  ctx.fillStyle = "rgba(249, 115, 22, 0.10)";
  ctx.strokeStyle = "rgba(249, 115, 22, 0.62)";
  ctx.lineWidth = 1.3;
  ctx.beginPath();
  ctx.roundRect(serviceX, serviceY, serviceW, serviceH, 5);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "rgba(20, 184, 166, 0.12)";
  ctx.beginPath();
  ctx.roundRect(dividerX, serviceY + 1, serviceX + serviceW - dividerX - 1, serviceH - 2, 4);
  ctx.fill();

  ctx.strokeStyle = "rgba(148, 163, 184, 0.32)";
  ctx.beginPath();
  ctx.moveTo(dividerX, serviceY + 5);
  ctx.lineTo(dividerX, serviceY + serviceH - 5);
  ctx.stroke();

  drawBlueprintTag(ctx, "Custodian\nData Rack", serviceX + (dividerX - serviceX) / 2, serviceY - 24, {
    tone: "amber",
    size: 5.4,
    paddingX: 4,
    paddingY: 2,
    lineHeight: 5.9
  });

  const passage = visualCenter((layout.serviceBayPassage || [6, 11])[0], (layout.serviceBayPassage || [6, 11])[1]);
  ctx.fillStyle = "rgba(16, 185, 129, 0.08)";
  ctx.strokeStyle = "rgba(16, 185, 129, 0.45)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.roundRect(passage.x - 16, passage.y - CELL / 2 + 4, 32, CELL - 8, 5);
  ctx.fill();
  ctx.stroke();

  drawBlueprintTag(ctx, "Student\nAssistant", dividerX + (serviceX + serviceW - dividerX) / 2, serviceY - 24, {
    tone: "teal",
    size: 5.4,
    paddingX: 4,
    paddingY: 2,
    lineHeight: 5.9
  });

  drawUnifiedStorageBlueprint(ctx, layout);
  ctx.restore();
}

function drawEntranceAreaBlueprint(ctx, layout) {
  ctx.save();

  const isMod = state && state.mode === "modified";
  if (isMod) {
    drawRearServiceBayBlueprint(ctx, layout);
    ctx.restore();
    return;
  }

  // Current sketch basis: data rack at the right, custodian table beside it.
  const rackCol = 7;
  const rackTopY = visualCenter(rackCol, 2).y - CELL / 2 + 7;
  const rackX = SERVICE_X + SERVICE_W - 20;
  const rackH = CELL * 2.15;
  ctx.fillStyle = "rgba(20,20,28,0.96)";
  ctx.strokeStyle = "rgba(71,85,105,0.65)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(rackX, rackTopY, 16, rackH, 3);
  ctx.fill();
  ctx.stroke();

  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  for (let oy = rackTopY + 8; oy < rackTopY + rackH - 8; oy += 10) {
    ctx.strokeRect(rackX + 3, oy, 10, 6);
  }

  drawBlueprintTag(ctx, "Data\nRack", rackX + 8, rackTopY + 10, {
    tone: "slate",
    size: 5.1,
    paddingX: 3,
    paddingY: 2,
    lineHeight: 5.6
  });

  const custodianTable = {
    x: SERVICE_X + 12,
    y: visualCenter(rackCol, 4).y + 5
  };
  ctx.fillStyle = "rgba(217, 70, 239, 0.08)";
  ctx.strokeStyle = "rgba(217, 70, 239, 0.45)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(custodianTable.x - 11, custodianTable.y - 45, 24, 96, 5);
  ctx.fill();
  ctx.stroke();

  drawBlueprintTag(ctx, "Custodian\nTable", custodianTable.x + 1, custodianTable.y - 55, {
    tone: "violet",
    size: 5.1,
    paddingX: 3,
    paddingY: 2,
    lineHeight: 5.6
  });
  drawMonitorTile(ctx, custodianTable.x - 9, custodianTable.y - 8, 18, 12);
  drawMonitorTile(ctx, custodianTable.x - 9, custodianTable.y + 20, 18, 12);

  // Student assistant bay: small desk with two monitor icons
  const assistX = rackCol;
  // Draw subtle assistant area background
  const assistCenter = visualCenter(assistX, isMod ? 8.5 : 8);
  ctx.beginPath();
  ctx.fillStyle = "rgba(20, 184, 166, 0.08)";
  ctx.roundRect(
    assistCenter.x - SERVICE_W / 2,
    assistCenter.y - (isMod ? CELL : CELL * 1.5) + 6,
    SERVICE_W,
    isMod ? CELL * 1.8 : CELL * 2.8,
    6
  );
  ctx.fill();
  ctx.strokeStyle = "rgba(20, 184, 166, 0.5)";
  ctx.lineWidth = 1;
  ctx.stroke();

  drawBlueprintTag(ctx, "Student\nAssistant", assistCenter.x, assistCenter.y - CELL + 9, {
    tone: "teal",
    size: 5.2,
    paddingX: 4,
    paddingY: 2,
    lineHeight: 5.8
  });

  // Student assistant: single monitor
  const monY = visualCenter(assistX, isMod ? 8 : 8).y - 6;
  const mx = assistCenter.x;
  drawMonitorTile(ctx, mx - 10, monY - 6, 20, 12);

  drawUnifiedStorageBlueprint(ctx, layout);

  ctx.restore();
}

function drawHallwayLabels(ctx, layout) {
  const hallX = LAB_RIGHT;
  const cx = hallX + (HALL_RIGHT - LAB_RIGHT) / 2; // Centered in hallway
  ctx.save();
  
  // 1. Right-side concrete balcony wall (grey base, dark slate inside trim)
  ctx.fillStyle = "rgba(148, 163, 184, 0.75)";
  ctx.fillRect(HALL_RIGHT - 8, 0, 8, MAP_H);
  
  ctx.fillStyle = "rgba(30, 41, 59, 0.95)";
  ctx.fillRect(HALL_RIGHT - 10, 0, 2, MAP_H);

  // 2. Stainless steel handrail on top of balcony wall
  ctx.strokeStyle = "#cbd5e1"; // Metallic silver/grey
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(HALL_RIGHT - 4, 0);
  ctx.lineTo(HALL_RIGHT - 4, MAP_H);
  ctx.stroke();

  // Railing support posts (horizontal connector plates/brackets)
  ctx.strokeStyle = "#475569";
  ctx.lineWidth = 1.2;
  for (let y = 0; y < MAP_H; y += CELL * 2) {
    ctx.beginPath();
    ctx.moveTo(HALL_RIGHT - 8, y + CELL);
    ctx.lineTo(HALL_RIGHT, y + CELL);
    ctx.stroke();
  }

  // 3. Directional labels in the walkway (centered on cx + 8 to avoid door swings)
  drawBlueprintTag(ctx, "Fire Exit", cx + 8, 20, {
    tone: "red",
    size: 6.2,
    paddingX: 5,
    paddingY: 2
  });
  
  ctx.strokeStyle = "#ef4444";
  ctx.lineWidth = 1.8;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(cx + 8, 48);
  ctx.lineTo(cx + 8, 32);
  ctx.lineTo(cx + 4, 36);
  ctx.moveTo(cx + 8, 32);
  ctx.lineTo(cx + 12, 36);
  ctx.stroke();

  // Bottom direction: "entrance" with a DOWN arrow
  drawBlueprintTag(ctx, "Entrance", cx + 8, MAP_H - 20, {
    tone: "slate",
    size: 6.2,
    paddingX: 5,
    paddingY: 2
  });
  
  ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
  ctx.lineWidth = 1.8;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(cx + 8, MAP_H - 48);
  ctx.lineTo(cx + 8, MAP_H - 32);
  ctx.lineTo(cx + 4, MAP_H - 36);
  ctx.moveTo(cx + 8, MAP_H - 32);
  ctx.lineTo(cx + 12, MAP_H - 36);
  ctx.stroke();

  // 4. Vertical label: "HALLWAY" (centered in the middle of the hallway)
  ctx.save();
  ctx.translate(cx - 4, MAP_H / 2);
  ctx.rotate(Math.PI / 2);
  drawBlueprintTag(ctx, "Hallway", 0, 0, {
    tone: "slate",
    size: 6.2,
    paddingX: 5,
    paddingY: 2,
    alpha: 0.72
  });
  ctx.restore();

  ctx.restore();
}

function drawMap() {
  const ctx = getDprContext(els.map, MAP_W, MAP_H);
  const layout = state.layout;
  ctx.clearRect(0, 0, MAP_W, MAP_H);

  try {
    // 1. Clean sketch-style background. The visible tile grid is intentionally removed.
    ctx.fillStyle = "rgba(30, 41, 59, 0.38)";
    ctx.fillRect(LAB_LEFT, 0, LAB_RIGHT - LAB_LEFT, MAP_H);
    
    // Fill base hallway color
    ctx.fillStyle = COLORS.hall;
    ctx.fillRect(LAB_RIGHT, 0, HALL_RIGHT - LAB_RIGHT, MAP_H);

    // --- Draw Blueprint Tiled Pattern ---
    ctx.save();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.07)"; // Subtle light blue grout line
    ctx.lineWidth = 1;
    
    // Horizontal grout lines
    for (let y = 0; y <= MAP_H; y += CELL) {
      ctx.beginPath();
      ctx.moveTo(LAB_RIGHT, y);
      ctx.lineTo(HALL_RIGHT, y);
      ctx.stroke();
    }
    
    // Vertical grout lines dividing hallway into 3 tiled columns (width 82 is divided)
    const vertCols = [LAB_RIGHT + 27, LAB_RIGHT + 54];
    for (const x of vertCols) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, MAP_H);
      ctx.stroke();
    }

    // --- Add Glossy Reflection Overlay ---
    // Gradient from right (open balcony light source) to left (solid wall)
    const glossGrad = ctx.createLinearGradient(HALL_RIGHT, 0, LAB_RIGHT, 0);
    glossGrad.addColorStop(0.0, "rgba(56, 189, 248, 0.14)"); // Light blue balcony glow
    glossGrad.addColorStop(0.35, "rgba(56, 189, 248, 0.05)");
    glossGrad.addColorStop(1.0, "rgba(56, 189, 248, 0.0)");
    
    ctx.fillStyle = glossGrad;
    ctx.fillRect(LAB_RIGHT, 0, HALL_RIGHT - LAB_RIGHT, MAP_H);
    ctx.restore();

    ctx.strokeStyle = "rgba(56, 189, 248, 0.1)";
    ctx.lineWidth = 1;
    for (const y of layout.workstationRows.map((row) => visualCenter(0, row).y)) {
      if (state && state.mode === "modified") {
        ctx.beginPath();
        ctx.moveTo(50, y);
        ctx.lineTo(182, y);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(210, y);
        ctx.lineTo(342, y);
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.moveTo(LAB_LEFT + 8, y);
        ctx.lineTo(WORKSTATION_X.get(2) + 26, y);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(WORKSTATION_X.get(4) - 26, y);
        ctx.lineTo(WORKSTATION_X.get(6) + 26, y);
        ctx.stroke();
      }
    }

    // 2. Blueprint outline for Classroom lab bounds
    ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
    ctx.lineWidth = 2.5;
    ctx.strokeRect(LAB_LEFT, 0, LAB_RIGHT - LAB_LEFT, MAP_H);
    ctx.lineWidth = 1;

    // 3. Hallway wall and partition wall
    drawHallwayWall(ctx, layout);
    drawPartitionWall(ctx, layout);
    drawServiceBaySketchPath(ctx, layout);
    drawHallwayLabels(ctx, layout);

    // 4. Thermal Heatmap Congestion Bloom
    drawClearEgressLanes(ctx, layout);
    drawHeatmap(ctx, layout);

    // 5. Blueprint elements
    drawWorkstationBenches(ctx, layout);
    layout.workstations.forEach(([x, y]) => drawWorkstationBlueprint(ctx, x, y));
    if (state.mode === "current") {
      drawCurrentRearExtraPcArea(ctx, layout);
    } else {
      layout.extraPcs.forEach(([x, y]) => drawWorkstationBlueprint(ctx, x, y));
    }
    layout.instructorDesk.forEach(([x, y], idx) => drawInstructorDeskBlueprint(ctx, x, y, idx));
    drawWhiteboard(ctx, layout);
    drawStudentWorkstationAreaLabel(ctx);
    drawTeacherArea(ctx);
    drawEntranceAreaBlueprint(ctx, layout);
    
    drawExitDoorBlueprint(ctx, layout.frontExit[0], layout.frontExit[1], "EXIT");
    drawExitDoorBlueprint(ctx, layout.backExit[0], layout.backExit[1], "ENTR");
    
    drawDoorSwingBlueprint(ctx, layout.frontExit);
    drawDoorSwingBlueprint(ctx, layout.backExit);
    
    (layout.fireExtinguishers || []).forEach((pos) => drawFireExtinguisherBlueprint(ctx, pos));
    
    drawStaircaseBlueprint(ctx, layout.frontStairs[0], layout.frontStairs[1]);
    drawStaircaseBlueprint(ctx, layout.emergencyStairs[0], layout.emergencyStairs[1]);
    
    // 6. pulsing fire smoke plume
    const fireCells = state.fireCells && state.fireCells.length ? state.fireCells : [layout.fireOrigin];
    fireCells.forEach(([x, y]) => drawFireSmoke(ctx, x, y));
    
    // 7. Agents avatars
    state.agents.filter((agent) => !agent.exited).forEach((agent) => {
      try {
        drawAgent(ctx, agent);
      } catch (err) {
        console.error(err);
        ctx.fillStyle = "red";
        ctx.font = "14px sans-serif";
        ctx.fillText(err.message, 10, 20);
      }
    });
  } catch (err) {
    ctx.fillStyle = "red";
    ctx.font = "14px sans-serif";
    ctx.fillText("Map Error: " + err.message, 10, 40);
  }
}

function drawHeatmap(ctx, layout) {
  if (!heatVisible) return;
  const max = Math.max(1, state.maxHeat);
  
  ctx.save();
  ctx.globalCompositeOperation = "screen";
  
  Object.entries(state.heatmap).forEach(([key, value]) => {
    const [x, y] = key.split(",").map(Number);
    if (x >= layout.labCols) return;
    
    const { x: cx, y: cy } = visualCenter(x, y);
    // Gradual density accumulation: use a minimum threshold of 10 visits for "hot" cells
    const intensity = Math.min(0.7, value / Math.max(10, max));
    
    // Classic thermal gradient scale: Red core -> Orange -> Yellow edge -> Transparent
    const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, CELL * 1.4);
    grad.addColorStop(0, `rgba(239, 68, 68, ${intensity})`); // Hot core
    grad.addColorStop(0.3, `rgba(249, 115, 22, ${intensity * 0.75})`); // Warning orange
    grad.addColorStop(0.7, `rgba(234, 179, 8, ${intensity * 0.3})`); // Outer yellow glow
    grad.addColorStop(1, "rgba(234, 179, 8, 0)");
    
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, CELL * 1.4, 0, Math.PI * 2);
    ctx.fill();
  });
  
  ctx.restore();
}

function drawFireSmoke(ctx, x, y) {
  const { x: cx, y: cy } = visualCenter(x, y);
  
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
  const { x: cx, y: cy } = agentVisualCenter(agent);
  
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
  
  // 1. Stampede knockdown render (agent.stamped_until > 0 used as proxy via phase)
  const isStamped = agent.phase === "tripped" && agent.stamped_until > 0;
  if (isStamped) {
    const pulse = 1 + 0.25 * Math.abs(Math.sin(Date.now() / 90));
    ctx.fillStyle = "rgba(239, 68, 68, 0.35)";
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(cx, cy, 12 * pulse, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.font = "800 10px var(--font-sans)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("S!", cx, cy);
    return;
  }

  // 2. Tripped or Fainted agent render
  if (agent.phase === "tripped" || agent.phase === "fainted") {
    const isFaint = agent.phase === "fainted";
    const pulse = 1 + 0.18 * Math.sin(Date.now() / (isFaint ? 180 : 120));
    ctx.fillStyle = isFaint ? "rgba(139, 92, 246, 0.28)" : "rgba(244, 63, 94, 0.28)";
    ctx.strokeStyle = isFaint ? COLORS.purple : COLORS.red;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 10.5 * pulse, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    
    ctx.fillStyle = "#ffffff";
    ctx.font = "800 11px var(--font-sans)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(isFaint ? "F" : "!", cx, cy);
    return;
  }
  
  // 2. Human-like avatar (head, torso, legs, arms) for clearer person representation
  const scale = agent.kind === "student" ? 1 : 1.25;
  const headR = 4 * scale;
  const torsoH = 8 * scale;
  const torsoW = 6 * scale;

  // Staff outer ring for emphasis
  if (agent.kind !== "student") {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, headR + torsoH / 1.5, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Hesitation pulse ring
  if (agent.phase === "hesitating") {
    const pulse = 1 + 0.12 * Math.sin(Date.now() / 100);
    ctx.strokeStyle = COLORS.orange;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.arc(cx, cy, headR + torsoH / 1.2 * pulse, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Body (torso)
  ctx.fillStyle = color;
  ctx.beginPath();
  try {
    ctx.roundRect(cx - torsoW / 2, cy - torsoH / 2 + headR / 2, torsoW, torsoH, Math.min(3, torsoW/2, torsoH/2));
  } catch(e) {
    ctx.rect(cx - torsoW / 2, cy - torsoH / 2 + headR / 2, torsoW, torsoH);
  }
  ctx.fill();

  // Head
  ctx.fillStyle = "#fff";
  ctx.beginPath();
  ctx.arc(cx, cy - torsoH / 2 - headR / 2 + 2, headR, 0, Math.PI * 2);
  ctx.fill();

  // Simple facial mark (eye) for contrast
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.beginPath();
  ctx.arc(cx - headR / 3, cy - torsoH / 2 - headR / 2 + 2, headR / 6, 0, Math.PI * 2);
  ctx.fill();

  // Legs
  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(cx - 6 * scale, cy + torsoH / 2);
  ctx.lineTo(cx - 2 * scale, cy + torsoH / 1.8);
  ctx.moveTo(cx + 6 * scale, cy + torsoH / 2);
  ctx.lineTo(cx + 2 * scale, cy + torsoH / 1.8);
  ctx.stroke();

  // Arms
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(cx - torsoW / 2 - 1, cy - 2);
  ctx.lineTo(cx - torsoW / 2 - 6 * scale, cy + 2);
  ctx.moveTo(cx + torsoW / 2 + 1, cy - 2);
  ctx.lineTo(cx + torsoW / 2 + 6 * scale, cy + 2);
  ctx.stroke();

  // Professor retrieving extinguisher — green pulse ring
  if (agent.kind === "instructor" && agent.phase === "retrieving_extinguisher") {
    const pulse = 1 + 0.15 * Math.sin(Date.now() / 140);
    ctx.strokeStyle = "rgba(16, 185, 129, 0.85)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, (headR + torsoH) * pulse, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Staff role emblem letter inside torso for clarity
  if (agent.kind !== "student") {
    ctx.fillStyle = "#fff";
    ctx.font = "700 9px var(--font-sans)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const char = agent.kind === "instructor" ? "P" : agent.kind === "assistant" ? "A" : "C";
    ctx.fillText(char, cx, cy + 1);
  } else {
    // Student micro heading dot to show heading
    if (agent.target && (agent.target[0] !== agent.x || agent.target[1] !== agent.y)) {
      const dx = agent.target[0] - agent.x;
      const dy = agent.target[1] - agent.y;
      const angle = Math.atan2(dy, dx);
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(cx + Math.cos(angle) * (headR + 4), cy + Math.sin(angle) * (headR + 4), 1.6, 0, Math.PI * 2);
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
  $("mWait").textContent = `${Number(state.avgWait || 0).toFixed(1)}s`;
  $("mQueue").textContent = Number(state.avgQueueLength || 0).toFixed(1);
  $("mThroughput").textContent = `${Number(state.throughputPerMinute || 0).toFixed(1)}/m`;
  $("mUtil").textContent = `${Number(state.exitUtilizationPercent || 0).toFixed(1)}%`;
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
    ["Professor", COLORS.orange],
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

function formatMetricValue(value, suffix = "", precision = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number.toFixed(precision)}${suffix}`;
}

function comparisonRow(label, current, modified, options = {}) {
  const { suffix = "", precision = 0, higherIsBetter = false } = options;
  const currentValue = Number(current);
  const modifiedValue = Number(modified);
  const improvement = Number.isFinite(currentValue) && currentValue > 0
    ? (higherIsBetter ? (modifiedValue - currentValue) : (currentValue - modifiedValue)) / currentValue * 100
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
  
  return `<tr><td>${label}</td><td>${formatMetricValue(current, suffix, precision)}</td><td>${formatMetricValue(modified, suffix, precision)}</td><td>${badge}</td></tr>`;
}

function comparisonAnalysis(data) {
  const timeSaved = data.current.processing_time - data.modified.processing_time;
  const waitSaved = data.current.average_wait_time - data.modified.average_wait_time;
  const throughputGain = data.modified.throughput_per_minute - data.current.throughput_per_minute;
  const timeText = timeSaved >= 0
    ? `${timeSaved.toFixed(0)}s faster`
    : `${Math.abs(timeSaved).toFixed(0)}s slower`;
  const waitText = waitSaved >= 0
    ? `${waitSaved.toFixed(1)}s less average waiting`
    : `${Math.abs(waitSaved).toFixed(1)}s more average waiting`;
  const throughputText = throughputGain >= 0
    ? `${throughputGain.toFixed(1)} more agents/min`
    : `${Math.abs(throughputGain).toFixed(1)} fewer agents/min`;

  return `<div class="analysis-note">
    Modified layout is ${timeText}, with ${waitText} and ${throughputText}. Use these deltas to support the conclusion and recommendations section.
  </div>`;
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
  post("/api/control", { action: running ? "start" : "pause", config: config() });
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
      ${comparisonRow("Total processing time", data.current.processing_time, data.modified.processing_time, { suffix: "s" })}
      ${comparisonRow("Average waiting time", data.current.average_wait_time, data.modified.average_wait_time, { suffix: "s", precision: 1 })}
      ${comparisonRow("Average queue length", data.current.average_queue_length, data.modified.average_queue_length, { precision: 1 })}
      ${comparisonRow("Throughput", data.current.throughput_per_minute, data.modified.throughput_per_minute, { suffix: "/min", precision: 1, higherIsBetter: true })}
      ${comparisonRow("Exit resource utilization", data.current.exit_utilization_percent, data.modified.exit_utilization_percent, { suffix: "%", precision: 1, higherIsBetter: true })}
      ${comparisonRow("Trips", data.current.trips, data.modified.trips)}
      ${comparisonRow("Door collisions", data.current.door_collisions, data.modified.door_collisions)}
      ${comparisonRow("Max heat", data.current.max_heat, data.modified.max_heat)}
    </tbody>
  </table>${comparisonAnalysis(data)}`;
};

applyUrlConfig();
state = makeFallbackState(els.mode.value);
syncFromState();
triggerDraw();
post("/api/reset", config());
setInterval(poll, 180);
