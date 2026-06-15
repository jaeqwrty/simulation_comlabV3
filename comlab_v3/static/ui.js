import { Store } from './store.js';
import { COLORS } from './constants.js';

export const $ = (id) => document.getElementById(id);
export const els = {
  map: $("mapCanvas"), chart: $("chart"), start: $("startBtn"), step: $("stepBtn"), reset: $("resetBtn"),
  mode: $("modeSelect"), panic: $("panicBtn"), heat: $("heatBtn"), fire: $("fireSelect"),
  speed: $("speedRange"), speedText: $("speedText"), compare: $("compareBtn"),
  statusDot: $("statusDot"), statusText: $("statusText"), layoutTitle: $("layoutTitle"),
  layoutNote: $("layoutNote"), legend: $("legend"), events: $("events"), comparison: $("comparison")
};