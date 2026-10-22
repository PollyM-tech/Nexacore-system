import { Select, Textarea, TextInput } from "flowbite-react";
import { useEffect, useState } from "react";
import { FormField } from "@/shared/components/ui/FormField";
import { FormModal } from "@/shared/components/ui/FormModal";
import { API } from "@/shared/api/endpoints";
import { useAdminOptions as usePaginatedList } from "@/features/admin/useAdminOptions";

const EMPTY = { customer: "", title: "", priority: "medium", description: "" };

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (body: Record<string, unknown>) => void;
  submitting?: boolean;
  error?: string | null;
};

type CustomerOption = {
  id: number;
  customer_id: string;
  customer_name: string;
};

export function TicketForm({ open, onClose, onSubmit, submitting, error }: Props) {
  const [f, setF] = useState({ ...EMPTY });
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));
  const customers = usePaginatedList<CustomerOption>("customers", API.customers);

  useEffect(() => {
    if (open) setF({ ...EMPTY });
  }, [open]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      customer: Number(f.customer),
      title: f.title,
      priority: f.priority,
      description: f.description,
    });
  };

  return (
    <FormModal open={open} onClose={onClose} title="New ticket"
      onSubmit={submit} submitting={submitting} submitDisabled={customers.isLoading || customers.isError} error={error ?? (customers.isError ? "Customer choices unavailable. Close and retry." : null)} submitLabel="Create">
      <FormField label="Customer" htmlFor="ticketform-customer" required>
        <Select id="ticketform-customer" disabled={customers.isLoading || customers.isError} required value={f.customer} onChange={set("customer")}>
          <option value="">Select customer</option>
          {customers.data?.map((c) => (
            <option key={c.id} value={c.id}>{c.customer_name} · {c.customer_id}</option>
          ))}
        </Select>
      </FormField>
      <FormField label="Priority" htmlFor="ticketform-priority">
        <Select id="ticketform-priority" value={f.priority} onChange={set("priority")}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </Select>
      </FormField>
      <FormField label="Subject" htmlFor="ticketform-subject" required full>
        <TextInput id="ticketform-subject" required value={f.title} onChange={set("title")} placeholder="e.g. Frequent disconnection at night" />
      </FormField>
      <FormField label="Description" htmlFor="ticketform-description" required full>
        <Textarea id="ticketform-description" required rows={3} value={f.description} onChange={set("description")} placeholder="Describe the issue reported by the customer…" />
      </FormField>
    </FormModal>
  );
}
