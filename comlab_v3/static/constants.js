export const COLORS = {
  text: "#f8fafc",
  muted: "#94a3b8",
  line: "rgba(51, 65, 85, 0.18)",
  cell: "rgba(30, 41, 59, 0.45)",
  hall: "rgba(15, 23, 42, 0.65)",
  green: "#10b981",
  yellow: "#fbbf24",
  blue: "#3b82f6",
  purple: "#8b5cf6",
  orange: "#f97316",
  assistant: "#14b8a6",
  custodian: "#d946ef",
  red: "#f43f5e"
};

export const CELL = 34;
export const MAP_W = 442;
export const MAP_H = 408;
export const LAB_LEFT = 0;
export const LAB_RIGHT = 360;
export const HALL_RIGHT = MAP_W;
export const SERVICE_X = 302;
export const SERVICE_W = 52;
export const WORKSTATION_X = new Map([
  [0, 42], [1, 82], [2, 122], [4, 190], [5, 230], [6, 270]
]);
export const AISLE_X = 156;
export const EXIT_X = LAB_RIGHT;
export const BASE_ROW_Y = new Map(Array.from({ length: 12 }, (_, y) => [y, y * CELL + CELL / 2]));
export const WORKSTATION_ROW_Y = new Map([
  [1, 72], [2, 116], [4, 160], [5, 204], [7, 248], [8, 292]
]);
