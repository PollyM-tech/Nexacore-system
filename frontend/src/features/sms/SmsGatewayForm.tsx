import { Checkbox, Label, Select, TextInput } from "flowbite-react";
import { useEffect, useMemo, useState } from "react";
import { GatewayField } from "@/features/sms/GatewayField";
import { useSmsProviders } from "@/features/sms/useSmsProviders";
import { FormField } from "@/shared/components/ui/FormField";
import { FormModal } from "@/shared/components/ui/FormModal";
import type { SmsGateway } from "@/shared/types/api";

const JSON_KEYS = ["headers", "payload"];

type Props = {
  open: boolean; onClose: () => void; initial?: SmsGateway | null;
  onSubmit: (body: Record<string, unknown>) => void; submitting?: boolean; error?: string | null;
};

export function SmsGatewayForm({ open, onClose, initial, onSubmit, submitting, error }: Props) {
  const providerQuery = useSmsProviders();
  const providers = useMemo(() => providerQuery.data ?? [], [providerQuery.data]);
  const [replaceCredentials,setReplaceCredentials] = useState(false);
  const [senderId,setSenderId] = useState("");
  const [provider, setProvider] = useState("");
  const [label, setLabel] = useState("");
  const [isActive,setIsActive] = useState(true);
  const [isDefault, setIsDefault] = useState(true);
  const [creds, setCreds] = useState<Record<string, string>>({});
  const [jsonError, setJsonError] = useState<string | null>(null);

  const meta = useMemo(() => providers.find((p) => p.key === provider), [providers, provider]);

  useEffect(() => {
    if (!open) return;
    setProvider(initial?.provider ?? providers[0]?.key ?? "");
    setLabel(initial?.label ?? "");
    setIsDefault(initial?.is_default ?? true);
    setIsActive(initial?.is_active ?? true);
    setReplaceCredentials(!initial);
    setSenderId(initial?.sender_id ?? "");
    const c = {} as Record<string, unknown>;
    setCreds(Object.fromEntries(Object.entries(c).map(([k, v]) => [k, JSON_KEYS.includes(k) ? JSON.stringify(v, null, 2) : String(v ?? "")])));
    setJsonError(null);
  }, [open, initial, providers]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setJsonError(null);
    if (!meta) { setJsonError("Provider configuration unavailable. Choose a supported provider."); return; }
    const out: Record<string, unknown> = {};
    for (const f of meta?.fields ?? []) {
      const raw = creds[f.key] ?? "";
      if (JSON_KEYS.includes(f.key)) {
        try { const parsed = raw ? JSON.parse(raw) : {}; if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Object required"); out[f.key] = parsed; }
        catch { setJsonError(`Invalid JSON in "${f.label}"`); return; }
      } else if (raw !== "") out[f.key] = raw;
    }
    onSubmit({ provider, label: label || meta?.label || provider, ...(replaceCredentials ? {credentials: out} : {}), sender_id:senderId, is_default: isDefault, is_active: isActive });
  };

  return (
    <FormModal open={open} onClose={onClose} title={initial ? "Edit gateway" : "Add SMS gateway"}
      onSubmit={submit} submitting={submitting} submitDisabled={providerQuery.isLoading || providerQuery.isError} error={error ?? jsonError} submitLabel={initial ? "Save changes" : "Add gateway"}>
      {(providerQuery.isLoading || providerQuery.isError) && <p role="status" className="sm:col-span-2">{providerQuery.isError ? "Provider metadata unavailable. Close and retry." : "Loading provider fields…"}</p>}
      <FormField label="Provider" htmlFor="smsgatewayform-provider" required>
        <Select id="smsgatewayform-provider" value={provider} onChange={(e) => { setProvider(e.target.value); setCreds({}); }} disabled={!!initial}>
          {providers.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
        </Select>
      </FormField>
      <FormField label="Display name" htmlFor="smsgatewayform-display-name"><TextInput id="smsgatewayform-display-name" value={label} onChange={(e) => setLabel(e.target.value)} placeholder={meta?.label} /></FormField>
      <FormField label="Sender ID" htmlFor="gateway-sender"><TextInput id="gateway-sender" value={senderId} onChange={e=>setSenderId(e.target.value)} /></FormField>
      {initial && <div className="sm:col-span-2"><Checkbox id="gateway-replace" checked={replaceCredentials} onChange={e=>setReplaceCredentials(e.target.checked)} /><Label htmlFor="gateway-replace" className="ml-2">Replace provider credentials explicitly</Label><p className="text-xs text-slate-500">Existing credentials cannot be read. Replacement requires the complete provider configuration.</p></div>}
      {replaceCredentials && meta?.fields.map((f) => (
        <GatewayField key={f.key} field={f} value={creds[f.key] ?? ""} onChange={(v) => setCreds((p) => ({ ...p, [f.key]: v }))} />
      ))}
      <FormField label="Configuration" htmlFor="gateway-enabled"><Select id="gateway-enabled" value={String(isActive)} onChange={e=>setIsActive(e.target.value === "true")}><option value="true">Enabled</option><option value="false">Disabled</option></Select></FormField>
      <div className="flex items-center gap-2 sm:col-span-2">
        <Checkbox id="gw-default" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
        <Label htmlFor="gw-default">Use this gateway by default for sending</Label>
      </div>
    </FormModal>
  );
}
