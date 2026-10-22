import { Button, Modal, ModalBody, ModalHeader, Select, Textarea, TextInput } from "flowbite-react";
import { useState } from "react";
import { FormField } from "@/shared/components/ui/FormField";
import { FormModal } from "@/shared/components/ui/FormModal";
import type { Package } from "@/shared/types/api";
import { billingCycles, knownCount } from "./packageColumns";
import { usePackageDetail } from "./usePackages";
import { apiError } from "@/shared/utils/apiError";

type Props = {
  open: boolean; onClose: () => void; initial?: Package | null;
  onSubmit: (body: Record<string, unknown>) => void;
  submitting?: boolean; error?: string | null;
};
// Positive scalar K/M/G units, with optional bps suffix; canonical directional
// values such as 10M/20M are also accepted by the RADIUS converter.
export function validPackageSpeed(speed: string) {
  const compact = speed.toUpperCase().replace(/ /g, "").replace(/([KMG])BPS/g, "$1");
  return /^\d+(?:\.\d+)?[KMG](?:\/\d+(?:\.\d+)?[KMG])?$/.test(compact)
    && compact.split("/").every((part) => Number.parseFloat(part) > 0)
    && (!speed.includes("/") || /^\d+(?:\.\d+)?[KMG]\/\d+(?:\.\d+)?[KMG]$/.test(speed));
}
export function PackageForm(props: Props) {
  const detail = usePackageDetail(props.initial?.id);
  if (!props.open) return null;
  if (props.initial && (detail.isPending || detail.isFetching || detail.isError)) {
    return <Modal show onClose={props.onClose} size="lg"><ModalHeader>Edit package</ModalHeader><ModalBody>
      <p role="status">{detail.isError ? apiError(detail.error, "Could not verify package usage. Editing is unavailable.") : "Loading current package and usage…"}</p>
      <div className="mt-4 flex gap-3">{detail.isError && <Button color="light" type="button" onClick={() => void detail.refetch()}>Retry package</Button>}<Button color="light" onClick={props.onClose}>Close</Button></div>
    </ModalBody></Modal>;
  }
  return <PackageFields {...props} initial={props.initial ? detail.data : null} />;
}
function PackageFields({ open, onClose, initial, onSubmit, submitting, error }: Props) {
  const [f, setF] = useState(() => ({ name: initial?.name ?? "", package_type: initial?.package_type ?? "monthly", speed: initial?.speed ?? "", price: initial?.price ?? "", description: initial?.description ?? "", is_active: String(initial?.is_active ?? true) }));
  const [validation, setValidation] = useState<string | null>(null);
  const set = (key: keyof typeof f) => (e: { target: { value: string } }) => setF((prev) => ({ ...prev, [key]: e.target.value }));
  const locked = !!initial && (!knownCount(initial.radius_customer_count) || initial.radius_customer_count > 0);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!f.name.trim()) { setValidation("Name: enter a package name."); return; }
    if (!(f.package_type in billingCycles)) { setValidation("Billing cycle: choose Monthly, Quarterly or Yearly."); return; }
    if ((!initial || f.speed !== initial.speed) && !locked && !validPackageSpeed(f.speed.trim())) { setValidation("Speed: use a positive value such as 10 Mbps, 512Kbps, 20M or 10M/20M."); return; }
    if (!/^\d+(?:\.\d{1,2})?$/.test(f.price) || Number(f.price) <= 0 || Number(f.price) > 99999999.99) { setValidation("Price: enter a positive KES amount with up to two decimal places (maximum 99,999,999.99)."); return; }
    const body: Record<string, unknown> = { name: f.name.trim(), package_type: f.package_type, price: f.price, description: f.description, is_active: f.is_active === "true" };
    if (!locked) body.speed = f.speed.trim();
    if (initial) for (const key of Object.keys(body)) if (body[key] === initial[key as keyof Package]) delete body[key];
    setValidation(null);
    onSubmit(body);
  };
  return <FormModal open={open} onClose={onClose} title={initial ? `Edit ${initial.name}` : "New package"} onSubmit={submit} submitting={submitting} error={validation ?? error} submitLabel={initial ? "Save changes" : "Create package"}>
    <FormField label="Package name" htmlFor="pkg-name" required><TextInput id="pkg-name" required maxLength={100} value={f.name} onChange={set("name")} /></FormField>
    <FormField label="Billing cycle" htmlFor="pkg-cycle" required><Select id="pkg-cycle" value={f.package_type} onChange={set("package_type")}>{Object.entries(billingCycles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></FormField>
    <FormField label="Speed" htmlFor="pkg-speed" required><TextInput id="pkg-speed" required disabled={locked} maxLength={50} value={f.speed} onChange={set("speed")} placeholder="10 Mbps" aria-describedby="pkg-speed-help" /><p id="pkg-speed-help" className="mt-1 text-xs text-slate-500">{locked ? knownCount(initial?.radius_customer_count) ? "This package is assigned to RADIUS customers. Move those customers to another package before changing the speed." : "Usage unavailable. Speed editing is disabled." : "Examples: 10 Mbps, 512Kbps, 20M or 10M/20M."}</p></FormField>
    <FormField label="Price (KES)" htmlFor="pkg-price" required><TextInput id="pkg-price" type="number" min="0.01" max="99999999.99" step="0.01" required value={f.price} onChange={set("price")} /><p className="mt-1 text-xs text-slate-500">Future bills use the current price. Existing historical invoices are not rewritten.</p></FormField>
    <FormField label="Status" htmlFor="pkg-status"><Select id="pkg-status" value={f.is_active} onChange={set("is_active")}><option value="true">Active</option><option value="false">Inactive</option></Select><p className="mt-1 text-xs text-slate-500">Existing customers remain assigned when deactivated; active subscribers are not disconnected.</p></FormField>
    <FormField label="Description" htmlFor="pkg-description" full><Textarea id="pkg-description" rows={3} value={f.description} onChange={set("description")} /></FormField>
  </FormModal>;
}
