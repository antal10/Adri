import { useEffect } from "react";
import { useSimulation } from "@/hooks/use-simulation";
import { SuspensionSVG } from "@/components/suspension-svg";
import { SolidworksPanel } from "@/components/solidworks-panel";
import { MatlabPanel } from "@/components/matlab-panel";
import { LabviewPanel } from "@/components/labview-panel";
import { PythonPanel } from "@/components/python-panel";
import { ControlBar } from "@/components/control-bar";
import { AdapterBadge } from "@/components/adapter-badge";

export default function Nucleus() {
  const sim = useSimulation();

  // Force dark mode
  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  return (
    <div className="h-screen w-screen overflow-hidden bg-background flex flex-col" data-testid="nucleus-root">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-label="Adri logo">
            <circle cx="16" cy="16" r="14" stroke="hsl(210 100% 55%)" strokeWidth="2" />
            <circle cx="16" cy="16" r="4" fill="hsl(210 100% 55%)" />
            <line x1="16" y1="2" x2="16" y2="12" stroke="hsl(210 100% 55%)" strokeWidth="1.5" />
            <line x1="16" y1="20" x2="16" y2="30" stroke="hsl(210 100% 55%)" strokeWidth="1.5" />
            <line x1="2" y1="16" x2="12" y2="16" stroke="hsl(210 100% 55%)" strokeWidth="1.5" />
            <line x1="20" y1="16" x2="30" y2="16" stroke="hsl(210 100% 55%)" strokeWidth="1.5" />
          </svg>
          <span className="font-semibold text-foreground tracking-tight text-base">ADRI</span>
          <span className="text-muted-foreground text-xs font-mono ml-1 hidden sm:inline">NUCLEUS</span>
        </div>
        <div className="flex items-center gap-4">
          <AdapterBadge tool="SOLIDWORKS" color="#e2231a" connected />
          <AdapterBadge tool="MATLAB" color="#f57c00" connected />
          <AdapterBadge tool="LabVIEW" color="#fed700" connected />
          <AdapterBadge tool="Python" color="#3776ab" connected />
        </div>
      </header>

      {/* Main content area */}
      <div className="flex-1 min-h-0 flex flex-col">
        {/* Control bar */}
        <ControlBar sim={sim} />

        {/* Dashboard grid */}
        <div className="flex-1 min-h-0 grid grid-cols-[1fr_minmax(260px,360px)_1fr] grid-rows-[1fr_1fr] gap-1.5 p-1.5">
          {/* Top-left: SOLIDWORKS geometry */}
          <div className="min-h-0 min-w-0">
            <SolidworksPanel
              state={sim.currentState}
              suspensionType={sim.suspensionType}
              onTypeChange={sim.setSuspensionType}
            />
          </div>

          {/* Center: SVG visualization — spans 2 rows */}
          <div className="row-span-2 min-h-0 min-w-0 flex flex-col">
            <SuspensionSVG
              state={sim.currentState}
              suspensionType={sim.suspensionType}
              bumpCount={sim.bumpCount}
            />
          </div>

          {/* Top-right: MATLAB dynamics */}
          <div className="min-h-0 min-w-0">
            <MatlabPanel
              history={sim.history}
              state={sim.currentState}
              suspensionType={sim.suspensionType}
            />
          </div>

          {/* Bottom-left: LabVIEW sensors */}
          <div className="min-h-0 min-w-0">
            <LabviewPanel sensors={sim.sensors} isRunning={sim.isRunning} />
          </div>

          {/* Bottom-right: Python pipeline */}
          <div className="min-h-0 min-w-0">
            <PythonPanel pipeline={sim.pipeline} />
          </div>
        </div>
      </div>
    </div>
  );
}
