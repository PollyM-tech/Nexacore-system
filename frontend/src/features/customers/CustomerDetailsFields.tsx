import { Select, TextInput } from "flowbite-react";
import { FormField } from "@/shared/components/ui/FormField";
import { kes } from "@/shared/utils/format";
import type { useCustomerForm } from "./useCustomerForm";
export function CustomerDetailsFields({ f, set, isEdit, options, radius }: ReturnType<typeof useCustomerForm>) {
  return <div className="grid gap-4 sm:grid-cols-2">
    {!isEdit ? <FormField label="Customer ID" htmlFor="customer-id"><TextInput id="customer-id" value={f.customer_id} maxLength={20} onChange={set("customer_id")} placeholder="Generated if left blank" /></FormField> : null}
    <FormField label="Customer name" required htmlFor="customer-name"><TextInput id="customer-name" required maxLength={255} value={f.customer_name} onChange={set("customer_name")} autoComplete="name" /></FormField>
    <FormField label="National ID" htmlFor="customer-nid"><TextInput id="customer-nid" maxLength={15} value={f.nid} onChange={set("nid")} /></FormField>
    <FormField label="Primary phone" required htmlFor="customer-phone"><TextInput id="customer-phone" type="tel" required maxLength={15} value={f.phone_number} onChange={set("phone_number")} autoComplete="tel" /></FormField>
    <FormField label="Alternate phone" htmlFor="customer-phone2"><TextInput id="customer-phone2" type="tel" maxLength={15} value={f.phone_number2} onChange={set("phone_number2")} /></FormField>
    <FormField label="Address" required full htmlFor="customer-address"><TextInput id="customer-address" required maxLength={255} value={f.address} onChange={set("address")} autoComplete="street-address" /></FormField>
    <FormField label="Zone" required htmlFor="customer-zone"><Select id="customer-zone" required value={f.zone} onChange={set("zone")}><option value="">Select zone</option>{options.zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}</Select></FormField>
    <FormField label="Package" required={radius} htmlFor="customer-package"><Select id="customer-package" required={radius} value={f.package} onChange={set("package")}>
      <option value="">{radius ? "Select an active package" : "No package"}</option>
      {options.packages.filter((p) => p.is_active || (isEdit && String(p.id) === f.package)).map((p) => <option key={p.id} value={p.id} disabled={!p.is_active && String(p.id) !== f.package}>{p.name} · {p.speed} · {kes(p.price)}{!p.is_active ? " (inactive)" : ""}</option>)}
    </Select>{radius && isEdit ? <p className="mt-2 text-xs text-slate-500">Package changes synchronize RADIUS. The new speed applies on next reauthentication / reconnect; the session is not disconnected automatically.</p> : isEdit ? <p className="mt-2 text-xs text-slate-500">For local secrets, assigning a package does not change the router profile automatically. Existing connection settings remain in place.</p> : null}</FormField>
    {!isEdit ? <FormField label="Billing day (1–28)" required htmlFor="customer-billing"><TextInput id="customer-billing" type="number" min={1} max={28} required value={f.billing_day} onChange={set("billing_day")} /><p className="mt-1 text-xs text-slate-500">First billing date is scheduled for next month.</p></FormField> : null}
  </div>;
}
