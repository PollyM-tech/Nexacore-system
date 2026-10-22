import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DetailCard } from "./InfoRow";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { TablePagination } from "@/shared/components/data/TablePagination";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { kes } from "@/shared/utils/format";
import type { MonthlyBill, Paginated } from "@/shared/types/api";
const columns: Column<MonthlyBill>[] = [
  { key: "period", header: "Billing period", render: (r) => r.billing_period || r.invoice_date || "—" },
  { key: "total", header: "Billed", render: (r) => kes(r.total_amount) },
  { key: "paid", header: "Allocated", render: (r) => kes(r.paid_amount) },
  { key: "due", header: "Remaining", render: (r) => kes(r.remaining_amount) },
  { key: "status", header: "Status", render: (r) => <StatusBadge status={r.payment_status} /> },
];
export function CustomerInvoices({ customerId }: { customerId: string }) {
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["monthly-bills", { customer_id: customerId, page, page_size: 6 }], queryFn: async () => (await api.get<Paginated<MonthlyBill>>(API.billing.monthlyBills, { params: { customer_id: customerId, page, page_size: 6 } })).data });
  const data = query.data;
  return <DetailCard title="Monthly invoices" action={<button type="button" className="text-sm text-brand-600 underline" onClick={() => { void query.refetch(); }}>Refresh invoices</button>}>
    <ListPageSection isLoading={query.isLoading} isError={query.isError} isEmpty={!data?.results.length} emptyTitle="No monthly invoices" emptyDescription="Monthly invoices have not been generated yet."><DataTable rows={data?.results ?? []} columns={columns} rowKey={(r) => r.id} /><TablePagination page={page} totalPages={data?.total_pages ?? Math.ceil((data?.count ?? 0) / 6)} onPage={setPage} rangeLabel={`${data?.count ?? 0} monthly invoices`} /></ListPageSection>
  </DetailCard>;
}
