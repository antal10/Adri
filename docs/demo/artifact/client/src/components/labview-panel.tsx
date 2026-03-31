import { PanelShell } from "./panel-shell";
import type { SensorReading } from "@/hooks/use-simulation";
import { Activity } from "lucide-react";

interface Props {
  sensors: SensorReading[];
  isRunning: boolean;
}

const statusColor = {
  nominal: "text-green-400",
  warning: "text-amber-400",
  critical: "text-red-400",
};

const statusBg = {
  nominal: "bg-green-500/10",
  warning: "bg-amber-500/10",
  critical: "bg-red-500/10",
};

const statusDot = {
  nominal: "bg-green-500",
  warning: "bg-amber-500",
  critical: "bg-red-500",
};

export function LabviewPanel({ sensors, isRunning }: Props) {
  return (
    <PanelShell title="Real-Time Sensor Stream" tool="LabVIEW" color="#fed700">
      <div className="space-y-2">
        {/* DAQ Status bar */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <Activity className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground">NI DAQ</span>
          <span className={`ml-auto ${isRunning ? "text-green-400" : "text-muted-foreground"}`}>
            {isRunning ? "STREAMING" : "IDLE"}
          </span>
          {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse-dot" />}
        </div>

        {/* Sensor grid */}
        {sensors.length > 0 ? (
          <div className="grid grid-cols-2 gap-1.5">
            {sensors.map((s) => (
              <div
                key={s.id}
                className={`rounded border border-border px-2.5 py-2 ${statusBg[s.status]}`}
                data-testid={`sensor-${s.id}`}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${statusDot[s.status]} ${s.status !== "nominal" ? "animate-pulse-dot" : ""}`} />
                  <span className="text-[10px] font-mono text-muted-foreground uppercase">{s.label}</span>
                </div>
                <div className={`text-base font-mono font-semibold tabular-nums ${statusColor[s.status]}`}>
                  {s.value >= 0 ? " " : ""}{s.value.toFixed(s.unit === "g" || s.unit === "°" ? 3 : 1)}
                </div>
                <div className="text-[10px] font-mono text-muted-foreground">{s.unit}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Activity className="h-8 w-8 mb-2 opacity-30" />
            <span className="text-xs font-mono">Start simulation to stream</span>
          </div>
        )}

        {/* Sample rate info */}
        {isRunning && (
          <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground border-t border-border pt-1.5 mt-1">
            <span>fs = 250 Hz</span>
            <span>6 ch active</span>
            <span>cDAQ-9174</span>
          </div>
        )}
      </div>
    </PanelShell>
  );
}
