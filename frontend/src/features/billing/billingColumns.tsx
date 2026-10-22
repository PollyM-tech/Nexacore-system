import { CustomerLink } from "@/features/admin/CustomerLink";
import type { Column } from "@/shared/components/data/DataTable";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { kes, dateTime } from "@/shared/utils/format";
import type { MonthlyBill, Transaction } from "@/shared/types/api";

export const billColumns: Column<MonthlyBill>[] = [
  {
    key: "customer",
    header: "Customer",
    render: (r) => (
      <div>
        <p className="font-medium text-slate-900 dark:text-white"><CustomerLink customer={r.customer} name={r.customer_name} /></p>
        <p className="text-xs text-slate-400">{r.billing_period ?? r.package_name ?? ""}</p>
      </div>
    ),
  },
  { key: "date", header: "Invoice date", render: r => dateTime(r.invoice_date) },
  { key: "total", header: "Billed", align: "right", render: (r) => <span className="font-semibold">{kes(r.total_amount)}</span> },
  { key: "paid", header: "Allocated / paid", align: "right", render: (r) => kes(r.paid_amount) },
  { key: "due", header: "Outstanding", align: "right", render: (r) => <span className="font-medium text-rose-600">{kes(r.remaining_amount)}</span> },
  { key: "status", header: "Status", render: (r) => <StatusBadge status={r.payment_status} /> },
];

export const txColumns: Column<Transaction>[] = [
  { key: "customer", header: "Customer", render: (r) => r.customer_name ?? "—" },
  { key: "amount", header: "Amount", align: "right", render: (r) => <span className="font-semibold text-emerald-600">{kes(r.amount)}</span> },
  {
    key: "method",
    header: "Method",
    render: (r) => <span className="capitalize">{r.payment_method}</span>,
  },
  { key: "ref", header: "Reference", render: (r) => r.transaction_id || "—" },
  {
    key: "date",
    header: "Date",
    render: (r) => (r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"),
  },
];
