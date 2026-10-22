import { Select, TextInput } from "flowbite-react";
import { useEffect, useState } from "react";
import { API } from "@/shared/api/endpoints";
import { FormField } from "@/shared/components/ui/FormField";
import { FormModal } from "@/shared/components/ui/FormModal";
import { useAdminOptions as usePaginatedList } from "@/features/admin/useAdminOptions";
import type { Customer, OltDevice, Onu } from "@/shared/types/api";

const EMPTY = {
  olt: "", onu_index: "", serial_number: "", name: "", pon_port: "", onu_model: "",
  status: "unknown", rx_power: "", customer: "", description: "",
};

type Props = {
  open: boolean; onClose: () => void; initial?: Onu | null;
  onSubmit: (body: Record<string, unknown>) => void; submitting?: boolean; error?: string | null;
};

export function OnuForm({ open, onClose, initial, onSubmit, submitting, error }: Props) {
  const { data: olts = [] } = usePaginatedList<OltDevice>("olt-devices", API.olt.devices);
  const { data: customers = [] } = usePaginatedList<Customer>("customers", API.customers);
  const [f, setF] = useState({ ...EMPTY });
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));

  useEffect(() => {
    if (!open) return;
    setF(initial ? {
      ...EMPTY, olt: String(initial.olt), onu_index: initial.onu_index, serial_number: initial.serial_number,
      name: initial.name, pon_port: initial.pon_port, onu_model: initial.onu_model, status: initial.status,
      rx_power: initial.rx_power ?? "", customer: initial.customer ? String(initial.customer) : "", description: initial.description ?? "",
    } : { ...EMPTY, olt: olts[0] ? String(olts[0].id) : "" });
  }, [open, initial, olts]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      olt: Number(f.olt), onu_index: f.onu_index, serial_number: f.serial_number, name: f.name,
      pon_port: f.pon_port, onu_model: f.onu_model, status: f.status,
      rx_power: f.rx_power === "" ? null : Number(f.rx_power),
      customer: f.customer ? Number(f.customer) : null, description: f.description,
    });
  };

  return (
    <FormModal open={open} onClose={onClose} title={initial ? "Edit ONU" : "Add ONU"}
      onSubmit={submit} submitting={submitting} error={error} submitLabel={initial ? "Save changes" : "Add ONU"}>
      <FormField label="OLT" htmlFor="onuform-olt" required>
        <Select id="onuform-olt" required value={f.olt} onChange={set("olt")}>
          <option value="">Select OLT…</option>
          {olts.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </Select>
      </FormField>
      <FormField label="Serial number" htmlFor="onuform-serial-number"><TextInput id="onuform-serial-number" value={f.serial_number} onChange={set("serial_number")} placeholder="HWTC12345678" /></FormField>
      <FormField label="ONU index / id" htmlFor="onuform-onu-index-id" required><TextInput id="onuform-onu-index-id" required value={f.onu_index} onChange={set("onu_index")} placeholder="e.g. 0/1/1:1" /></FormField>
      <FormField label="PON port" htmlFor="onuform-pon-port"><TextInput id="onuform-pon-port" value={f.pon_port} onChange={set("pon_port")} placeholder="0/1/1" /></FormField>
      <FormField label="Name / label" htmlFor="onuform-name-label"><TextInput id="onuform-name-label" value={f.name} onChange={set("name")} /></FormField>
      <FormField label="ONU model" htmlFor="onuform-onu-model"><TextInput id="onuform-onu-model" value={f.onu_model} onChange={set("onu_model")} /></FormField>
      <FormField label="Stored status (manual)" htmlFor="onuform-status">
        <Select id="onuform-status" value={f.status} onChange={set("status")}>
          <option value="online">Online</option><option value="offline">Offline</option>
          <option value="los">Loss of signal</option><option value="unknown">Unknown</option>
        </Select>
      </FormField>
      <FormField label="Stored Rx power (dBm, manual)" htmlFor="onuform-rx-power-dbm"><TextInput id="onuform-rx-power-dbm" type="number" step="0.01" value={f.rx_power} onChange={set("rx_power")} placeholder="-21.50" /></FormField>
      <FormField label="Customer" htmlFor="onuform-customer" full>
        <Select id="onuform-customer" value={f.customer} onChange={set("customer")}>
          <option value="">Unassigned</option>
          {customers.map((c) => <option key={c.id} value={c.id}>{c.customer_name} · {c.customer_id}</option>)}
        </Select>
      </FormField>
    </FormModal>
  );
}
