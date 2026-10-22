import { Select, TextInput } from "flowbite-react";
import { FormField } from "@/shared/components/ui/FormField";
import { PasswordInput } from "./PasswordInput";
import type { useCustomerForm } from "./useCustomerForm";
export function ConnectionFields({ f, set, setPassword, radius, options, profiles, profilesLoading, profilesError }: ReturnType<typeof useCustomerForm>) {
  return <div className="grid gap-4 sm:grid-cols-2">
    <FormField label="Authentication mode" htmlFor="connection-mode"><Select id="connection-mode" value={f.authentication_mode} onChange={(e) => { set("authentication_mode")(e); setPassword(""); }}><option value="radius">RADIUS</option><option value="local_secret">Local secret</option></Select></FormField>
    <FormField label="Router" required={radius} htmlFor="connection-router"><Select id="connection-router" required={radius} value={f.router} onChange={set("router")}><option value="">{radius ? "Select router" : "No router — profile only"}</option>{options.routers.filter((r) => r.is_active).map((r) => <option key={r.id} value={r.id}>{r.name} · {r.host}</option>)}</Select></FormField>
    {radius ? <p className="text-sm text-slate-500 sm:col-span-2">Lintech generates the PPPoE username automatically. The package controls the RADIUS rate limit. Enter the password chosen by the customer.</p> : null}
    {!radius && f.router ? <>
      <FormField label="PPPoE username" required htmlFor="connection-username"><TextInput id="connection-username" required value={f.pppoe_name} maxLength={255} onChange={set("pppoe_name")} autoComplete="off" /></FormField>
      <FormField label="MikroTik profile" htmlFor="connection-profile">
        {profiles.length ? <Select id="connection-profile" value={f.profile_name} onChange={set("profile_name")}><option value="">Package name / default</option>{profiles.map((p) => <option key={p} value={p}>{p}</option>)}</Select>
          : <TextInput id="connection-profile" value={f.profile_name} onChange={set("profile_name")} placeholder={profilesLoading ? "Loading profiles…" : "Package name / default"} />}
        {profilesError ? <p className="mt-1 text-xs text-amber-600">Profile lookup unavailable. Enter the existing router profile name if known.</p> : null}
      </FormField>
    </> : null}
    {radius || f.router ? <PasswordInput key={f.authentication_mode} id="create-pppoe-password" label="PPPoE password" value={f.pppoe_pass} onChange={setPassword} /> : <p className="text-sm text-slate-500 sm:col-span-2">This creates a customer profile without provisioning a connection. Attaching a connection later requires a separate supported workflow.</p>}
  </div>;
}
