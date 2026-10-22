import { Alert, Button } from "flowbite-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { routerColumns } from "./routerColumns";
import { RouterForm } from "./RouterForm";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { Column } from "@/shared/components/data/DataTable";
import { AdminResourceList } from "@/features/admin/AdminResourceList";
import { useAdminCrud } from "@/features/admin/useAdminCrud";
import { apiError } from "@/shared/utils/apiError";
import type { Router } from "@/shared/types/api";
export function RoutersManager() {
  const [form, setForm] = useState<Router | "new" | null>(null);
  const { create, update } = useAdminCrud("routers", API.routers);
  const qc = useQueryClient();
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const test = useMutation({
    mutationFn: async (router: Router) => (await api.post<{status: string}>(`${API.routers}${router.id}/test_connection/`)).data,
    onSuccess: (data, router) => setResult({ ok: data.status === "success", message: `${router.name}: ${data.status === "success" ? "API connection succeeded." : "API connection failed. Check router configuration and connectivity."}` }),
    onError: (_, router) => setResult({ ok: false, message: `${router.name}: connection test failed. Check router connectivity or your permissions.` }),
    onSettled: () => { void qc.invalidateQueries({queryKey:["routers"]}); void qc.invalidateQueries({queryKey:["dashboard-summary"]}); },
  });
  const pending = create.isPending || update.isPending;
  const close = () => { if (!pending) { setForm(null); create.reset(); update.reset(); } };
  const columns: Column<Router>[] = [...routerColumns, { key:"actions", header:"Actions", render:r => <div className="flex flex-wrap gap-2 min-w-48"><Button size="xs" color="light" disabled={test.isPending || r.use_ssl} title={r.use_ssl ? "TLS tests unavailable: backend does not apply the stored SSL flag." : undefined} onClick={() => { setResult(null); test.mutate(r); }}>{test.isPending && test.variables?.id === r.id ? "Testing…" : "Test connection"}</Button><Button size="xs" color="light" onClick={() => { create.reset(); update.reset(); setForm(r); }}>Edit</Button><Link className="text-sm text-brand-600 underline" to={`/admin/bandwidth/live?router=${r.id}`}>Sessions</Link></div> }];
  return <div className="space-y-4">
    <p className="text-sm text-slate-500">Enabled is configuration state. Connection status is the last stored test result. Tests run only when requested. Router deletion is unavailable until assigned connections are protected. TLS-only setup/testing is unavailable because the backend ignores the stored SSL flag.</p>
    {result && <Alert color={result.ok ? "success" : "failure"}>{result.message}</Alert>}
    <AdminResourceList queryKey="routers" url={API.routers} columns={columns} rowKey={r=>r.id} emptyTitle="No routers" emptyDescription="Add a MikroTik API connection." emptyIcon="router" toolbarAction={<Button color="primary" onClick={()=>{create.reset();update.reset();setForm("new");}}>Add router</Button>} />
    {form !== null && <RouterForm open initial={form === "new" ? null : form} onClose={close} submitting={pending} error={create.isError || update.isError ? apiError(create.error ?? update.error) : null} onSubmit={body => form === "new" ? create.mutate(body,{onSuccess:close}) : update.mutate({id:form.id,body},{onSuccess:close})} />}
  </div>;
}
