interface PanelShellProps {
  title: string;
  tool: string;
  color: string;
  children: React.ReactNode;
}

export function PanelShell({ title, tool, color, children }: PanelShellProps) {
  return (
    <div className="h-full flex flex-col rounded-md border border-border bg-card overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-card shrink-0">
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-xs font-mono font-medium text-foreground">{tool}</span>
        <span className="text-xs text-muted-foreground ml-auto">{title}</span>
      </div>
      {/* Panel content */}
      <div className="flex-1 min-h-0 overflow-auto p-2.5">
        {children}
      </div>
    </div>
  );
}
