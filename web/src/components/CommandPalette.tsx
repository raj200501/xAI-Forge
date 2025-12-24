import { useMemo, useState } from "react";
import type { TraceManifest } from "../types/trace";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  traces: TraceManifest[];
  activeTraceId?: string | null;
  onSelectTrace: (traceId: string) => void;
  onStartRun: () => void;
  onReplay: () => void;
}

interface CommandItem {
  id: string;
  label: string;
  action: () => void;
  shortcut?: string;
}

export default function CommandPalette({
  open,
  onClose,
  traces,
  activeTraceId,
  onSelectTrace,
  onStartRun,
  onReplay,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");

  const commands = useMemo<CommandItem[]>(() => {
    const items: CommandItem[] = [
      {
        id: "start-run",
        label: "Start a new run",
        action: () => {
          onStartRun();
          onClose();
        },
      },
    ];
    if (activeTraceId) {
      items.push({
        id: "replay",
        label: "Replay current trace",
        action: () => {
          onReplay();
          onClose();
        },
      });
      items.push({
        id: "copy",
        label: "Copy trace id",
        action: () => {
          navigator.clipboard?.writeText(activeTraceId).catch(() => undefined);
          onClose();
        },
      });
    }
    for (const trace of traces) {
      items.push({
        id: `jump-${trace.trace_id}`,
        label: `Jump to trace ${trace.trace_id}`,
        action: () => {
          onSelectTrace(trace.trace_id);
          onClose();
        },
      });
    }
    return items;
  }, [activeTraceId, onClose, onReplay, onSelectTrace, onStartRun, traces]);

  const filtered = commands.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()),
  );

  if (!open) return null;

  return (
    <div className="palette-overlay" onClick={onClose}>
      <div className="palette" onClick={(event) => event.stopPropagation()}>
        <input
          autoFocus
          placeholder="Type a command..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <div className="palette-results">
          {filtered.length === 0 && <p className="empty">No commands.</p>}
          {filtered.map((item) => (
            <button
              key={item.id}
              type="button"
              className="palette-item"
              onClick={item.action}
            >
              <span>{item.label}</span>
              {item.shortcut && <kbd>{item.shortcut}</kbd>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
