import { useEffect, useMemo, useState } from "react";
import { Button, Select } from "flowbite-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { customerColumns } from "./customerColumns";
import { OnlineBadge } from "./OnlineBadge";
import { useOnlineStatus } from "./useOnlineStatus";
import { useCustomerOptions } from "./useCustomerOptions";
import { invalidateCustomer } from "./customerQueryKeys";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { ROUTES } from "@/shared/constants/routes";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { TablePagination } from "@/shared/components/data/TablePagination";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { ErrorAlert } from "@/shared/components/feedback/ErrorAlert";
import type { Customer } from "@/shared/types/api";
const filters: Record<string, Record<string, string | number>> = {
  all: {}, active: { status: "active" }, inactive: { status: "disconnected" },
  free: { free: 1 }, due: { due: 1 }, expired: { expired: 1 }, left: { status: "left" }, online: {},
};
export function CustomersManager() {
  const [params, setParams] = useSearchParams();
  const filter = params.get("filter") || "all";
  const zone = params.get("zone") || "";
  const search = params.get("q") || "";
  const auth = params.get("auth") || "";
  const [page, setPage] = useState(1);
  const client = useQueryClient();
  const online = useOnlineStatus();
  const options = useCustomerOptions();
  const serverParams = { ...(filters[filter] ?? {}), ...(zone ? { zone } : {}) };
  const query = useQuery({ queryKey: ["customers", serverParams], queryFn: async () => (await api.get<Customer[]>(API.customers, { params: serverParams })).data });
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); };
  const key = params.toString();
  useEffect(() => { setPage(1); }, [key]);
  const rows = useMemo(() => (query.data ?? []).filter((r) => {
    const text = [r.customer_id, r.customer_name, r.phone_number, r.address, r.package_name, r.zone_name, r.pppoe_name].join(" ").toLowerCase();
    return text.includes(search.toLowerCase().trim())
      && (!auth || (auth === "unknown" ? !["radius", "local_secret"].includes(r.authentication_mode ?? "") : r.authentication_mode === auth))
      && (filter !== "online" || (online.ready && online.isOnline(r.pppoe_name)));
  }), [query.data, search, auth, filter, online.ready, online.isOnline]);
  const totalPages = Math.max(1, Math.ceil(rows.length / 10));
  const currentPage = Math.min(page, totalPages);
  const status = useMutation({
    mutationFn: async (v: { id: string; status: string }) => (await api.post<{ warning?: string }>(API.customerStatus(v.id), { status: v.status })).data,
    onSuccess: (data, vars) => { void invalidateCustomer(client, vars.id); setNotice(data.warning ? "Account status saved, but network synchronization needs attention. Verify the connection before retrying." : "Account status updated. Session state is checked separately."); },
  });
  const [notice, setNotice] = useState("");
  const columns: Column<Customer>[] = [...customerColumns,
    { key: "session", header: "Session state", render: (r) => <OnlineBadge online={online.isOnline(r.pppoe_name)} ready={online.ready} error={online.isError} loading={online.isLoading} hasPppoe={!!r.pppoe_name} /> },
    { key: "actions", header: "Actions", render: (r) => <div className="flex items-center gap-3 whitespace-nowrap text-xs">
      <Link to={`${ROUTES.customers}/${encodeURIComponent(r.customer_id)}/edit`} className="text-brand-700 underline dark:text-brand-300">Edit</Link>
      <button type="button" className="text-slate-600 underline dark:text-slate-300" disabled={status.isPending} onClick={() => {
        const nextStatus = r.customer_status === "active" ? "disconnected" : "active";
        if (window.confirm(`${nextStatus === "active" ? "Activate" : "Disconnect"} ${r.customer_name}?`)) { setNotice(""); status.mutate({ id: r.customer_id, status: nextStatus }); }
      }}>{r.customer_status === "active" ? "Disconnect" : "Activate"}</button>
    </div> },
  ];
  const sessionChecking = filter === "online" && online.isLoading;
  const sessionError = filter === "online" && online.isError;
  return <div className="space-y-4">
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-48 flex-1"><label htmlFor="customer-search" className="mb-1 block text-xs font-medium">Search customers</label><input id="customer-search" type="search" value={search} onChange={(e) => update("q", e.target.value)} placeholder="Name, ID, phone, username…" className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm focus:outline-2 focus:outline-brand-500 dark:border-slate-700 dark:bg-ink-900" /></div>
      <div><label htmlFor="customer-filter" className="mb-1 block text-xs font-medium">Accounts</label><Select id="customer-filter" value={filter} onChange={(e) => update("filter", e.target.value)}>{Object.keys(filters).map((f) => <option key={f} value={f}>{f === "online" ? "Detected online" : f}</option>)}</Select></div>
      <div><label htmlFor="customer-zone-filter" className="mb-1 block text-xs font-medium">Zone</label><Select id="customer-zone-filter" value={zone} onChange={(e) => update("zone", e.target.value)}><option value="">All zones</option>{options.zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}</Select></div>
      <div><label htmlFor="customer-auth-filter" className="mb-1 block text-xs font-medium">Authentication</label><Select id="customer-auth-filter" value={auth} onChange={(e) => update("auth", e.target.value)}><option value="">All modes</option><option value="radius">RADIUS</option><option value="local_secret">Local secret</option><option value="unknown">Unconfigured / Unknown</option></Select></div>
      <Button color="light" disabled={query.isFetching || online.isLoading} onClick={() => { void query.refetch(); void online.refetch(); }}>Refresh list</Button>
      <Link to={ROUTES.customerNew} className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700">Add customer</Link>
    </div>
    <p className="text-xs text-slate-500">Session state is router detection, not account status. “Not detected” does not prove the customer is offline; unreachable routers may be omitted.</p>
    {online.isError ? <div role="alert" className="text-sm text-amber-600">Session detection unavailable. <button type="button" className="underline" onClick={() => { void online.refetch(); }}>Retry detection</button></div> : null}
    {options.isError ? <p role="alert" className="text-sm text-amber-600">Filter options unavailable. <button type="button" onClick={options.retry} className="underline">Retry</button></p> : null}
    {notice ? <p role="status" className="rounded-xl bg-slate-100 p-3 text-sm dark:bg-slate-800">{notice}</p> : null}
    {status.isError ? <ErrorAlert message="Status update failed. Check your permissions and try again." /> : null}
    <ListPageSection isLoading={query.isLoading || sessionChecking} isError={query.isError || sessionError} isEmpty={!rows.length}
      errorMessage="Could not verify the requested customer list." emptyTitle="No customers found" emptyDescription="Try another search or filter." emptyIcon="users">
      <DataTable columns={columns} rows={rows.slice((currentPage - 1) * 10, currentPage * 10)} rowKey={(r) => r.id} />
      <TablePagination page={currentPage} totalPages={totalPages} onPage={setPage} rangeLabel={`${rows.length} matching customers`} />
    </ListPageSection>
    {query.isError ? <Button color="light" onClick={() => { void query.refetch(); }}>Retry customers</Button> : null}
  </div>;
}
