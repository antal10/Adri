import { PanelShell } from "./panel-shell";
import type { SimState, SuspensionType } from "@/hooks/use-simulation";

interface Props {
  state: SimState;
  suspensionType: SuspensionType;
  onTypeChange: (t: SuspensionType) => void;
}

const GEOM: Record<SuspensionType, { label: string; rows: { param: string; value: string; unit: string }[] }> = {
  macpherson: {
    label: "MacPherson Strut",
    rows: [
      { param: "Sprung Mass", value: "280.0", unit: "kg" },
      { param: "Unsprung Mass", value: "35.0", unit: "kg" },
      { param: "Spring k", value: "25,000", unit: "N/m" },
      { param: "Damper c", value: "2,000", unit: "N·s/m" },
      { param: "Tire k", value: "180,000", unit: "N/m" },
      { param: "Motion Ratio", value: "0.95", unit: "" },
      { param: "Strut Length", value: "340", unit: "mm" },
      { param: "Lower Arm", value: "320", unit: "mm" },
      { param: "Wheel Diam", value: "330", unit: "mm" },
    ],
  },
  "double-wishbone": {
    label: "Double Wishbone",
    rows: [
      { param: "Sprung Mass", value: "300.0", unit: "kg" },
      { param: "Unsprung Mass", value: "40.0", unit: "kg" },
      { param: "Spring k", value: "22,000", unit: "N/m" },
      { param: "Damper c", value: "1,800", unit: "N·s/m" },
      { param: "Tire k", value: "180,000", unit: "N/m" },
      { param: "Motion Ratio", value: "0.72", unit: "" },
      { param: "Upper Arm", value: "285", unit: "mm" },
      { param: "Lower Arm", value: "320", unit: "mm" },
      { param: "Wheel Diam", value: "330", unit: "mm" },
    ],
  },
};

export function SolidworksPanel({ state, suspensionType, onTypeChange }: Props) {
  const geom = GEOM[suspensionType];

  const liveRows = [
    { param: "Chassis Δz", value: (state.zs * 1000).toFixed(2), unit: "mm" },
    { param: "Wheel Δz", value: (state.zu * 1000).toFixed(2), unit: "mm" },
    { param: "Camber Δ", value: (state.springDeflection * (suspensionType === "macpherson" ? 0.04 : 0.015)).toFixed(3), unit: "°" },
    { param: "Scrub Radius Δ", value: (state.zu * 1000 * 0.05).toFixed(2), unit: "mm" },
  ];

  return (
    <PanelShell title="Geometry & BOM" tool="SOLIDWORKS" color="#e2231a">
      <div className="space-y-1.5">
        {/* Suspension type toggle */}
        <div className="flex rounded border border-border overflow-hidden" data-testid="suspension-toggle">
          {(["macpherson", "double-wishbone"] as SuspensionType[]).map(t => (
            <button
              key={t}
              onClick={() => onTypeChange(t)}
              className={`flex-1 text-[10px] font-mono py-1 px-1 transition-colors ${
                suspensionType === t
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-muted-foreground hover:bg-accent"
              }`}
              data-testid={`toggle-${t}`}
            >
              {t === "macpherson" ? "MacPherson" : "Dbl Wishbone"}
            </button>
          ))}
        </div>

        {/* Assembly parameters */}
        <div>
          <h4 className="text-[10px] font-mono text-muted-foreground mb-0.5 uppercase tracking-wider">{geom.label}</h4>
          <div className="rounded border border-border overflow-hidden">
            <table className="w-full text-[11px] font-mono">
              <tbody>
                {geom.rows.map((r, i) => (
                  <tr key={r.param} className={i % 2 === 0 ? "bg-card" : "bg-background"}>
                    <td className="px-1.5 py-px text-muted-foreground">{r.param}</td>
                    <td className="px-1.5 py-px text-right text-foreground tabular-nums">{r.value}</td>
                    <td className="px-1 py-px text-muted-foreground w-10 text-[10px]">{r.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live kinematics */}
        <div>
          <h4 className="text-[10px] font-mono text-muted-foreground mb-0.5 uppercase tracking-wider">
            Live Kinematics
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 ml-1.5 animate-pulse-dot" />
          </h4>
          <div className="rounded border border-border overflow-hidden">
            <table className="w-full text-[11px] font-mono">
              <tbody>
                {liveRows.map((r, i) => (
                  <tr key={r.param} className={i % 2 === 0 ? "bg-card" : "bg-background"}>
                    <td className="px-1.5 py-px text-muted-foreground">{r.param}</td>
                    <td className="px-1.5 py-px text-right text-foreground tabular-nums">{r.value}</td>
                    <td className="px-1 py-px text-muted-foreground w-10 text-[10px]">{r.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PanelShell>
  );
}
