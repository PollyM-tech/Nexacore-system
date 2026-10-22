import { DASHBOARD_TONES } from "@/shared/constants/dashboardTones";
import { Link } from "react-router-dom";
import { PageHeader } from "@/shared/components/layout/PageHeader";
import { TableSkeleton } from "@/shared/components/ui/TableSkeleton";
import { PlatformError } from "./PlatformFeedback";
import { usePlatformSummary } from "./queries";
export function PlatformDashboard() {
 const q=usePlatformSummary();const s=q.data;
 if(q.isPending)return <TableSkeleton />;
 if(q.isError)return <PlatformError error={q.error} retry={()=>void q.refetch()} />;
 const cards:[string,number|undefined][]=[["Total ISPs",s?.organizations.total],["Active ISPs",s?.organizations.active],["Total users",s?.users.total],["Total customers",s?.customers.total],["Active customers",s?.customers.active],["Enabled routers",s?.routers.active],["Total packages",s?.packages.total]];
 return <><PageHeader title="Platform dashboard" description="Cross-organization Lintech inventory and account totals." /><div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label,value],index)=><section key={label} className={`rounded-2xl bg-gradient-to-br p-5 text-white shadow-sm ${DASHBOARD_TONES[index % DASHBOARD_TONES.length]}`}><h2 className="text-sm font-semibold text-white">{label}</h2><p className="mt-2 text-3xl font-semibold">{typeof value==="number"&&Number.isFinite(value)?value.toLocaleString("en-KE"):"Unavailable"}</p></section>)}</div><p className="text-sm font-semibold text-white">Enabled routers are configured as active, not verified online. Counts are inventory/account metrics, not real-time health or SaaS subscription status.</p><Link className="text-brand-600 underline" to="/superadmin/organizations">Manage ISP organizations</Link></>;
}
