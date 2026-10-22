import { DashboardSection } from "./DashboardSection";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { usePaginatedList } from "@/shared/hooks/usePaginatedList";
import { API } from "@/shared/api/endpoints";
import { ROUTES } from "@/shared/constants/routes";
import { dateTime } from "@/shared/utils/format";
import type { Router } from "@/shared/types/api";

export function RouterStatusCard() {
  const query = usePaginatedList<Router>("routers", API.routers, { page: 1, page_size: 5 });
  const rows = query.data ?? [];
  return (
    <DashboardSection title="Router status" description="Last stored API connection-test results."
      to={ROUTES.routers} linkLabel="All routers" loading={query.isLoading} error={query.isError}
      empty={!rows.length} emptyMessage="No routers configured yet." onRetry={() => { void query.refetch(); }}>
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {rows.map((router) => <li key={router.id} className="space-y-2 py-4 first:pt-0 last:pb-0">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0"><p className="break-words text-sm font-semibold">{router.name}</p><p className="mt-1 break-all font-mono text-xs text-slate-500">{router.host}</p></div>
            <StatusBadge status={router.status || "unknown"} />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <span>Checked: {router.last_checked ? dateTime(router.last_checked) : "Never"}</span>
            <StatusBadge status={router.is_active ? "enabled" : "disabled"} />
          </div>
        </li>)}
      </ul>
      <p className="mt-4 text-xs text-slate-400">Enabled is configuration only. Refreshing this list does not test router connectivity.</p>
    </DashboardSection>
  );
}
