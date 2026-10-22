import { useParams } from "react-router-dom";
import { BillingPanel } from "@/features/customers/detail/BillingPanel";
import { CustomerInvoices } from "@/features/customers/detail/CustomerInvoices";
import { DetailHeader } from "@/features/customers/detail/DetailHeader";
import { LiveStatusCard } from "@/features/customers/detail/LiveStatusCard";
import { ProfileCards } from "@/features/customers/detail/ProfileCards";
import { RadiusSessionHistory } from "@/features/customers/detail/RadiusSessionHistory";
import { CustomerPayments } from "@/features/customers/detail/CustomerPayments";
import { useCustomerDetail } from "@/features/customers/detail/useCustomerDetail";
export function CustomerDetailPage() {
  const { customerId } = useParams();
  const query = useCustomerDetail(customerId);
  const data = query.data;
  if (query.isLoading) return <p role="status" className="py-12 text-center">Loading customer…</p>;
  if (query.isError || !data) return <div role="alert" className="py-12 text-center"><p>Customer information is unavailable. The account may not exist, access may be restricted, or the request failed.</p><button type="button" className="mt-3 text-brand-600 underline" onClick={() => { void query.refetch(); }}>Retry customer</button></div>;
  return <div className="min-w-0 space-y-5">
    <DetailHeader customer={data} />
    <ProfileCards customer={data} />
    <div className="grid min-w-0 items-start gap-5 xl:grid-cols-2"><BillingPanel customer={data} /><LiveStatusCard key={data.customer_id} customerId={data.customer_id} mode={data.router_info?.authentication_mode} router={data.router_info?.router_name} /></div>
    {data.router_info?.authentication_mode === "radius" ? <RadiusSessionHistory key={`sessions-${data.customer_id}`} customerId={data.customer_id} /> : null}
    <CustomerPayments key={`payments-${data.customer_id}`} customerId={data.customer_id} />
    <CustomerInvoices key={`bills-${data.customer_id}`} customerId={data.customer_id} />
  </div>;
}
