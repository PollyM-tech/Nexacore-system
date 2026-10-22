import { useNavigate } from "react-router-dom";
import { Select, TextInput } from "flowbite-react";
import { useState } from "react";
import { FormModal } from "@/shared/components/ui/FormModal";
import { FormField } from "@/shared/components/ui/FormField";
import { useOrganizationMutation } from "./queries";
import { platformError } from "./PlatformFeedback";
import type { Organization } from "./types";
export function OrganizationForm({initial,onClose}:{initial?:Organization;onClose:()=>void}) {
 const [f,setF]=useState({name:initial?.name??"",slug:initial?.slug??"",organization_type:initial?.organization_type??"hybrid",status:initial?.status??"active",email:initial?.email??"",phone_number:initial?.phone_number??""});
 const mutation=useOrganizationMutation();const navigate=useNavigate();
 const set=(key:keyof typeof f)=>(e:{target:{value:string}})=>setF(p=>({...p,[key]:e.target.value}));
 return <FormModal open title={initial?`Edit ${initial.name}`:"Create ISP organization"} onClose={onClose} submitting={mutation.isPending} error={mutation.isError?platformError(mutation.error):null} submitLabel={initial?"Save organization":"Create organization"} onSubmit={e=>{
 e.preventDefault();if(!f.name.trim()||!f.slug.trim())return;
 if(f.status!=="active"&&(!initial||f.status!==initial.status)&&!window.confirm(`${f.status === "suspended" ? "Suspend" : "Deactivate"} this organization? Tenant data is retained. This blocks organization access but does not disconnect PPPoE sessions.`))return;
 const body:Record<string,unknown>={...f,name:f.name.trim(),slug:f.slug.trim()};if(initial)for(const key of Object.keys(body))if(body[key]===initial[key as keyof Organization])delete body[key];
 mutation.mutate({id:initial?.id,body},{onSuccess:org=>{onClose();if(!initial)navigate(`/superadmin/organizations/${org.id}`);}});
 }}>
 <FormField label="Organization name" htmlFor="org-name" required><TextInput id="org-name" required maxLength={255} value={f.name} onChange={set("name")} /></FormField>
 <FormField label="Slug" htmlFor="org-slug" required><TextInput id="org-slug" required maxLength={100} pattern="[-a-zA-Z0-9_]+" value={f.slug} onChange={set("slug")} /></FormField>
 <FormField label="ISP technology" htmlFor="org-type"><Select id="org-type" value={f.organization_type} onChange={set("organization_type")}><option value="hybrid">Hotspot + PPPoE</option><option value="pppoe">PPPoE</option><option value="hotspot">Hotspot</option></Select></FormField>
 <FormField label="Status" htmlFor="org-status"><Select id="org-status" value={f.status} onChange={set("status")}><option value="active">Active</option><option value="suspended">Suspended</option><option value="inactive">Inactive</option></Select><p className="mt-1 text-xs text-slate-500">Active enables the organization. Suspended/inactive disables access without deleting tenant data.</p></FormField>
 <FormField label="Contact email" htmlFor="org-email"><TextInput id="org-email" type="email" value={f.email} onChange={set("email")} /></FormField>
 <FormField label="Contact phone" htmlFor="org-phone"><TextInput id="org-phone" maxLength={20} value={f.phone_number} onChange={set("phone_number")} /></FormField>
 {!initial&&<p className="text-sm text-slate-500 sm:col-span-2">No user is created automatically. Open the organization after creation and add an existing user as owner. Defaults: Kenya, KES, Africa/Nairobi.</p>}
 </FormModal>;
}
