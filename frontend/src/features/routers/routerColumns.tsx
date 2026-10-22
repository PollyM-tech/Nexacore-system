import type { Column } from "@/shared/components/data/DataTable";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import type { Router } from "@/shared/types/api";
import { dateTime } from "@/shared/utils/format";
export const routerColumns: Column<Router>[] = [
  { key: "name", header: "Router", render: r => <div><p className="font-medium">{r.name}</p><p className="text-xs text-slate-500">{r.description || "—"}</p></div> },
  { key: "host", header: "Host / API port", render: r => <span className="whitespace-nowrap font-mono">{r.host}:{r.port ?? "—"}</span> },
  { key: "ssl", header: "SSL", render: r => r.use_ssl ? "Yes" : "No" },
  { key: "enabled", header: "Configuration", render: r => r.is_active ? "Enabled" : "Disabled" },
  { key: "status", header: "Stored connection result", render: r => <StatusBadge status={r.status ?? "unknown"} /> },
  { key: "checked", header: "Last checked", render: r => dateTime(r.last_checked) },
];
