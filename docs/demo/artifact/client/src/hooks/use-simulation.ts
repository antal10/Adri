import { useState, useRef, useCallback, useEffect } from "react";

// ── Suspension type definitions ──
export type SuspensionType = "macpherson" | "double-wishbone";

interface SuspensionParams {
  mSprung: number;    // kg
  mUnsprung: number;  // kg
  kSpring: number;    // N/m
  kTire: number;      // N/m
  cDamper: number;    // N·s/m
  motionRatio: number; // spring/damper motion ratio
}

const PARAMS: Record<SuspensionType, SuspensionParams> = {
  "macpherson": {
    mSprung: 280, mUnsprung: 35, kSpring: 25000, kTire: 180000, cDamper: 2000,
    motionRatio: 0.95, // coaxial, nearly 1:1
  },
  "double-wishbone": {
    mSprung: 300, mUnsprung: 40, kSpring: 22000, kTire: 180000, cDamper: 1800,
    motionRatio: 0.72, // pushrod / rocker geometry
  },
};

const DT = 0.001;         // integration timestep (1ms)
const STEPS_PER_FRAME = 4; // 4ms sim time per animation frame
const HISTORY_LEN = 600;   // samples to keep

export interface SimState {
  time: number;
  zs: number; zu: number; zr: number;
  dzs: number; dzu: number;
  fSpring: number; fDamper: number; fTire: number;
  accelG: number;
  damperVelocity: number;
  springDeflection: number; // mm
  tireDeflection: number;   // mm
}

export interface SimHistory {
  times: number[];
  zs: number[];
  zu: number[];
  zr: number[];
  accelG: number[];
  fSpring: number[];
  fDamper: number[];
  fTire: number[];
  fftFreqs: number[];
  fftMag: number[];
}

export interface SensorReading {
  id: string;
  label: string;
  value: number;
  unit: string;
  status: "nominal" | "warning" | "critical";
}

export interface PipelineStage {
  name: string;
  status: "idle" | "running" | "done";
  latency: number;
  rows: number;
}

// ── Road bump — half-sine profile ──
function roadBump(t: number, bumpStart: number, bumpHeight: number, bumpLength: number, speed: number): number {
  const dur = bumpLength / speed;
  const tRel = t - bumpStart;
  if (tRel < 0 || tRel > dur) return 0;
  return bumpHeight * Math.sin(Math.PI * tRel / dur);
}

// ── Multi-bump road: sum all active bump events ──
function roadProfile(t: number, bumps: { start: number; height: number }[], bumpLength: number, speed: number): number {
  let z = 0;
  for (const b of bumps) {
    z += roadBump(t, b.start, b.height, bumpLength, speed);
  }
  return z;
}

// ── Simple DFT for small arrays ──
function computeFFT(signal: number[], dt: number): { freqs: number[]; mag: number[] } {
  const N = signal.length;
  if (N < 16) return { freqs: [], mag: [] };
  const maxBins = Math.min(N / 2, 128);
  const freqs: number[] = [];
  const mag: number[] = [];
  const fs = 1 / dt;
  for (let k = 1; k < maxBins; k++) {
    let re = 0, im = 0;
    for (let n = 0; n < N; n++) {
      const angle = (2 * Math.PI * k * n) / N;
      re += signal[n] * Math.cos(angle);
      im -= signal[n] * Math.sin(angle);
    }
    freqs.push((k * fs) / N);
    mag.push(Math.sqrt(re * re + im * im) / N);
  }
  return { freqs, mag };
}

// ── Default pipeline stages (Python is data-janitor only) ──
function defaultPipeline(): PipelineStage[] {
  return [
    { name: "Ingest TDMS", status: "idle", latency: 0, rows: 0 },
    { name: "Resample 1 kHz", status: "idle", latency: 0, rows: 0 },
    { name: "Format Columns", status: "idle", latency: 0, rows: 0 },
    { name: "Export .mat", status: "idle", latency: 0, rows: 0 },
  ];
}

// ── Default empty state ──
const EMPTY_STATE: SimState = {
  time: 0, zs: 0, zu: 0, zr: 0, dzs: 0, dzu: 0,
  fSpring: 0, fDamper: 0, fTire: 0,
  accelG: 0, damperVelocity: 0, springDeflection: 0, tireDeflection: 0,
};

const EMPTY_HISTORY: SimHistory = {
  times: [], zs: [], zu: [], zr: [], accelG: [],
  fSpring: [], fDamper: [], fTire: [],
  fftFreqs: [], fftMag: [],
};

