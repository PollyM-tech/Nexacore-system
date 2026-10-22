import { CustomerLink } from "@/features/admin/CustomerLink";
import type { Column } from "@/shared/components/data/DataTable";
import type { Transaction } from "@/shared/types/api";
import { kes, dateTime } from "@/shared/utils/format";
export const paymentMethods: Record<string,string> = {cash:"Cash",mpesa:"M-Pesa",bank_transfer:"Bank transfer",card:"Card",adjustment:"Adjustment",other:"Other"};
export const paymentColumns: Column<Transaction>[] = [
  {key:"customer",header:"Customer",render:r=><CustomerLink customer={r.customer} name={r.customer_name} />},
  {key:"amount",header:"Ledger amount",align:"right",render:r=><span className="whitespace-nowrap font-semibold">{kes(r.amount)}</span>},
  {key:"method",header:"Method / entry",render:r=><div>{paymentMethods[r.payment_method] ?? r.payment_method}<p className="text-xs text-slate-500">{r.payment_method === "adjustment" ? "Ledger adjustment · not received income" : Number(r.amount)>0 ? "Received payment" : "Negative ledger entry"}</p></div>},
  {key:"ref",header:"Receipt / reference",render:r=>r.transaction_id || "—"},
  {key:"by",header:"Received by",render:r=>r.received_by_username || "—"},
  {key:"notes",header:"Notes",render:r=><span className="break-words">{r.notes || "—"}</span>},
  {key:"date",header:"Date / time",render:r=>dateTime(r.created_at)},
];
