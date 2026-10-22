import { Alert, Button, Select } from "flowbite-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { onuColumns } from "./onuColumns";
import { AdminResourceList } from "@/features/admin/AdminResourceList";
import { useAdminOptions } from "@/features/admin/useAdminOptions";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { Onu, OltDevice } from "@/shared/types/api";
export function OnusManager({oltId,onOltId}: {oltId?:string;onOltId?:(id:string)=>void}={}) {
 const [local,setLocal]=useState("");const olt=oltId??local;const setOlt=onOltId??setLocal;
 const options=useAdminOptions<OltDevice>("olt-devices",API.olt.devices);const qc=useQueryClient();
 const sync=useMutation({mutationFn:async(id:number)=>(await api.post<{ok:boolean;found:number;created:number;updated:number}>(API.olt.syncOnus(id))).data,onSettled:()=>{void qc.invalidateQueries({queryKey:["onus"]});void qc.invalidateQueries({queryKey:["olt-devices"]});}});
 return <div className="space-y-4"><p className="text-sm text-slate-500">Stored ONU inventory and last SNMP observations. Failed sync does not mean ONUs are offline. Manual create/edit/delete is unavailable pending safe tenant validation for OLT/customer assignments.</p>
 {options.isError && <Alert color="failure">OLT choices unavailable.</Alert>}
 {sync.isError && <Alert color="failure">SNMP sync failed or is unavailable. Stored observations may be stale.</Alert>}
 {sync.isSuccess && <Alert color={sync.data.ok?"success":"failure"}>{sync.data.ok?`SNMP sync completed: ${sync.data.found} ONUs, ${sync.data.created} new, ${sync.data.updated} updated.`:"SNMP sync failed; stored observations may be stale."}</Alert>}
 <AdminResourceList<Onu> queryKey="onus" url={API.olt.onus} columns={onuColumns} rowKey={r=>r.id} searchPlaceholder="Serial, name, ONU index or PON port" emptyTitle="No stored ONUs" emptyDescription="Select an OLT and run an explicit SNMP sync." params={{olt}} filters={<Select aria-label="OLT filter" value={olt} onChange={e=>setOlt(e.target.value)}><option value="">All OLTs</option>{options.data?.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</Select>} toolbarAction={olt?<Button disabled={sync.isPending} onClick={()=>{if(window.confirm("Refresh stored ONU observations from this OLT over SNMP?"))sync.mutate(Number(olt));}}>{sync.isPending?"Syncing…":"Sync SNMP observations"}</Button>:null} /></div>;
}
