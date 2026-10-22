import { Alert, TabItem, Tabs } from "flowbite-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { useAdminOptions as usePaginatedList } from "@/features/admin/useAdminOptions";
import { apiError } from "@/shared/utils/apiError";
import type { Customer, Router } from "@/shared/types/api";
import { HistoricalLogsTable } from "./HistoricalLogsTable";
import { ReportFilters } from "./ReportFilters";
import { ReportSummaryCards } from "./ReportSummaryCards";
import { RouterSummariesTable } from "./RouterSummariesTable";
import { TopUsersTable } from "./TopUsersTable";
import type { ReportFilterState } from "./types";
import {
  useConsumptionSummary,
  useRouterSummaries,
  useTopUsers,
  useUsageLogs,
} from "./useBandwidthReports";

const EMPTY: ReportFilterState = { date_from: "", date_to: "", router: "", customer: "" };

export function UsageReportsView() {
  const [draft, setDraft] = useState<ReportFilterState>(EMPTY);
  const [applied, setApplied] = useState<ReportFilterState>(EMPTY);
  const qc = useQueryClient();

  const summary = useConsumptionSummary();
  const logs = useUsageLogs(applied, true);
  const topUsers = useTopUsers(applied, true);
  const routerSummaries = useRouterSummaries(applied, true);

  const routers = usePaginatedList<Router>("routers", API.routers);
  const customers = usePaginatedList<Customer>("customers", API.customers);
  const routerOptions = (routers.data ?? []).map((r) => ({ value: String(r.id), label: r.name }));
  const customerOptions = (customers.data ?? []).map((c) => ({
    value: c.customer_id,
    label: `${c.customer_name} (${c.customer_id})`,
  }));

  const sync = useMutation({
    mutationFn: () => api.post(API.bandwidth.sync, { router: applied.router || undefined }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bandwidth-summary"] });
      qc.invalidateQueries({ queryKey: ["bandwidth-logs"] });
      qc.invalidateQueries({ queryKey: ["bandwidth-top-users"] });
      qc.invalidateQueries({ queryKey: ["bandwidth-router-summaries"] });
    },
    onError: (e) => window.alert(apiError(e)),
  });

  const exportCsv = async () => {
    const params = Object.fromEntries(Object.entries(applied).filter(([, v]) => v !== ""));
    const res = await api.get(API.bandwidth.export, { params, responseType: "blob" });
    const url = URL.createObjectURL(res.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "bandwidth_usage.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">Stored RouterOS usage snapshots. The backend sums cumulative snapshots; repeated samples can double-count bytes. These are not accurate consumption totals and are separate from RADIUS accounting.</p>
      {summary.isError ? <Alert color="failure">Usage summary unavailable.</Alert> : summary.isLoading ? <p>Loading summary…</p> : <ReportSummaryCards summary={summary.data} />}
      {(routers.isError || customers.isError) && <Alert color="failure">Some filter options are unavailable.</Alert>}
      <ReportFilters
        draft={draft}
        onChange={(patch) => setDraft((d) => ({ ...d, ...patch }))}
        routerOptions={routerOptions}
        customerOptions={customerOptions}
        onQuery={() => setApplied(draft)}
        onSync={() => sync.mutate()}
        syncing={sync.isPending}
      />
      <Tabs variant="underline" aria-label="Usage reports">
        <TabItem active title="Historical Usage Logs">
          {logs.isError ? <Alert color="failure">Usage logs unavailable.</Alert> : logs.isLoading ? <p>Loading logs…</p> : <HistoricalLogsTable data={logs.data} onExport={() => void exportCsv().catch(()=>window.alert("Export failed. Check your permissions and connection."))} />}
        </TabItem>
        <TabItem title="Top 50 Users">
          {topUsers.isError ? <Alert color="failure">Top users unavailable.</Alert> : topUsers.isLoading ? <p>Loading users…</p> : <TopUsersTable rows={topUsers.data ?? []} />}
        </TabItem>
        <TabItem title="Router Summaries">
          {routerSummaries.isError ? <Alert color="failure">Router summaries unavailable.</Alert> : routerSummaries.isLoading ? <p>Loading routers…</p> : <RouterSummariesTable rows={routerSummaries.data ?? []} />}
        </TabItem>
      </Tabs>
    </div>
  );
}
