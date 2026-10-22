import { Alert, Button } from "flowbite-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { OltDeviceForm } from "./OltDeviceForm";
import { AdminResourceList } from "@/features/admin/AdminResourceList";
import { useAdminCrud } from "@/features/admin/useAdminCrud";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { Column } from "@/shared/components/data/DataTable";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { dateTime } from "@/shared/utils/format";
import { apiError } from "@/shared/utils/apiError";
import type { OltDevice } from "@/shared/types/api";
export function OltDevicesManager({onViewOnus}: {onViewOnus?:(olt:OltDevice)=>void}) {
 const [form,setForm]=useState<OltDevice | "new" | null>(null);const {create,update}=useAdminCrud("olt-devices",API.olt.devices);const qc=useQueryClient();const [result,setResult]=useState<{ok:boolean;text:string}|null>(null);
 const test=useMutation({mutationFn:async(id:number)=>(await api.post<{status:string}>(API.olt.testConnection(id))).data,onSuccess:d=>setResult({ok:d.status==="online",text:d.status==="online"?"SNMP connection succeeded.":"SNMP connection failed. Check connectivity and configuration."}),onError:()=>setResult({ok:false,text:"SNMP test unavailable or failed. Check connectivity and permissions."}),onSettled:()=>qc.invalidateQueries({queryKey:["olt-devices"]})});
 const close=()=>{setForm(null);create.reset();update.reset();};
 const columns:Column<OltDevice>[]=[
 {key:"name",header:"OLT",render:r=><div>{r.name}<p className="text-xs">{r.host} · {r.olt_type}</p></div>},
 {key:"enabled",header:"Configuration",render:r=>r.is_active?"Enabled":"Disabled"},
 {key:"status",header:"Stored SNMP status",render:r=><StatusBadge status={r.status || "unknown"} />},
 {key:"checked",header:"Last checked",render:r=>dateTime(r.last_checked)},
 {key:"count",header:"Stored ONUs",render:r=>r.onu_count ?? "Unavailable"},
 {key:"actions",header:"Actions",render:r=><div className="flex gap-2"><Button size="xs" color="light" onClick={()=>{create.reset();update.reset();setForm(r);}}>Edit</Button><Button size="xs" color="light" disabled={test.isPending} onClick={()=>{setResult(null);test.mutate(r.id);}}>{test.isPending && test.variables===r.id?"Testing…":"Test SNMP"}</Button><Button size="xs" color="light" onClick={()=>onViewOnus?.(r)}>ONUs</Button></div>},
 ];
 return <div className="space-y-4"><p className="text-sm text-slate-500">Stored inventory and last SNMP check, not continuously live telemetry. Device deletion is hidden to protect stored ONUs.</p>{result && <Alert color={result.ok?"success":"failure"}>{result.text}</Alert>}<AdminResourceList queryKey="olt-devices" url={API.olt.devices} columns={columns} rowKey={r=>r.id} searchPlaceholder="Search OLT name or host" emptyTitle="No OLT devices" emptyDescription="Register an OLT to read SNMP inventory." toolbarAction={<Button onClick={()=>{create.reset();update.reset();setForm("new");}}>Add OLT</Button>} />
 {form!==null && <OltDeviceForm open initial={form==="new"?null:form} onClose={()=>{if(!create.isPending&&!update.isPending)close();}} submitting={create.isPending||update.isPending} error={create.isError||update.isError?apiError(create.error??update.error):null} onSubmit={body=>form==="new"?create.mutate(body,{onSuccess:close}):update.mutate({id:form.id,body},{onSuccess:close})} />}</div>;
}
