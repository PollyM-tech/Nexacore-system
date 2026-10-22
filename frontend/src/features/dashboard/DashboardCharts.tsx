import { ErrorAlert } from "@/shared/components/feedback/ErrorAlert";
import { CollectionDonut } from "@/features/dashboard/CollectionDonut";
import { MonthlyBillingChart } from "@/features/dashboard/MonthlyBillingChart";
import { YearlyRevenueChart } from "@/features/dashboard/YearlyRevenueChart";
import { useDashboardSummary } from "@/features/dashboard/useDashboardSummary";

export function DashboardCharts() {
  const { data, isLoading, isError, refetch } = useDashboardSummary();

  if (isLoading) {
    return (
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card-surface h-[360px] animate-pulse lg:col-span-2" />
        <div className="card-surface h-[360px] animate-pulse" />
      </div>
    );
  }

  if (isError || !data) return (
    <section className="card-surface p-5">
      <ErrorAlert message="Invoice allocation charts could not be loaded." />
      <button type="button" onClick={() => { void refetch(); }} className="text-sm font-semibold text-brand-600 underline">Try again</button>
    </section>
  );
  const monthly = data.monthly;
  const yearly = data.yearly;
  const collected = data.revenue.collected;
  const outstanding = data.revenue.outstanding;
  if (!monthly.some((row) => row.billed || row.collected || row.due) && !yearly.some((row) => row.billed || row.collected) && !collected && !outstanding) {
    return <section className="card-surface p-5"><h2 className="font-semibold">Invoice allocations</h2><p className="mt-2 text-sm text-slate-500">No billing activity to chart yet.</p></section>;
  }

  return (
    <div className="grid min-w-0 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <MonthlyBillingChart data={monthly} />
      </div>
      <CollectionDonut collected={collected} due={outstanding} />
      <div className="lg:col-span-3">
        <YearlyRevenueChart data={yearly} />
      </div>
    </div>
  );
}
