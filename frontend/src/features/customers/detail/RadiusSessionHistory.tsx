import { DetailCard } from "./InfoRow";
import { useCustomerRadiusSessions } from "./useCustomerRadius";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { bytes, dateTime, duration } from "@/shared/utils/format";
import type { RadiusSession } from "@/shared/types/api";
const columns: Column<RadiusSession>[] = [
  { key: "start", header: "Start", render: (r) => <span className="whitespace-nowrap">{dateTime(r.started_at)}</span> },
  { key: "stop", header: "Stop", render: (r) => <span className="whitespace-nowrap">{dateTime(r.stopped_at)}</span> },
  { key: "duration", header: "Duration", render: (r) => <span className="whitespace-nowrap">{duration(r.duration_seconds)}</span> },
  { key: "ip", header: "IP", render: (r) => r.ip_address || "—" },
  { key: "mac", header: "MAC", render: (r) => r.mac_address || "—" },
  { key: "router", header: "Router", render: (r) => r.router_name || r.nas_ip_address || "—" },
  { key: "upload", header: "Upload", render: (r) => <span className="whitespace-nowrap">{bytes(r.upload_bytes)}</span> },
  { key: "download", header: "Download", render: (r) => <span className="whitespace-nowrap">{bytes(r.download_bytes)}</span> },
  { key: "cause", header: "Termination cause", render: (r) => r.terminate_cause || "—" },
  { key: "online", header: "Accounting state", render: (r) => <span className="whitespace-nowrap">{r.online ? "Online (fresh)" : r.stopped_at ? "Stopped" : "Stale / incomplete"}</span> },
];
export function RadiusSessionHistory({ customerId }: { customerId: string }) {
  const query = useCustomerRadiusSessions(customerId);
  const rows = query.data?.results ?? [];
  return <DetailCard title="Recent RADIUS accounting history" action={<button type="button" className="text-sm text-brand-600 underline" disabled={query.isFetching} onClick={() => { void query.refetch(); }}>Refresh history</button>}>
    <p className="mb-4 text-xs text-slate-500">Newest 20 accounting sessions, not unlimited history. Router names reflect the customer’s current assignment; NAS IP identifies the recorded access server.</p>
    <ListPageSection isLoading={query.isLoading} isError={query.isError} isEmpty={!rows.length} emptyTitle="No accounting history" emptyDescription="Sessions will appear after RADIUS accounting starts." errorMessage="Accounting history is unavailable."><DataTable columns={columns} rows={rows} rowKey={(r) => r.id} /></ListPageSection>
  </DetailCard>;
}
