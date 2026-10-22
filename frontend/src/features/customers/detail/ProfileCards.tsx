import { useState } from "react";
import { Button } from "flowbite-react";
import { DetailCard, InfoRow } from "./InfoRow";
import { ChangePasswordModal } from "./ChangePasswordModal";
import { ConnectionEditModal } from "./ConnectionEditModal";
import { AuthenticationBadge } from "../AuthenticationBadge";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import type { CustomerDetail } from "@/shared/types/api";
export function ProfileCards({ customer: c }: { customer: CustomerDetail }) {
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [connectionOpen, setConnectionOpen] = useState(false);
  const r = c.router_info;
  return <div className="grid min-w-0 gap-5 md:grid-cols-2">
    <DetailCard title="Profile"><InfoRow label="Customer ID">{c.customer_id}</InfoRow><InfoRow label="Name">{c.customer_name}</InfoRow><InfoRow label="Account status"><StatusBadge status={c.customer_status} /></InfoRow><InfoRow label="Primary phone">{c.phone_number}</InfoRow><InfoRow label="Alternate phone">{c.phone_number2 || "—"}</InfoRow><InfoRow label="National ID">{c.nid || "—"}</InfoRow><InfoRow label="Address">{c.address}</InfoRow><InfoRow label="Zone">{c.zone_name || "—"}</InfoRow></DetailCard>
    <DetailCard title="Connection"><InfoRow label="Authentication"><AuthenticationBadge mode={r?.authentication_mode} /></InfoRow>
      {r ? <><InfoRow label="PPPoE username"><span className="break-all font-mono text-xs">{r.pppoe_name}</span></InfoRow><InfoRow label="Router">{r.router_name || "Unconfigured"}</InfoRow><InfoRow label="Profile">{r.profile_name || "—"}</InfoRow><InfoRow label="Configured remote IP">{r.remote_ip || "—"}</InfoRow>
        <p className="mt-3 text-xs text-slate-500">Credentials are write-only. Authentication mode and username cannot be changed here. Stored remote IP is configuration metadata; live IP is shown separately.</p>
        <div className="mt-4 flex flex-wrap gap-2">{r.authentication_mode === "radius" || r.authentication_mode === "local_secret" ? <Button color="light" size="sm" onClick={() => setPasswordOpen(true)}>Change PPPoE password</Button> : null}{r.authentication_mode === "local_secret" ? <Button color="light" size="sm" onClick={() => setConnectionOpen(true)}>Edit profile</Button> : null}</div>
      </> : <p className="py-4 text-sm text-slate-500">No connection configured. Provisioning an existing profile requires a supported attach workflow.</p>}
    </DetailCard>
    {passwordOpen ? <ChangePasswordModal customerId={c.customer_id} onClose={() => setPasswordOpen(false)} /> : null}
    {connectionOpen ? <ConnectionEditModal customer={c} onClose={() => setConnectionOpen(false)} /> : null}
  </div>;
}
