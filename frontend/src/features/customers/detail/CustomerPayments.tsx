import { useState } from "react";
import { useCustomerPayments } from "./useCustomerPayments";
import { DetailCard } from "./InfoRow";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { TablePagination } from "@/shared/components/data/TablePagination";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { dateTime, kes } from "@/shared/utils/format";
import type { Transaction } from "@/shared/types/api";
const methods: Record<string, string> = { cash: "Cash", mpesa: "M-Pesa", bank_transfer: "Bank transfer", card: "Card", adjustment: "Manual adjustment", other: "Other" };
const columns: Column<Transaction>[] = [
  { key: "amount", header: "Amount", align: "right", render: (r) => <div className="whitespace-nowrap"><span className="font-semibold">{kes(r.amount)}</span><p className="text-xs text-slate-400">{r.payment_method === "adjustment" || Number(r.amount) < 0 ? "Adjustment / debit" : Number(r.amount) > 0 && ["cash", "mpesa", "bank_transfer", "card", "other"].includes(r.payment_method) ? "Received" : "Ledger entry"}</p></div> },
  { key: "method", header: "Method", render: (r) => methods[r.payment_method] || r.payment_method },
  { key: "receipt", header: "Receipt / reference", render: (r) => <span className="font-mono text-xs">{r.transaction_id || "—"}</span> },
  { key: "by", header: "Received by", render: (r) => r.received_by_username || "—" },
  { key: "notes", header: "Notes", render: (r) => <span className="block min-w-36 max-w-72 break-words">{r.notes || "—"}</span> },
  { key: "date", header: "Posted", render: (r) => <span className="whitespace-nowrap">{dateTime(r.created_at)}</span> },
];
export function CustomerPayments({ customerId }: { customerId: string }) {
  const [page, setPage] = useState(1);
  const query = useCustomerPayments(customerId, page);
  const data = query.data;
  return <DetailCard title="Payment history" action={<button type="button" className="text-sm text-brand-600 underline" disabled={query.isFetching} onClick={() => { void query.refetch(); }}>Refresh payments</button>}>
    <p className="mb-4 text-xs text-slate-500">Newest ledger entries first. Adjustments are separate from received payments.</p>
    <ListPageSection isLoading={query.isLoading} isError={query.isError} isEmpty={!data?.results.length} emptyTitle="No payments" emptyDescription="This customer has no recorded transactions." errorMessage="Payment history could not be loaded.">
      <DataTable columns={columns} rows={data?.results ?? []} rowKey={(r) => r.id} />
      <TablePagination page={data?.current_page ?? page} totalPages={data?.total_pages ?? Math.ceil((data?.count ?? 0) / 10)} onPage={setPage} rangeLabel={`${data?.count ?? 0} transactions · server page ${page}`} />
    </ListPageSection>
    {query.isError && page > 1 ? <button type="button" className="mt-3 text-sm text-brand-600 underline" onClick={() => setPage(1)}>Return to first page</button> : null}
  </DetailCard>;
}
