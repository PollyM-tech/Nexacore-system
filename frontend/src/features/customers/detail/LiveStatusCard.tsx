import { Button } from "flowbite-react";
import { DetailCard, InfoRow } from "./InfoRow";
import { useCustomerLiveStats } from "./useCustomerLiveStats";
import { useCustomerRadiusSummary } from "./useCustomerRadius";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { bytes, dateTime, duration } from "@/shared/utils/format";

export function LiveStatusCard({ customerId, mode, router }: { customerId: string; mode?: string | null; router?: string | null }) {
  const live = useCustomerLiveStats(customerId);
  const radius = mode === "radius";
  const summary = useCustomerRadiusSummary(customerId, radius);
  const d = live.isError ? undefined : live.data;
  const account = summary.isError ? undefined : summary.data;
  const routerLive = d?.live_stats_available === true;
  const accountingOnline = account?.online ?? (!routerLive && d?.status === "online" && radius);
  const checking = live.isLoading && (!radius || summary.isLoading);
  const localUncertain = !radius && (!d || (!!d.message && !routerLive));
  const label = checking ? "Checking" : routerLive || accountingOnline ? "Online" : radius && account ? "Not online in accounting" : localUncertain || !d ? "Unable to verify" : "Offline";
  // latest_session can be closed while another session is active. Never present
  // such a row as the active session just because the summary says online.
  const latest = account?.latest_session ?? d?.accounting;
  const activeAccounting = latest?.online ? latest : undefined;
  const counters = routerLive ? { ip: d.address, mac: d.caller_id, uptime: d.uptime, down: d.bytes_out, up: d.bytes_in }
    : activeAccounting ? { ip: activeAccounting.ip_address, mac: activeAccounting.mac_address, uptime: duration(activeAccounting.duration_seconds), down: activeAccounting.download_bytes, up: activeAccounting.upload_bytes } : undefined;
  return <DetailCard title="Current connection status" action={<Button color="light" size="xs" disabled={live.isFetching || (radius && summary.isFetching)} onClick={() => { void live.refetch(); if (radius) void summary.refetch(); }}>Refresh status</Button>}>
    <div className="my-3"><StatusBadge status={label} /></div>
    <InfoRow label="Source">{routerLive ? "RouterOS live session" : accountingOnline ? "RADIUS accounting" : radius ? "RADIUS accounting / unavailable" : "RouterOS"}</InfoRow>
    <InfoRow label="Assigned router">{router || "Unconfigured"}</InfoRow>
    <InfoRow label="Router live data">{live.isLoading ? "Checking" : live.isError ? "Unavailable — access or request failed" : routerLive ? "Available" : "Unavailable — API access or no matching session"}</InfoRow>
    {radius ? <InfoRow label="Accounting state">{summary.isLoading ? "Checking" : summary.isError ? "Unavailable" : account?.online ? "Online (fresh accounting)" : "No fresh active session"}</InfoRow> : null}
    {counters ? <><InfoRow label="IP address">{counters.ip || "—"}</InfoRow><InfoRow label="MAC / caller">{counters.mac || "—"}</InfoRow><InfoRow label="Uptime">{counters.uptime || "—"}</InfoRow><InfoRow label="Download">{bytes(counters.down)}</InfoRow><InfoRow label="Upload">{bytes(counters.up)}</InfoRow></> : null}
    {radius ? <InfoRow label="Latest session accounting update">{dateTime(latest?.updated_at || latest?.started_at)}</InfoRow> : null}
    {radius && account?.online && latest && !latest.online && !routerLive ? <p className="mt-3 text-sm text-slate-500">Accounting confirms an active session, but the newest history record is not that session. Current-session accounting counters are unavailable.</p> : null}
    {radius && latest && !latest.online && !latest.stopped_at ? <p className="mt-3 text-sm text-amber-600">Latest accounting row is stale or incomplete; an absent stop packet does not prove it is online.</p> : null}
    {live.isError || (radius && summary.isError) ? <p role="alert" className="mt-3 text-sm text-amber-600">Some connection information could not be verified. Cached readings are not presented as current. Use Refresh status to retry.</p> : null}
    {account ? <div className="mt-4 rounded-xl bg-slate-50 p-3 dark:bg-ink-800"><p className="mb-2 text-xs font-semibold uppercase text-slate-500">Lifetime RADIUS accounting</p><InfoRow label="Sessions">{account.totals.session_count}</InfoRow><InfoRow label="Duration">{duration(account.totals.total_session_seconds)}</InfoRow><InfoRow label="Download">{bytes(account.totals.total_output_bytes)}</InfoRow><InfoRow label="Upload">{bytes(account.totals.total_input_bytes)}</InfoRow></div> : null}
    <p className="mt-4 text-xs leading-relaxed text-slate-500">{radius ? "RADIUS counters update approximately every 5 minutes; sessions become stale after 15 minutes without accounting activity. " : "Router errors cannot establish that a customer is offline. "}Traffic values are cumulative session bytes, not throughput. Last successful live check: {live.dataUpdatedAt ? dateTime(new Date(live.dataUpdatedAt).toISOString()) : "—"}.</p>
  </DetailCard>;
}
