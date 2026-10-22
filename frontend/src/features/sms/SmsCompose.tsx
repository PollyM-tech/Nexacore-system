import { Alert, Button } from "flowbite-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AudienceFields, type ComposeState } from "@/features/sms/AudienceFields";
import { MessageEditor } from "@/features/sms/MessageEditor";
import { VariableHelper } from "@/features/sms/VariableHelper";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { useAdminOptions as usePaginatedList } from "@/features/admin/useAdminOptions";
import { apiError } from "@/shared/utils/apiError";
import type { SmsGateway, SmsTemplate } from "@/shared/types/api";

const INIT: ComposeState = { audience: "single", mobile: "", customer_id: "", zone: "" };

export function SmsCompose() {
  const qc = useQueryClient();
  const { data: templates = [] } = usePaginatedList<SmsTemplate>("sms-templates", API.sms.templates);
  const gatewayQuery = usePaginatedList<SmsGateway>("sms-gateways", API.sms.gateways);
  const gateways = gatewayQuery.data ?? [];
  const [s, setS] = useState<ComposeState>(INIT);
  const [message, setMessage] = useState("");
  const update = (patch: Partial<ComposeState>) => setS((p) => ({ ...p, ...patch }));

  const mut = useMutation({
    mutationFn: () => api.post(API.sms.send, {
      audience: s.audience, message, mobile: s.mobile,
      customer_id: s.customer_id, zone: s.zone ? Number(s.zone) : undefined,
    }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sms-logs"] }),
  });

  const noGateway = !gateways.some(g=>g.is_active);
  const submit = (e: React.FormEvent) => { e.preventDefault(); if ((s.audience === "customer" && !s.customer_id) || (s.audience === "zone" && !s.zone)) return; if (["single","customer"].includes(s.audience) || window.confirm("Send this SMS to every customer in the selected audience? Provider charges may apply.")) mut.mutate(); };

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <form onSubmit={submit} className="card-surface space-y-4 p-5 sm:p-6 lg:col-span-2">
        {gatewayQuery.isLoading && <p>Loading SMS configuration…</p>}
        {gatewayQuery.isError && <Alert color="failure">SMS configuration unavailable. Sending is disabled.</Alert>}
        {!gatewayQuery.isLoading && !gatewayQuery.isError && noGateway ? <Alert color="warning">No SMS gateway configured yet. Add one in the <b>Gateways</b> tab first.</Alert> : null}
        {mut.isSuccess ? <Alert color="success">Provider processing: {mut.data.sent} accepted, {mut.data.failed} failed of {mut.data.total}. Handset delivery is not confirmed.</Alert> : null}
        {mut.isError ? <Alert color="failure">{apiError(mut.error)}</Alert> : null}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AudienceFields state={s} update={update} />
        </div>
        <MessageEditor message={message} onMessage={setMessage} templates={templates} showVars={false} />
        <div className="flex items-center justify-end gap-3">
          <Button color="primary" type="submit" disabled={mut.isPending || gatewayQuery.isLoading || gatewayQuery.isError || noGateway || !message.trim()}>
            {mut.isPending ? "Sending…" : "Send SMS"}
          </Button>
        </div>
      </form>
      <VariableHelper />
    </div>
  );
}
