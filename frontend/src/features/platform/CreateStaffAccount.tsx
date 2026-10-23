import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Select, TextInput } from "flowbite-react";
import { api } from "@/shared/api/client";
import { FormModal } from "@/shared/components/ui/FormModal";
import { FormField } from "@/shared/components/ui/FormField";
import { PasswordInput } from "@/features/customers/PasswordInput";
const memberRoles = ["owner", "admin", "technician", "billing", "support", "viewer"] as const;
import { platformKeys } from "./api";
import { platformError } from "./PlatformFeedback";

export function CreateStaffAccount({orgId,onClose}:{orgId:string;onClose:()=>void}) {
  const [form,setForm]=useState({username:"",email:"",first_name:"",last_name:"",role:"viewer"});
  const [password,setPassword]=useState("");
  const [confirmation,setConfirmation]=useState("");
  const [validation,setValidation]=useState("");
  const qc=useQueryClient();
  const create=useMutation({gcTime:0,
    // Credentials stay in this mounted form, never in mutation variables or query data.
    mutationFn:async()=>{try {await api.post(`/platform/organizations/${encodeURIComponent(orgId)}/users/`,{...form,password});} catch(error) {throw new Error(platformError(error));}},
    onSuccess:async()=>{setPassword("");setConfirmation("");await Promise.all([platformKeys.members(orgId),platformKeys.organization(orgId),platformKeys.users,platformKeys.organizations,platformKeys.summary,platformKeys.audit].map(queryKey=>qc.invalidateQueries({queryKey})));onClose();},
  });
  return <FormModal open onClose={()=>{setPassword("");setConfirmation("");onClose();}} title="Create ISP staff account" submitLabel="Create account" submitting={create.isPending} error={validation || (create.isError?create.error.message:null)} onSubmit={e=>{e.preventDefault();if(password!==confirmation){setValidation("Passwords must match.");return;}setValidation("");create.mutate();}}>
    <p className="text-sm text-slate-500 sm:col-span-2">Creates a standard staff account for this ISP. It never grants Django or platform administrator access. Share the initial password through a secure channel.</p>
    {([['username','Username'],['email','Email'],['first_name','First name'],['last_name','Last name']] as const).map(([field,label])=><FormField key={field} htmlFor={`new-staff-${field}`} label={label}><TextInput id={`new-staff-${field}`} type={field==='email'?'email':'text'} required={field==='username'||field==='email'} maxLength={field==='email'?254:150} value={form[field]} onChange={e=>setForm(f=>({...f,[field]:e.target.value}))} /></FormField>)}
    <FormField htmlFor="new-staff-role" label="ISP role"><Select id="new-staff-role" value={form.role} onChange={e=>setForm(f=>({...f,role:e.target.value}))}>{memberRoles.map(role=><option key={role}>{role}</option>)}</Select></FormField>
    <PasswordInput id="new-staff-password" label="Initial password" value={password} onChange={setPassword} />
    <PasswordInput id="new-staff-confirm" label="Confirm password" value={confirmation} onChange={setConfirmation} />
  </FormModal>;
}
