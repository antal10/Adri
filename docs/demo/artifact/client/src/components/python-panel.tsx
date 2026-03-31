import { PanelShell } from "./panel-shell";
import type { PipelineStage } from "@/hooks/use-simulation";
import { CheckCircle, Loader2, Circle } from "lucide-react";

interface Props {
  pipeline: PipelineStage[];
}

const statusIcon = {
  idle: <Circle className="h-3 w-3 text-muted-foreground" />,
  running: <Loader2 className="h-3 w-3 text-blue-400 animate-spin" />,
  done: <CheckCircle className="h-3 w-3 text-green-400" />,
};

export function PythonPanel({ pipeline }: Props) {
  const allDone = pipeline.every((s) => s.status === "done");

  return (
    <PanelShell title="Data Pipeline" tool="Python" color="#3776ab">
      <div className="space-y-2.5">
        {/* Pipeline stages */}
        <div>
          <h4 className="text-[9px] font-mono text-muted-foreground mb-1 uppercase tracking-wider">
            Pipeline Stages — Data Janitor
          </h4>
          <div className="space-y-0.5">
            {pipeline.map((stage, i) => (
              <div
                key={stage.name}
                className="flex items-center gap-2 rounded px-2 py-1.5 border border-border bg-background"
                data-testid={`pipeline-${i}`}
              >
                {statusIcon[stage.status]}
                <span className={`text-xs font-mono flex-1 ${stage.status === "done" ? "text-foreground" : "text-muted-foreground"}`}>
                  {stage.name}
                </span>
                {stage.status === "done" && (
                  <>
                    <span className="text-[10px] font-mono text-muted-foreground tabular-nums">{stage.latency}ms</span>
                    <span className="text-[10px] font-mono text-muted-foreground tabular-nums">{stage.rows} rows</span>
                  </>
                )}
                {stage.status === "running" && (
                  <span className="text-[10px] font-mono text-blue-400">processing...</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Export confirmation */}
        {allDone && (
          <div className="rounded border border-border bg-background p-2 space-y-1">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-muted-foreground">Output</span>
              <span className="text-green-400 text-[10px]">bump_data.mat</span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-muted-foreground">Status</span>
              <span className="text-green-400 text-[10px]">Ready for MATLAB</span>
            </div>
          </div>
        )}

        {/* Code snippet — data janitor only, no signal processing */}
        <div>
          <h4 className="text-[9px] font-mono text-muted-foreground mb-0.5 uppercase tracking-wider">Active Script</h4>
          <pre className="rounded border border-border bg-background p-2 text-[10px] font-mono text-muted-foreground leading-relaxed overflow-x-auto">
{`import pandas as pd
from nptdms import TdmsFile

# 1. Ingest TDMS from LabVIEW
raw = TdmsFile.read("daq_stream.tdms")
df = raw["sensors"].as_dataframe()

# 2. Resample to uniform 1 kHz
df.index = pd.to_timedelta(df["time"], unit="s")
df = df.resample("1ms").interpolate()

# 3. Format columns for MATLAB
df = df.rename(columns={
  "accel_z": "az_g",
  "spring_defl": "x_spring_mm",
})

# 4. Export clean .mat
from scipy.io import savemat
savemat("bump_data.mat", {
  "t": df.index.total_seconds(),
  "data": df.values
})`}
          </pre>
        </div>

        {/* Signal chain note */}
        <div className="rounded bg-background/50 border border-border px-2 py-1.5">
          <div className="text-[9px] font-mono text-muted-foreground leading-snug">
            <span className="text-blue-400">LabVIEW</span> → TDMS →{" "}
            <span className="text-blue-400">Python</span> → Ingest → Resample → Format → Export →{" "}
            <span className="text-amber-400">MATLAB</span> (FFT, Butterworth, peak detect)
          </div>
        </div>
      </div>
    </PanelShell>
  );
}
