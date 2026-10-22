import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { AddCustomerButton } from "@/features/customers/AddCustomerButton";
import { DashboardStatsGrid } from "@/features/dashboard/DashboardStatsGrid";
import { RecentPaymentsCard } from "@/features/dashboard/RecentPaymentsCard";
import { ActiveRadiusSessionsCard } from "@/features/dashboard/ActiveRadiusSessionsCard";
import { RouterStatusCard } from "@/features/dashboard/RouterStatusCard";
import { DashboardCharts } from "@/features/dashboard/DashboardCharts";
import { PageHeader } from "@/shared/components/layout/PageHeader";
import { Icon } from "@/shared/components/icons/Icon";

const dashboardKeys = ["dashboard-summary", "customers-online", "transactions", "radius-active-sessions", "routers"];

export function DashboardPage() {
  const client = useQueryClient();
  const fetching = useIsFetching({ predicate: (q) => dashboardKeys.includes(String(q.queryKey[0])) });
  const refresh = () => {
    void client.invalidateQueries({ predicate: (q) => dashboardKeys.includes(String(q.queryKey[0])) });
  };
  return (
    <div className="min-w-0 space-y-6">
      <PageHeader title="Network overview" description="Customers, received payments and network operations."
        actions={<>
          <button type="button" onClick={refresh} disabled={fetching > 0}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-ink-900">
            <Icon name="refresh" className={`h-4 w-4 ${fetching ? "animate-spin" : ""}`} />Refresh
          </button>
          <AddCustomerButton />
        </>} />
      <DashboardStatsGrid />
      <ActiveRadiusSessionsCard />
      <div className="grid min-w-0 items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <RecentPaymentsCard />
        <RouterStatusCard />
      </div>
      <DashboardCharts />
    </div>
  );
}
