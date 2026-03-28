import { Play, Pause, RotateCcw, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface ControlBarProps {
  sim: {
    isRunning: boolean;
    bumpSpeed: number;
    setBumpSpeed: (v: number) => void;
    bumpHeight: number;
    setBumpHeight: (v: number) => void;
    bumpCount: number;
    start: () => void;
    pause: () => void;
    reset: () => void;
    triggerBump: () => void;
    currentState: { time: number };
  };
}

export function ControlBar({ sim }: ControlBarProps) {
  return (
    <div className="flex items-center gap-3 px-3 py-1.5 border-b border-border shrink-0 bg-card/50">
      {/* Play / Pause / Reset */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={sim.isRunning ? sim.pause : sim.start}
          className="h-7 w-7 p-0"
          data-testid="btn-play-pause"
        >
          {sim.isRunning ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={sim.reset}
          className="h-7 w-7 p-0"
          data-testid="btn-reset"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="default"
          size="sm"
          onClick={() => { if (!sim.isRunning) sim.start(); sim.triggerBump(); }}
          className="h-7 px-2.5 text-xs font-mono gap-1"
          data-testid="btn-bump"
        >
          <Zap className="h-3 w-3" />
          HIT BUMP
        </Button>
      </div>

      {/* Time + bump counter */}
      <div className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
        t={sim.currentState.time.toFixed(2)}s
        {sim.bumpCount > 0 && (
          <span className="ml-2 text-primary">#{sim.bumpCount}</span>
        )}
      </div>

      {/* Speed */}
      <div className="flex items-center gap-1.5 ml-auto">
        <label className="text-[11px] text-muted-foreground font-mono whitespace-nowrap">
          {sim.bumpSpeed} km/h
        </label>
        <Slider
          value={[sim.bumpSpeed]}
          onValueChange={([v]) => sim.setBumpSpeed(v)}
          min={10} max={100} step={5}
          className="w-20"
          data-testid="slider-speed"
        />
      </div>

      {/* Height */}
      <div className="flex items-center gap-1.5">
        <label className="text-[11px] text-muted-foreground font-mono whitespace-nowrap">
          {sim.bumpHeight} mm
        </label>
        <Slider
          value={[sim.bumpHeight]}
          onValueChange={([v]) => sim.setBumpHeight(v)}
          min={10} max={100} step={5}
          className="w-20"
          data-testid="slider-height"
        />
      </div>
    </div>
  );
}
