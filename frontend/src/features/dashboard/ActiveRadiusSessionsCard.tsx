import { Link } from "react-router-dom";
import { DashboardSection } from "./DashboardSection";
import { useActiveRadiusSessions } from "./useActiveRadiusSessions";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { ROUTES } from "@/shared/constants/routes";
import { bytes, dateTime, duration } from "@/shared/utils/format";
import type { RadiusSession } from "@/shared/types/api";

const columns: Column<RadiusSession>[] = [
  { key: "customer", header: "Customer", render: (r) => <div className="min-w-32">
    {r.customer_id ? <Link to={`${ROUTES.customers}/${encodeURIComponent(r.customer_id)}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">{r.customer_name || r.customer_id}</Link> : r.customer_name || "Unmapped customer"}
    <div className="mt-1"><StatusBadge status={r.online ? "online" : "offline"} /></div>
  </div> },
  { key: "username", header: "Username", render: (r) => <span className="font-mono text-xs">{r.username}</span> },
  { key: "ip", header: "IP address", render: (r) => <span className="whitespace-nowrap font-mono text-xs">{r.ip_address || "—"}</span> },
  { key: "mac", header: "MAC / caller", render: (r) => <span className="whitespace-nowrap font-mono text-xs">{r.mac_address || "—"}</span> },
  { key: "router", header: "Router", render: (r) => r.router_name || r.nas_ip_address || "—" },
  { key: "uptime", header: "Uptime", render: (r) => <div className="whitespace-nowrap" title={`Started: ${dateTime(r.started_at)}`}>
    <p>{duration(r.duration_seconds)}</p><p className="mt-1 text-xs text-slate-400">Since {dateTime(r.started_at)}</p>
  </div> },
  { key: "download", header: "Download", align: "right", render: (r) => <span className="whitespace-nowrap">{bytes(r.download_bytes)}</span> },
  { key: "upload", header: "Upload", align: "right", render: (r) => <span className="whitespace-nowrap">{bytes(r.upload_bytes)}</span> },
];

export function ActiveRadiusSessionsCard() {
  const query = useActiveRadiusSessions();
  const rows = query.data?.results ?? [];
  return (
    <DashboardSection title="Active RADIUS sessions" description="Up to 8 newest active accounting sessions · refreshes every 30 seconds."
      loading={query.isLoading} error={query.isError} empty={!rows.length}
      emptyMessage="No fresh active RADIUS sessions detected." onRetry={() => { void query.refetch(); }}>
      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} />
      <p className="mt-3 text-xs leading-relaxed text-slate-400">Uptime and cumulative traffic are the latest accounting values, updated approximately every 5 minutes. Sessions with no accounting activity for 15 minutes are excluded. This preview is not a total online-user count.</p>
    </DashboardSection>
  );
}
