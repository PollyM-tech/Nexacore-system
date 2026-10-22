import { Select, Textarea, TextInput } from "flowbite-react";
import { useEffect, useState } from "react";
import { Icon } from "@/shared/components/icons/Icon";
import { FormField } from "@/shared/components/ui/FormField";
import { FormModal } from "@/shared/components/ui/FormModal";
import type { Router } from "@/shared/types/api";

const EMPTY = { name: "", host: "", port: "8728", username: "", password: "", use_ssl: "false", description: "", is_active: "true" };

type Props = {
  open: boolean;
  onClose: () => void;
  initial?: Router | null;
  onSubmit: (body: Record<string, unknown>) => void;
  submitting?: boolean;
  error?: string | null;
};

export function RouterForm({ open, onClose, initial, onSubmit, submitting, error }: Props) {
  const [f, setF] = useState({ ...EMPTY });
  const [showPass, setShowPass] = useState(false);
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));

  useEffect(() => {
    if (!open) return;
    setShowPass(false);
    setF(
      initial
        ? {
            ...EMPTY, name: initial.name, host: initial.host, port: String(initial.port ?? 8728),
            username: initial.username ?? "", password: "", use_ssl: String(initial.use_ssl ?? false),
            description: initial.description ?? "", is_active: String(initial.is_active),
          }
        : { ...EMPTY },
    );
  }, [open, initial]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const body: Record<string, unknown> = {
      name: f.name, host: f.host, port: Number(f.port), username: f.username,
      use_ssl: f.use_ssl === "true", description: f.description, is_active: f.is_active === "true",
    };
    if (!initial || f.password) body.password = f.password;
    onSubmit(body);
  };

  return (
    <FormModal open={open} onClose={onClose} title={initial ? "Edit router" : "New router"}
      onSubmit={submit} submitting={submitting} error={error} submitLabel={initial ? "Save changes" : "Create"}>
      <FormField label="Router name" htmlFor="routerform-router-name" required><TextInput id="routerform-router-name" required value={f.name} onChange={set("name")} placeholder="e.g. Core-Router-1" /></FormField>
      <FormField label="Host / IP" htmlFor="routerform-host-ip" required><TextInput id="routerform-host-ip" required value={f.host} onChange={set("host")} placeholder="192.168.88.1" /></FormField>
      <FormField label="API port" htmlFor="routerform-api-port"><TextInput id="routerform-api-port" type="number" min={1} max={65535} required value={f.port} onChange={set("port")} /></FormField>
      <FormField label="Use SSL" htmlFor="routerform-use-ssl">
        <Select id="routerform-use-ssl" disabled={!!initial?.use_ssl} value={f.use_ssl} onChange={set("use_ssl")}>
          <option value="false">No</option>
          <option value="true" disabled>Yes · backend TLS support required</option>
        </Select>
        <p className="mt-1 text-xs text-slate-500">TLS configuration is unavailable: the backend currently ignores the stored SSL flag. Existing SSL settings are preserved; connection testing is disabled for them.</p>
      </FormField>
      <FormField label="API username" htmlFor="routerform-api-username" required><TextInput id="routerform-api-username" required value={f.username} onChange={set("username")} /></FormField>
      <FormField label="API password" htmlFor="routerform-api-password" required={!initial}>
        <TextInput id="routerform-api-password" type={showPass ? "text" : "password"} required={!initial} value={f.password} onChange={set("password")}
          placeholder={initial ? "Leave blank to keep current" : ""}
          rightIcon={() => (
            <button type="button" aria-label={showPass ? "Hide password" : "Show password"} onClick={() => setShowPass((s) => !s)} className="pointer-events-auto text-slate-400 hover:text-slate-600">
              <Icon name={showPass ? "eyeOff" : "eye"} className="h-4 w-4" />
            </button>
          )} />
      </FormField>
      <FormField label="Status" htmlFor="routerform-status">
        <Select id="routerform-status" value={f.is_active} onChange={set("is_active")}>
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </Select>
      </FormField>
      <FormField label="Description" htmlFor="routerform-description" full><Textarea id="routerform-description" rows={2} value={f.description} onChange={set("description")} /></FormField>
    </FormModal>
  );
}
