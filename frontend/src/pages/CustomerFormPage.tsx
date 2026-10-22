import { useState } from "react";
import { Alert, Button } from "flowbite-react";
import { AuthenticationBadge } from "@/features/customers/AuthenticationBadge";
import { CustomerDetailsFields } from "@/features/customers/CustomerDetailsFields";
import { ConnectionFields } from "@/features/customers/ConnectionFields";
import { useCustomerForm } from "@/features/customers/useCustomerForm";
import { PageHeader } from "@/shared/components/layout/PageHeader";

export function CustomerFormPage() {
  const form = useCustomerForm();
  const [copyMessage, setCopyMessage] = useState("");
  if (form.detailLoading) return <p role="status" className="py-12 text-center">Loading customer…</p>;
  if (form.detailError) return <Alert color="failure">Customer could not be loaded. Check access or connectivity. <button type="button" className="underline" onClick={form.retryDetail}>Retry</button></Alert>;
  if (form.created) return <section className="card-surface mx-auto max-w-2xl space-y-5 p-6" role="status">
    <h1 className="text-2xl font-semibold">Customer created</h1><AuthenticationBadge mode={form.created.mode} /><p>Customer ID: <strong>{form.created.id}</strong></p>
    {form.created.username ? <><p>PPPoE username</p><p className="break-all rounded-xl bg-slate-50 p-4 font-mono dark:bg-ink-800">{form.created.username}</p>
      <p className="text-sm text-slate-500">The PPPoE password is the value you entered. It is not returned by the server and cannot be retrieved from this screen.</p>
      <Button color="light" onClick={async () => { try { await navigator.clipboard.writeText(form.created!.username!); setCopyMessage("Username copied."); } catch { setCopyMessage("Copy unavailable. Select the username above to copy it."); } }}>Copy username</Button><p className="text-sm">{copyMessage}</p></> : <p>No connection was provisioned.</p>}
    <Button color="primary" onClick={form.finish}>Open customer</Button>
  </section>;
  return <div className="space-y-5">
    <PageHeader title={form.isEdit ? "Edit customer" : "Add customer"} description={form.isEdit ? "Update profile and subscription without changing credentials." : "Create the subscriber profile and provision the connection."} />
    <form className="mx-auto max-w-4xl space-y-5" onSubmit={(e) => { void form.submit(e); }}>
      {form.error ? <Alert color="failure">{form.error}</Alert> : null}
      {form.options.isError ? <Alert color="failure">Customer options could not be loaded. <button type="button" className="underline" onClick={form.options.retry}>Retry</button></Alert> : null}
      {form.options.isLoading ? <p role="status">Loading zones, packages and routers…</p> : null}
      <fieldset disabled={form.submitting || form.options.isLoading || form.options.isError} className="card-surface space-y-5 p-5 sm:p-6">
        <legend className="sr-only">Customer profile</legend><h2 className="font-semibold">Customer</h2><CustomerDetailsFields {...form} />
      </fieldset>
      {!form.isEdit ? <fieldset disabled={form.submitting || form.options.isLoading || form.options.isError} className="card-surface space-y-5 p-5 sm:p-6"><legend className="sr-only">Connection settings</legend><h2 className="font-semibold">Connection</h2><ConnectionFields {...form} /></fieldset> : null}
      <div className="flex flex-wrap justify-end gap-3"><Button type="button" color="light" onClick={form.cancel} disabled={form.submitting}>Cancel</Button><Button type="submit" color="primary" disabled={form.submitting || form.options.isLoading || form.options.isError}>{form.submitting ? "Saving…" : form.isEdit ? "Save customer" : "Create customer"}</Button></div>
    </form>
  </div>;
}
