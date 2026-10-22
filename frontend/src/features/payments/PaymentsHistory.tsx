import { Select } from "flowbite-react";
import { useState } from "react";
import { paymentColumns } from "@/features/payments/paymentColumns";
import { API } from "@/shared/api/endpoints";
import { AdminResourceList as ResourceList } from "@/features/admin/AdminResourceList";
import type { Transaction } from "@/shared/types/api";

const METHODS = ["cash", "mpesa", "bank_transfer", "card", "adjustment", "other"];

export function PaymentsHistory() {
  const [method, setMethod] = useState("");
  return (
    <ResourceList<Transaction>
      queryKey="transactions" url={API.billing.transactions} columns={paymentColumns} rowKey={(r) => r.id}
      searchPlaceholder="Search payments…" emptyTitle="No payments yet"
      emptyDescription="Recorded payments and adjustments will appear here." emptyIcon="cash"
      params={{ payment_method: method }}
      filters={
        <Select aria-label="Payment method filter" sizing="sm" value={method} onChange={(e) => setMethod(e.target.value)} className="w-40">
          <option value="">All methods</option>
          {METHODS.map((m) => <option key={m} value={m} className="capitalize">{m === "mpesa" ? "M-Pesa" : m.replace(/_/g, " ")}</option>)}
        </Select>
      }
    />
  );
}
