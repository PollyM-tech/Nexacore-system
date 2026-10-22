import { kes } from "@/shared/utils/format";
import { DASHBOARD_TONES } from "@/shared/constants/dashboardTones";
import { LiveStatsCard } from "@/features/portal/LiveStatsCard";
import { ProfileCard } from "@/features/portal/ProfileCard";
import { BillsList } from "@/features/portal/BillsList";
import { usePortalProfile } from "@/features/portal/portalAuth";
import { useLiveStats, usePortalBills } from "@/features/portal/portalData";
import { PageHeader } from "@/shared/components/layout/PageHeader";

export function PortalDashboardPage() {
  const { data: profile } = usePortalProfile();
  const stats = useLiveStats();
  const bills = usePortalBills();
  const recent = bills.data?.slice(0, 3);

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Hi, ${profile?.customer_name?.split(" ")[0] ?? "there"} 👋`}
        description="Here's your connection and account overview."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {[["Account balance", profile ? kes(profile.balance) : "Unavailable"], ["Account status", profile?.customer_status || "Unavailable"]].map(([label, value], index) => <section key={label} className={`rounded-2xl bg-gradient-to-br p-5 text-white shadow-sm ${DASHBOARD_TONES[index]}`}><h2 className="text-sm font-semibold">{label}</h2><p className="mt-3 text-2xl font-bold">{value}</p></section>)}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <ProfileCard profile={profile} />
        <LiveStatsCard stats={stats.data} loading={stats.isLoading} />
      </div>
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Recent bills</h2>
        <BillsList bills={recent} loading={bills.isLoading} />
      </div>
    </div>
  );
}
