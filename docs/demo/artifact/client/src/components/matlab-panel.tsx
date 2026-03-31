import { PanelShell } from "./panel-shell";
import type { SimHistory, SimState, SuspensionType } from "@/hooks/use-simulation";
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, BarChart, Bar, CartesianGrid,
} from "recharts";

interface Props {
  history: SimHistory;
  state: SimState;
  suspensionType: SuspensionType;
}

const SUSP_PARAMS = {
  macpherson: { mSprung: 280, mUnsprung: 35, kSpring: 25000, cDamper: 2000, kTire: 180000, motionRatio: 0.95 },
  "double-wishbone": { mSprung: 300, mUnsprung: 40, kSpring: 22000, cDamper: 1800, kTire: 180000, motionRatio: 0.72 },
};

export function MatlabPanel({ history, state, suspensionType }: Props) {
  const p = SUSP_PARAMS[suspensionType];
  const kEff = p.kSpring * p.motionRatio * p.motionRatio;
  const cEff = p.cDamper * p.motionRatio * p.motionRatio;

  // Natural frequencies (analytical)
  const fn1 = (1 / (2 * Math.PI)) * Math.sqrt(kEff / p.mSprung);
  const fn2 = (1 / (2 * Math.PI)) * Math.sqrt(p.kTire / p.mUnsprung);
  const zeta = cEff / (2 * Math.sqrt(kEff * p.mSprung));

  // Prepare time-domain data (subsample for performance)
  const step = Math.max(1, Math.floor(history.times.length / 100));
  const timeData = [];
  for (let i = 0; i < history.times.length; i += step) {
    timeData.push({
      t: history.times[i],
      zs: history.zs[i] * 1000,
      zu: history.zu[i] * 1000,
      zr: history.zr[i] * 1000,
    });
  }

  // Prepare FFT data (limit to 50Hz range)
  const fftData = [];
  for (let i = 0; i < history.fftFreqs.length; i++) {
    if (history.fftFreqs[i] > 50) break;
    fftData.push({
      freq: history.fftFreqs[i],
      mag: history.fftMag[i] * 1000,
    });
  }

  // Peak detection from acceleration history
  const peakAccel = history.accelG.length > 0
    ? Math.max(...history.accelG.map(Math.abs))
    : 0;
  const settleIdx = history.accelG.length > 10
    ? history.accelG.findIndex((v, i) => i > history.accelG.length * 0.3 && Math.abs(v) < 0.05)
    : -1;
  const settleTime = settleIdx > 0 && history.times.length > settleIdx
    ? history.times[settleIdx] - history.times[0]
    : null;

  return (
    <PanelShell title="Dynamics & Freq Analysis" tool="MATLAB" color="#f57c00">
      <div className="space-y-1.5">
        {/* KPIs — suspension-type aware */}
        <div className="grid grid-cols-3 gap-1.5">
          <div className="rounded border border-border bg-background px-2 py-1">
            <div className="text-[9px] font-mono text-muted-foreground">f₁ body</div>
            <div className="text-xs font-mono font-semibold text-foreground tabular-nums">{fn1.toFixed(1)} Hz</div>
          </div>
          <div className="rounded border border-border bg-background px-2 py-1">
            <div className="text-[9px] font-mono text-muted-foreground">f₂ wheel</div>
            <div className="text-xs font-mono font-semibold text-foreground tabular-nums">{fn2.toFixed(1)} Hz</div>
          </div>
          <div className="rounded border border-border bg-background px-2 py-1">
            <div className="text-[9px] font-mono text-muted-foreground">ζ damping</div>
            <div className="text-xs font-mono font-semibold text-foreground tabular-nums">{zeta.toFixed(3)}</div>
          </div>
        </div>

        {/* Effective stiffness + motion ratio row */}
        <div className="grid grid-cols-3 gap-1.5">
          <div className="rounded border border-border bg-background px-2 py-1">
            <div className="text-[9px] font-mono text-muted-foreground">k_eff</div>
            <div className="text-xs font-mono font-semibold text-foreground tabular-nums">{(kEff / 1000).toFixed(1)}k</div>
          </div>
          <div className="rounded border border-border bg-background px-2 py-1">
            <div className="text-[9px] font-mono text-muted-foreground">c_eff</div>
            <div className="text-xs font-mono font-semibold text-foreground tabular-nums">{cEff.toFixed(0)}</div>
          </div>
          <div className="rounded border border-border bg-background px-2 py-1">
            <div className="text-[9px] font-mono text-muted-foreground">λ ratio</div>
            <div className="text-xs font-mono font-semibold text-foreground tabular-nums">{p.motionRatio.toFixed(2)}</div>
          </div>
        </div>

        {/* Time-domain response */}
        <div>
          <h4 className="text-[9px] font-mono text-muted-foreground mb-0.5 uppercase tracking-wider">Displacement Response</h4>
          <div className="h-24 w-full">
            {timeData.length > 2 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeData} margin={{ top: 2, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 12% 18%)" />
                  <XAxis
                    dataKey="t"
                    tick={{ fontSize: 8, fontFamily: "var(--font-mono)", fill: "hsl(220 10% 50%)" }}
                    tickFormatter={(v: number) => v.toFixed(2)}
                    axisLine={{ stroke: "hsl(220 12% 20%)" }}
                    tickLine={false}
                    tickCount={5}
                    type="number"
                    domain={['dataMin', 'dataMax']}
                  />
                  <YAxis
                    tick={{ fontSize: 8, fontFamily: "var(--font-mono)", fill: "hsl(220 10% 50%)" }}
                    tickFormatter={(v: number) => v.toFixed(0)}
                    axisLine={{ stroke: "hsl(220 12% 20%)" }}
                    tickLine={false}
                    width={30}
                  />
                  <Line type="monotone" dataKey="zs" stroke="hsl(210 100% 60%)" strokeWidth={1.5} dot={false} name="Chassis" />
                  <Line type="monotone" dataKey="zu" stroke="hsl(142 72% 55%)" strokeWidth={1.5} dot={false} name="Wheel" />
                  <Line type="monotone" dataKey="zr" stroke="hsl(38 92% 55%)" strokeWidth={1} dot={false} name="Road" strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-muted-foreground">
                Waiting for data...
              </div>
            )}
          </div>
        </div>

        {/* FFT — Butterworth-filtered spectrum */}
        <div>
          <h4 className="text-[9px] font-mono text-muted-foreground mb-0.5 uppercase tracking-wider">Butterworth LP → FFT Spectrum</h4>
          <div className="h-20 w-full">
            {fftData.length > 2 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={fftData} margin={{ top: 2, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 12% 18%)" />
                  <XAxis
                    dataKey="freq"
                    tick={{ fontSize: 8, fontFamily: "var(--font-mono)", fill: "hsl(220 10% 50%)" }}
                    tickFormatter={(v: number) => v.toFixed(0)}
                    axisLine={{ stroke: "hsl(220 12% 20%)" }}
                    tickLine={false}
                    tickCount={6}
                    type="number"
                    domain={[0, 'dataMax']}
                    label={{ value: "Hz", position: "insideBottomRight", offset: -2, fontSize: 7, fill: "hsl(220 10% 45%)" }}
                  />
                  <YAxis
                    tick={{ fontSize: 8, fontFamily: "var(--font-mono)", fill: "hsl(220 10% 50%)" }}
                    axisLine={{ stroke: "hsl(220 12% 20%)" }}
                    tickLine={false}
                    width={26}
                  />
                  <Bar dataKey="mag" fill="hsl(280 65% 60%)" radius={[1, 1, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-muted-foreground">
                Waiting for data...
              </div>
            )}
          </div>
        </div>

        {/* Peak detection readouts — moved from Python */}
        <div className="rounded border border-border bg-background p-1.5 space-y-0.5">
          <h4 className="text-[9px] font-mono text-muted-foreground uppercase tracking-wider">Peak Detection</h4>
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-muted-foreground">Peak |accel|</span>
            <span className={`tabular-nums font-semibold ${peakAccel > 2 ? "text-red-400" : peakAccel > 0.8 ? "text-amber-400" : "text-foreground"}`}>
              {peakAccel.toFixed(3)} g
            </span>
          </div>
          {settleTime !== null && (
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-muted-foreground">Settle time</span>
              <span className="text-foreground tabular-nums font-semibold">{(settleTime * 1000).toFixed(0)} ms</span>
            </div>
          )}
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-muted-foreground">Samples</span>
            <span className="text-foreground tabular-nums">{history.times.length}</span>
          </div>
        </div>
      </div>
    </PanelShell>
  );
}
