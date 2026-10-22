import { Button } from "flowbite-react";
import { useState } from "react";
import { BillingSettingsModal } from "./BillingSettingsModal";
import { DetailCard, InfoRow } from "./InfoRow";
import { useCustomerOptions } from "../useCustomerOptions";
import { kes } from "@/shared/utils/format";
import type { CustomerDetail } from "@/shared/types/api";
export function BillingPanel({ customer: c }: { customer: CustomerDetail }) {
  const [open, setOpen] = useState(false);
  const options = useCustomerOptions();
  const pkg = options.packages.find((p) => p.id === c.package);
  const s = c.billing_summary;
  return <DetailCard title="Subscription and billing">
    <InfoRow label="Package">{c.package_name || "Unassigned"}</InfoRow><InfoRow label="Package price">{c.package_price ? kes(c.package_price) : "—"}</InfoRow><InfoRow label="Package speed">{pkg?.speed || (options.isLoading ? "Loading…" : "Unavailable")}</InfoRow>
    <InfoRow label="Billing date">{c.billing_date || "—"}</InfoRow><InfoRow label="Extended / grace days">{c.extended_billing_days ?? 0}</InfoRow>
    <InfoRow label="Account balance"><span className={Number(c.balance) < 0 ? "text-rose-600" : ""}>{kes(c.balance)}</span></InfoRow>
    <p className="my-2 text-xs text-slate-500">Negative balance indicates money due; positive balance is account credit.</p>
    {s ? <><InfoRow label="Total billed">{kes(s.total_billed)}</InfoRow><InfoRow label="Allocated to invoices">{kes(s.total_paid)}</InfoRow><InfoRow label="Invoice outstanding">{kes(s.pending_amount)}</InfoRow></> : null}
    {c.router_info?.authentication_mode === "radius" ? <p className="mt-3 text-xs text-slate-500">Package changes apply to the RADIUS rate limit on the next reauthentication. Use Edit customer to change the package.</p> : null}
    <Button color="light" size="sm" className="mt-4" onClick={() => setOpen(true)}>Change billing schedule</Button>
    {open ? <BillingSettingsModal open onClose={() => setOpen(false)} customer={c} /> : null}
  </DetailCard>;
}
