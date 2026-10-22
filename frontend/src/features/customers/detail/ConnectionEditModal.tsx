import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { TextInput } from "flowbite-react";
import { FormModal } from "@/shared/components/ui/FormModal";
import { FormField } from "@/shared/components/ui/FormField";
import { API } from "@/shared/api/endpoints";
import { api } from "@/shared/api/client";
import { invalidateCustomer } from "../customerQueryKeys";
import type { CustomerDetail } from "@/shared/types/api";

export function ConnectionEditModal({ onClose, customer }: { onClose: () => void; customer: CustomerDetail }) {
  const [profile, setProfile] = useState(customer.router_info?.profile_name ?? "");
  const [warning, setWarning] = useState("");
  const client = useQueryClient();
  const mutation = useMutation({ mutationFn: async () => (await api.post<{ warning?: string }>(API.customerConnection(customer.customer_id), { profile_name: profile })).data,
    onSuccess: (data) => { void invalidateCustomer(client, customer.customer_id); if (data.warning) setWarning("Saved locally, but router synchronization failed. Verify the existing router profile before retrying."); else onClose(); },
  });
  return <FormModal open onClose={onClose} title="Local connection profile" submitting={mutation.isPending}
    onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }} error={mutation.isError ? "Connection update failed. Check your permissions and profile name." : warning || null}>
    <p className="text-sm text-slate-500 sm:col-span-2">Username and router are read-only. Renaming or moving a MikroTik secret is not supported by this workflow. Change the password using the separate password action.</p>
    <FormField label="Username" htmlFor="edit-connection-name"><TextInput id="edit-connection-name" readOnly value={customer.router_info?.pppoe_name || ""} /></FormField>
    <FormField label="Router" htmlFor="edit-connection-router"><TextInput id="edit-connection-router" readOnly value={customer.router_info?.router_name || "Unconfigured"} /></FormField>
    <FormField label="Existing MikroTik profile name" htmlFor="edit-connection-profile" full><TextInput id="edit-connection-profile" required maxLength={100} value={profile} onChange={(e) => setProfile(e.target.value)} /></FormField>
  </FormModal>;
}