// ═══════════════════════════════════════
export function useSimulation() {
  const [isRunning, setIsRunning] = useState(false);
  const [bumpSpeed, setBumpSpeed] = useState(40);
  const [bumpHeight, setBumpHeight] = useState(50);
  const [suspensionType, setSuspensionType] = useState<SuspensionType>("macpherson");
  const [currentState, setCurrentState] = useState<SimState>(EMPTY_STATE);
  const [history, setHistory] = useState<SimHistory>(EMPTY_HISTORY);
  const [sensors, setSensors] = useState<SensorReading[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStage[]>(defaultPipeline());
  const [bumpCount, setBumpCount] = useState(0);

  // Mutable sim state — never causes re-renders
  const simRef = useRef({
    t: 0, zs: 0, zu: 0, dzs: 0, dzu: 0,
    bumps: [] as { start: number; height: number }[],
    lastBumpTime: -999,
    histTimes: [] as number[],
    histZs: [] as number[],
    histZu: [] as number[],
    histZr: [] as number[],
    histAccel: [] as number[],
    histFSpring: [] as number[],
    histFDamper: [] as number[],
    histFTire: [] as number[],
    frameCount: 0,
    pipelineStart: -1,
  });
  const rafRef = useRef<number>(0);

  // Derived from current slider values
  const speedMs = bumpSpeed / 3.6;
  const bumpH = bumpHeight / 1000;
  const bumpLength = 0.3; // 30 cm

  const step = useCallback(() => {
    const s = simRef.current;
    const p = PARAMS[suspensionType];
    // Effective spring/damper rates accounting for motion ratio
    const kEff = p.kSpring * p.motionRatio * p.motionRatio;
    const cEff = p.cDamper * p.motionRatio * p.motionRatio;

    for (let i = 0; i < STEPS_PER_FRAME; i++) {
      // Road input from all bumps
      const zr = roadProfile(s.t, s.bumps, bumpLength, speedMs);

      const springDefl = s.zs - s.zu;
      const tireDefl = s.zu - zr;
      const relVel = s.dzs - s.dzu;

      const fSpring = -kEff * springDefl;
      const fDamper = -cEff * relVel;
      const fTire = -p.kTire * tireDefl;

      const as = (fSpring + fDamper) / p.mSprung;
      const au = (-fSpring - fDamper + fTire) / p.mUnsprung;

      s.dzs += as * DT;
      s.dzu += au * DT;
      s.zs += s.dzs * DT;
      s.zu += s.dzu * DT;
      s.t += DT;

      // Record first sub-step each frame (~250 Hz effective sample rate)
      if (i === 0) {
        s.histTimes.push(s.t);
        s.histZs.push(s.zs);
        s.histZu.push(s.zu);
        s.histZr.push(zr);
        s.histAccel.push(as / 9.81);
        s.histFSpring.push(-fSpring);
        s.histFDamper.push(-fDamper);
        s.histFTire.push(fTire);

        if (s.histTimes.length > HISTORY_LEN) {
          s.histTimes.shift(); s.histZs.shift(); s.histZu.shift(); s.histZr.shift();
          s.histAccel.shift(); s.histFSpring.shift(); s.histFDamper.shift(); s.histFTire.shift();
        }
      }
    }

    // Prune old bumps (finished > 0.5s ago)
    const bumpDur = bumpLength / speedMs;
    s.bumps = s.bumps.filter(b => s.t - b.start < bumpDur + 0.5);

    s.frameCount++;

    // Current state snapshot
    const zr = roadProfile(s.t, s.bumps, bumpLength, speedMs);
    const springDefl = s.zs - s.zu;
    const tireDefl = s.zu - zr;
    const relVel = s.dzs - s.dzu;
    const fSpring = -kEff * springDefl;
    const fDamper = -cEff * relVel;
    const fTire = -p.kTire * tireDefl;
    const as = (fSpring + fDamper) / p.mSprung;

    const state: SimState = {
      time: s.t,
      zs: s.zs, zu: s.zu, zr,
      dzs: s.dzs, dzu: s.dzu,
      fSpring: -fSpring, fDamper: -fDamper, fTire,
      accelG: as / 9.81,
      damperVelocity: relVel,
      springDeflection: springDefl * 1000,
      tireDeflection: tireDefl * 1000,
    };
    setCurrentState(state);

    // Update charts every 3 frames
    if (s.frameCount % 3 === 0) {
      const fft = computeFFT(s.histAccel.slice(-128), DT * STEPS_PER_FRAME);
      setHistory({
        times: [...s.histTimes],
        zs: [...s.histZs],
        zu: [...s.histZu],
        zr: [...s.histZr],
        accelG: [...s.histAccel],
        fSpring: [...s.histFSpring],
        fDamper: [...s.histFDamper],
        fTire: [...s.histFTire],
        fftFreqs: fft.freqs,
        fftMag: fft.mag,
      });
    }

    // Sensors every 5 frames
    if (s.frameCount % 5 === 0) {
      const accelAbs = Math.abs(state.accelG);
      setSensors([
        { id: "accel", label: "Vertical Accel", value: state.accelG, unit: "g",
          status: accelAbs > 2.0 ? "critical" : accelAbs > 0.8 ? "warning" : "nominal" },
        { id: "spring", label: "Spring Defl", value: state.springDeflection, unit: "mm",
          status: Math.abs(state.springDeflection) > 30 ? "critical" : Math.abs(state.springDeflection) > 15 ? "warning" : "nominal" },
        { id: "tire", label: "Tire Defl", value: state.tireDeflection, unit: "mm",
          status: Math.abs(state.tireDeflection) > 2 ? "critical" : Math.abs(state.tireDeflection) > 1 ? "warning" : "nominal" },
        { id: "damperV", label: "Damper Vel", value: state.damperVelocity * 1000, unit: "mm/s",
          status: Math.abs(state.damperVelocity) > 0.5 ? "critical" : Math.abs(state.damperVelocity) > 0.2 ? "warning" : "nominal" },
        { id: "force", label: "Damper Force", value: state.fDamper, unit: "N",
          status: Math.abs(state.fDamper) > 1500 ? "critical" : Math.abs(state.fDamper) > 800 ? "warning" : "nominal" },
        { id: "road", label: "Road Input", value: state.zr * 1000, unit: "mm",
          status: state.zr * 1000 > 30 ? "critical" : state.zr * 1000 > 10 ? "warning" : "nominal" },
      ]);
    }

    // Python pipeline: Ingest → Resample → Format → Export (data-janitor only)
    if (s.pipelineStart >= 0) {
      const elapsed = (s.t - s.pipelineStart) * 1000;
      const nSamples = Math.floor(s.histTimes.length);
      setPipeline([
        { name: "Ingest TDMS", status: elapsed > 40 ? "done" : elapsed > 0 ? "running" : "idle",
          latency: elapsed > 40 ? 36 : 0, rows: elapsed > 40 ? nSamples : 0 },
        { name: "Resample 1 kHz", status: elapsed > 100 ? "done" : elapsed > 40 ? "running" : "idle",
          latency: elapsed > 100 ? 54 : 0, rows: elapsed > 100 ? nSamples * 4 : 0 },
        { name: "Format Columns", status: elapsed > 160 ? "done" : elapsed > 100 ? "running" : "idle",
          latency: elapsed > 160 ? 22 : 0, rows: elapsed > 160 ? nSamples * 4 : 0 },
        { name: "Export .mat", status: elapsed > 220 ? "done" : elapsed > 160 ? "running" : "idle",
          latency: elapsed > 220 ? 14 : 0, rows: elapsed > 220 ? 1 : 0 },
      ]);
    }

    rafRef.current = requestAnimationFrame(step);
  }, [bumpH, speedMs, bumpLength, suspensionType]);

  const start = useCallback(() => {
    if (isRunning) return;
    setIsRunning(true);
    rafRef.current = requestAnimationFrame(step);
  }, [isRunning, step]);

  const pause = useCallback(() => {
    setIsRunning(false);
    cancelAnimationFrame(rafRef.current);
  }, []);

  const reset = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    setIsRunning(false);
    setBumpCount(0);
    simRef.current = {
      t: 0, zs: 0, zu: 0, dzs: 0, dzu: 0,
      bumps: [], lastBumpTime: -999,
      histTimes: [], histZs: [], histZu: [], histZr: [],
      histAccel: [], histFSpring: [], histFDamper: [], histFTire: [],
      frameCount: 0, pipelineStart: -1,
    };
    setCurrentState(EMPTY_STATE);
    setHistory(EMPTY_HISTORY);
    setSensors([]);
    setPipeline(defaultPipeline());
  }, []);

  // Trigger a bump — can be called repeatedly
  const triggerBump = useCallback(() => {
    const s = simRef.current;
    const minGap = bumpLength / speedMs + 0.08; // minimum gap between bumps
    if (s.t - s.lastBumpTime < minGap) return; // debounce
    const bStart = s.t + 0.03; // 30ms lookahead
    s.bumps.push({ start: bStart, height: bumpH });
    s.lastBumpTime = bStart;
    s.pipelineStart = bStart;
    setBumpCount(c => c + 1);
    // Reset pipeline for new bump event
    setPipeline(defaultPipeline());
  }, [bumpH, bumpLength, speedMs]);

  useEffect(() => {
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  return {
    isRunning, currentState, history, sensors, pipeline,
    bumpSpeed, setBumpSpeed, bumpHeight, setBumpHeight,
    suspensionType, setSuspensionType,
    bumpCount,
    start, pause, reset, triggerBump,
  };
}
