interface AdapterBadgeProps {
  tool: string;
  color: string;
  connected: boolean;
}

export function AdapterBadge({ tool, color, connected }: AdapterBadgeProps) {
  return (
    <div className="flex items-center gap-1.5" data-testid={`badge-${tool.toLowerCase()}`}>
      <div
        className="w-2 h-2 rounded-full animate-pulse-dot"
        style={{ backgroundColor: connected ? color : "hsl(var(--muted-foreground))" }}
      />
      <span className="text-xs font-mono text-muted-foreground hidden md:inline">{tool}</span>
    </div>
  );
}
