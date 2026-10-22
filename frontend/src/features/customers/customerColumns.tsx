import { Link } from "react-router-dom";
import type { Column } from "@/shared/components/data/DataTable";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { ROUTES } from "@/shared/constants/routes";
import { kes } from "@/shared/utils/format";
import type { Customer } from "@/shared/types/api";
import { AuthenticationBadge } from "./AuthenticationBadge";
export const customerColumns: Column<Customer>[] = [
  { key: "customer", header: "Customer", render: (r) => <div className="min-w-36"><Link className="font-semibold text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-brand-300" to={`${ROUTES.customers}/${encodeURIComponent(r.customer_id)}`} onClick={(e) => e.stopPropagation()}>{r.customer_name}</Link><p className="mt-1 text-xs text-slate-400">{r.customer_id}</p></div> },
  { key: "phone", header: "Phone", render: (r) => r.phone_number || "—" },
  { key: "package", header: "Package", render: (r) => r.package_name || "—" },
  { key: "authentication", header: "Authentication", render: (r) => <AuthenticationBadge mode={r.authentication_mode} /> },
  { key: "status", header: "Account status", render: (r) => <StatusBadge status={r.customer_status} /> },
  { key: "balance", header: "Balance", align: "right", render: (r) => <span className={`whitespace-nowrap ${Number(r.balance) < 0 ? "text-rose-600" : ""}`}>{kes(r.balance)}</span> },
  { key: "billing", header: "Billing date", render: (r) => r.billing_date || "—" },
];
