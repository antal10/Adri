import type { SimState, SuspensionType } from "@/hooks/use-simulation";

interface Props {
  state: SimState;
  suspensionType: SuspensionType;
  bumpCount: number;
}

// ── Coil spring path generator ──
function coilPath(cx: number, top: number, bot: number, coils: number, halfWidth: number): string {
  const pts: string[] = [`M ${cx} ${top}`];
  const h = (bot - top) / (coils * 2);
  for (let i = 0; i < coils * 2; i++) {
    const x = i % 2 === 0 ? cx + halfWidth : cx - halfWidth;
    pts.push(`L ${x} ${top + h * (i + 1)}`);
  }
  pts.push(`L ${cx} ${bot}`);
  return pts.join(" ");
}

export function SuspensionSVG({ state, suspensionType, bumpCount }: Props) {
  const scale = 800;
  const zsVis = state.zs * scale;
  const zuVis = state.zu * scale;
  const zrVis = state.zr * scale;

  // Base positions
  const chassisBaseY = 70;
  const wheelBaseY = 215;
  const roadBaseY = 296;

  const chassisY = chassisBaseY - zsVis;
  const wheelY = wheelBaseY - zuVis;
  const roadY = roadBaseY - zrVis;
  const wheelCY = wheelY + 18;

  // Common colors
  const armBlue = "hsl(210 100% 55%)";
  const springGreen = "hsl(142 72% 50%)";
  const damperOrange = "hsl(38 92% 50%)";
  const metalDark = "hsl(220 12% 16%)";
  const metalBorder = "hsl(220 10% 30%)";
  const labelColor = "hsl(220 10% 52%)";
  const labelFont = "var(--font-mono)";

  // Knuckle center X
  const kx = 165;

  return (
    <div className="h-full flex flex-col rounded-md border border-border bg-card overflow-hidden" data-testid="suspension-svg">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-card shrink-0">
        <svg width="12" height="12" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="hsl(210 100% 55%)" /></svg>
        <span className="text-xs font-mono font-medium text-foreground">NUCLEUS</span>
        <span className="text-xs text-muted-foreground ml-auto">
          {suspensionType === "macpherson" ? "MacPherson" : "Dbl Wishbone"}
        </span>
      </div>
      <div className="flex-1 min-h-0 flex items-center justify-center p-1">
        <svg viewBox="40 15 265 310" className="w-full h-full" style={{ maxWidth: 330 }}>

          {/* ── Road ── */}
          <line x1="50" y1={roadBaseY} x2="290" y2={roadBaseY} stroke="hsl(220 10% 28%)" strokeWidth="1.5" strokeDasharray="6 4" />
          {bumpCount > 0 && zrVis > 0.5 && (
            <ellipse cx={kx} cy={roadY + 1} rx="22" ry={Math.max(1, zrVis * 0.25 + 2)} fill="hsl(38 92% 50% / 0.25)" stroke={damperOrange} strokeWidth="0.8" />
          )}
          <text x={kx} y={roadBaseY + 14} textAnchor="middle" fill={labelColor} fontSize="8" fontFamily={labelFont}>ROAD</text>

          {/* ── Tire ── */}
          <circle cx={kx} cy={wheelCY} r="22" fill="none" stroke="hsl(220 10% 42%)" strokeWidth="3" />
          <circle cx={kx} cy={wheelCY} r="9" fill="none" stroke="hsl(220 10% 32%)" strokeWidth="1.5" />
          <line x1={kx - 16} y1={wheelCY + 22} x2={kx + 16} y2={wheelCY + 22} stroke="hsl(220 10% 38%)" strokeWidth="2" />

          {/* ── Knuckle / upright ── */}
          <rect x={kx - 7} y={wheelY - 18} width="14" height="36" rx="2" fill={metalDark} stroke={metalBorder} strokeWidth="1" />

          {suspensionType === "macpherson" ? (
            /* ════ MacPherson Strut ════ */
            <>
              {/* Strut body: coaxial spring + damper on same axis */}
              {(() => {
                const strutX = kx;
                const strutTop = chassisY + 22;
                const strutBot = wheelY - 20;
                const pistonY = strutTop + (strutBot - strutTop) * 0.4;

                return (
                  <>
                    {/* Spring wrapped around strut tube */}
                    <path d={coilPath(strutX, strutTop + 8, strutBot - 8, 6, 16)}
                      fill="none" stroke={springGreen} strokeWidth="2" strokeLinejoin="round" />

                    {/* Damper tube (inner) */}
                    <rect x={strutX - 5} y={pistonY} width="10" height={strutBot - pistonY}
                      rx="2" fill={metalDark} stroke={damperOrange} strokeWidth="1.2" />
                    {/* Damper rod */}
                    <line x1={strutX} y1={strutTop} x2={strutX} y2={pistonY + 2}
                      stroke={damperOrange} strokeWidth="1.5" />

                    {/* Top mount */}
                    <circle cx={strutX} cy={strutTop} r="3" fill={damperOrange} />
                    {/* Bottom mount */}
                    <circle cx={strutX} cy={strutBot} r="2.5" fill={damperOrange} />
                  </>
                );
              })()}

              {/* Lower control arm only */}
              <line x1="88" y1={wheelY + 14} x2={kx} y2={wheelY + 10}
                stroke={armBlue} strokeWidth="2.5" />
              <circle cx="88" cy={wheelY + 14} r="3" fill={armBlue} />
              <circle cx={kx} cy={wheelY + 10} r="2.5" fill="hsl(210 100% 40%)" />

              {/* Labels */}
              <text x="78" y={wheelY + 26} fill={labelColor} fontSize="7" fontFamily={labelFont}>LOWER ARM</text>
              <text x={kx + 14} y={chassisY + 56} fill={labelColor} fontSize="7" fontFamily={labelFont}>STRUT</text>
            </>
          ) : (
            /* ════ Double Wishbone ════ */
            <>
              {/* Spring — between upper arm pivot area and lower arm */}
              {(() => {
                const springX = 128;
                const springTop = chassisY + 28;
                const springBot = wheelY - 4;
                return (
                  <path d={coilPath(springX, springTop, springBot, 5, 13)}
                    fill="none" stroke={springGreen} strokeWidth="2" strokeLinejoin="round" />
                );
              })()}

              {/* Damper — separate, offset to the right */}
              {(() => {
                const dx = 200;
                const dTop = chassisY + 24;
                const dBot = wheelY - 4;
                const pistonY = dTop + (dBot - dTop) * 0.42;
                return (
                  <>
                    <rect x={dx - 6} y={pistonY} width="12" height={dBot - pistonY}
                      rx="2" fill={metalDark} stroke={damperOrange} strokeWidth="1.2" />
                    <line x1={dx} y1={dTop} x2={dx} y2={pistonY + 2}
                      stroke={damperOrange} strokeWidth="1.8" />
                    <circle cx={dx} cy={dTop} r="2.5" fill={damperOrange} />
                    <circle cx={dx} cy={dBot} r="2.5" fill={damperOrange} />
                  </>
                );
              })()}

              {/* Upper control arm */}
              <line x1="88" y1={chassisY + 20} x2={kx} y2={wheelY - 14}
                stroke={armBlue} strokeWidth="2.5" />
              <circle cx="88" cy={chassisY + 20} r="3" fill={armBlue} />
              <circle cx={kx} cy={wheelY - 14} r="2.5" fill="hsl(210 100% 40%)" />

              {/* Lower control arm */}
              <line x1="88" y1={wheelY + 14} x2={kx} y2={wheelY + 10}
                stroke={armBlue} strokeWidth="2.5" />
              <circle cx="88" cy={wheelY + 14} r="3" fill={armBlue} />
              <circle cx={kx} cy={wheelY + 10} r="2.5" fill="hsl(210 100% 40%)" />

              {/* Labels — positioned clear of chassis rect */}
              <text x="58" y={(chassisY + 20 + wheelY - 14) / 2 - 4} fill={labelColor} fontSize="7" fontFamily={labelFont}>UPPER</text>
              <text x="58" y={(chassisY + 20 + wheelY - 14) / 2 + 4} fill={labelColor} fontSize="7" fontFamily={labelFont}>ARM</text>
              <text x="60" y={wheelY + 26} fill={labelColor} fontSize="7" fontFamily={labelFont}>LOWER ARM</text>
            </>
          )}

          {/* ── Chassis ── */}
          <rect x="65" y={chassisY - 6} width="175" height="24" rx="4" fill="hsl(220 12% 13%)" stroke="hsl(220 10% 23%)" strokeWidth="1.5" />
          <text x={kx - 12} y={chassisY + 11} textAnchor="middle" fill={labelColor} fontSize="8" fontFamily={labelFont}>
            CHASSIS {(state.zs * 1000).toFixed(1)}mm
          </text>

          {/* ── Dimension annotation ── */}
          <g fill="none" stroke={labelColor} strokeWidth="0.5" strokeDasharray="2 2" opacity="0.4">
            <line x1="252" y1={chassisY + 8} x2="268" y2={chassisY + 8} />
            <line x1="252" y1={wheelY} x2="268" y2={wheelY} />
            <line x1="260" y1={chassisY + 8} x2="260" y2={wheelY} />
          </g>
          <text x="270" y={(chassisY + wheelY) / 2 + 3} fill={labelColor} fontSize="7" fontFamily={labelFont}>
            {Math.abs(state.springDeflection).toFixed(1)}mm
          </text>

          {/* Arrow markers */}
          <defs>
            <marker id="arrowGreen" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
              <polygon points="0 0, 6 2, 0 4" fill={springGreen} />
            </marker>
            <marker id="arrowOrange" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
              <polygon points="0 0, 6 2, 0 4" fill={damperOrange} />
            </marker>
          </defs>
        </svg>
      </div>
    </div>
  );
}
