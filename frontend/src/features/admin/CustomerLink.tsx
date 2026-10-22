import { Link } from "react-router-dom";
import { useAdminOptions } from "./useAdminOptions";
import { API } from "@/shared/api/endpoints";
import type { Customer } from "@/shared/types/api";
export function CustomerLink({ customer, name }: { customer?: number; name?: string }) {
  return customer ? <ResolvedCustomerLink customer={customer} name={name} /> : <>{name || "—"}</>;
}
function ResolvedCustomerLink({ customer, name }: { customer: number; name?: string }) {
  // Shared complete customer list maps the invoice's internal PK to the external
  // customer ID used by detail routes. This is one cached request, not N+1.
  const query = useAdminOptions<Customer>("customers", API.customers);
  const row = query.data?.find(c => c.id === customer);
  return row ? <Link className="text-brand-600 underline focus-visible:outline-2" to={`/admin/customers/${encodeURIComponent(row.customer_id)}`}>{name || row.customer_name}</Link> : <>{name || "—"}</>;
}
