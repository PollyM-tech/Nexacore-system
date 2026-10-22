import { DASHBOARD_TONES } from "@/shared/constants/dashboardTones";
import { Link } from "react-router-dom";
import { useDashboardSummary } from "./useDashboardSummary";
import { useOnlineStatus } from "@/features/customers/useOnlineStatus";
import { Icon, type IconName } from "@/shared/components/icons/Icon";
import { ROUTES } from "@/shared/constants/routes";
import { kes } from "@/shared/utils/format";

type Metric = { title: string; value: string | number | undefined; hint: string; icon: IconName; to: string; loading: boolean; error: boolean };

export function DashboardStatsGrid() {
  const summary = useDashboardSummary();
  const online = useOnlineStatus();
  const data = summary.data;
  const common = { loading: summary.isLoading, error: summary.isError };
  const cards: Metric[] = [
    { title: "Total Customers", value: data?.customers.total, hint: "All subscriber accounts", icon: "users", to: ROUTES.customers, ...common },
    { title: "Active Customers", value: data?.customers.active, hint: "Active account status", icon: "check", to: `${ROUTES.customers}?filter=active`, ...common },
    { title: "Online PPPoE Users", value: online.ready ? online.count : undefined, hint: "Detected usernames · every 30s", icon: "activity", to: `${ROUTES.customers}?filter=online`, loading: online.isLoading, error: online.isError },
    { title: "Today Received", value: kes(data?.revenue.received?.today), hint: "Positive received payments", icon: "cash", to: ROUTES.payments, ...common },
    { title: "This Week", value: kes(data?.revenue.received?.week), hint: "Received since Monday", icon: "calendar", to: ROUTES.payments, ...common },
    { title: "This Month", value: kes(data?.revenue.received?.month), hint: "Received since month start", icon: "billing", to: ROUTES.payments, ...common },
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card, index) => <Link to={card.to} key={card.title} aria-busy={card.loading}
          className={`min-w-0 rounded-2xl bg-gradient-to-br p-5 text-white shadow-sm transition hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 ${DASHBOARD_TONES[index % DASHBOARD_TONES.length]}`}>
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-white">{card.title}</p>
            <span className="rounded-lg bg-white/20 p-2 text-white"><Icon name={card.icon} className="h-4 w-4" /></span>
          </div>
          {card.loading ? <div className="my-3 h-8 w-32 animate-pulse rounded bg-white/20"><span className="sr-only">Loading</span></div>
            : <p className="mt-3 break-words text-2xl font-semibold tracking-tight text-white">{card.error ? "Unavailable" : card.value ?? "—"}</p>}
          <p className="mt-3 text-xs text-white">{card.error ? "Latest check failed · use Refresh" : card.hint}</p>
        </Link>)}
      </div>
      <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">Received totals exclude adjustments and use the application’s reporting timezone. Online detection depends on router API availability; unreachable routers can cause an incomplete count.</p>
    </div>
  );
}
