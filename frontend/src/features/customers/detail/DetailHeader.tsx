import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "flowbite-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { ROUTES } from "@/shared/constants/routes";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { invalidateCustomer } from "../customerQueryKeys";
import type { CustomerDetail } from "@/shared/types/api";
export function DetailHeader({ customer }: { customer: CustomerDetail }) {
  const client = useQueryClient();
  const [notice, setNotice] = useState("");
  const mutation = useMutation({ mutationFn: async (status: "active" | "disconnected") => (await api.post<{ warning?: string }>(API.customerStatus(customer.customer_id), { status })).data,
    onSuccess: (data) => { setNotice(data.warning ? "Account status saved, but network synchronization needs attention. Verify the session before retrying." : "Account status updated."); void invalidateCustomer(client, customer.customer_id); },
  });
  return <div className="mb-6 space-y-3">
    <Link className="text-sm text-brand-600 underline" to={ROUTES.customers}>← Customers</Link>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="min-w-0"><h1 className="break-words text-2xl font-bold">{customer.customer_name}</h1><p className="mt-1 text-sm text-slate-500">Customer {customer.customer_id}</p><div className="mt-2"><StatusBadge status={customer.customer_status} /></div></div>
      <div className="flex flex-wrap items-center gap-3">
        <Link to={`${ROUTES.customers}/${encodeURIComponent(customer.customer_id)}/edit`} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700">Edit customer</Link>
        <Link to={`${ROUTES.payments}?customer=${encodeURIComponent(customer.customer_id)}`} className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white">Record payment</Link>
        <Button color="light" size="sm" disabled={mutation.isPending} onClick={() => {
          const status = customer.customer_status === "active" ? "disconnected" : "active";
          if (window.confirm(`${status === "active" ? "Activate" : "Disconnect"} this customer?`)) { setNotice(""); mutation.mutate(status); }
        }}>{mutation.isPending ? "Updating…" : customer.customer_status === "active" ? "Disconnect account" : "Activate account"}</Button>
      </div>
    </div>
    {notice ? <p role="status" className="text-sm text-slate-500">{notice}</p> : null}
    {mutation.isError ? <p role="alert" className="text-sm text-rose-600">Status update failed. Check access and try again.</p> : null}
  </div>;
}
