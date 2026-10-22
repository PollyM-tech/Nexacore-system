import { DashboardSection } from "./DashboardSection";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { usePaginatedList } from "@/shared/hooks/usePaginatedList";
import { API } from "@/shared/api/endpoints";
import { ROUTES } from "@/shared/constants/routes";
import { dateTime, kes } from "@/shared/utils/format";
import type { Transaction } from "@/shared/types/api";

const methods: Record<string, string> = {
  cash: "Cash", mpesa: "M-Pesa", bank_transfer: "Bank transfer", card: "Card",
  adjustment: "Manual adjustment", other: "Other",
};
const columns: Column<Transaction>[] = [
  { key: "customer", header: "Customer", render: (r) => r.customer_name || "—" },
  { key: "amount", header: "Amount", align: "right", render: (r) => {
    const amount = Number(r.amount);
    const received = amount > 0 && ["cash", "mpesa", "bank_transfer", "card", "other"].includes(r.payment_method);
    return <div className="whitespace-nowrap"><p className={received ? "font-semibold text-brand-700 dark:text-brand-300" : "font-medium"}>{kes(r.amount)}</p><p className="mt-1 text-xs text-slate-400">{r.payment_method === "adjustment" ? "Adjustment" : amount < 0 ? "Debit / adjustment" : received ? "Received" : "Ledger entry"}</p></div>;
  } },
  { key: "method", header: "Method", render: (r) => <span className="whitespace-nowrap">{methods[r.payment_method] || r.payment_method}</span> },
  { key: "receipt", header: "Receipt / reference", render: (r) => <span className="font-mono text-xs">{r.transaction_id || "—"}</span> },
  { key: "date", header: "Posted", render: (r) => <time className="whitespace-nowrap text-xs" dateTime={r.created_at}>{dateTime(r.created_at)}</time> },
];

export function RecentPaymentsCard() {
  // Share the transactions prefix so payment recording invalidates this preview.
  // Backend model ordering is newest first. This list is never used for totals.
  const query = usePaginatedList<Transaction>("transactions", API.billing.transactions, { page: 1, page_size: 6 });
  const rows = query.data ?? [];
  return (
    <DashboardSection title="Recent payments" description="Latest ledger entries, including clearly marked adjustments."
      to={ROUTES.payments} linkLabel="All payments" loading={query.isLoading} error={query.isError}
      empty={!rows.length} emptyMessage="No payment transactions recorded yet." onRetry={() => { void query.refetch(); }}>
      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} />
      <p className="mt-3 text-xs text-slate-400">M-Pesa references appear here after settlement into the billing ledger.</p>
    </DashboardSection>
  );
}
