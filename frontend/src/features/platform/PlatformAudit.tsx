import { TextInput } from "flowbite-react";
import { useState } from "react";
import { PLATFORM, platformKeys } from "./api";
import { PlatformList } from "./PlatformList";
import { PageHeader } from "@/shared/components/layout/PageHeader";
import { dateTime } from "@/shared/utils/format";
import type { PlatformAuditEvent } from "./types";
function sensitive(key:string) {const normalized=key.toLowerCase().replace(/[^a-z0-9]/g,"");return /password|passwd|secret|token|apikey|pppoepass|credential|authorization|privatekey|encryptionkey|community|passkey|consumerkey|signingkey/.test(normalized)||["pass","pwd"].includes(normalized);}
export function safeMetadataRows(metadata:unknown):[string,string][] {
 const rows:[string,string][]=[];let visited=0;
 function visit(value:unknown,path:string,depth:number) {
  if(++visited>60||rows.length>=20)return;
  if(depth>3){rows.push([path,"Nested values omitted"]);return;}
  if(Array.isArray(value)){value.slice(0,8).forEach((v,i)=>visit(v,`${path}[${i}]`,depth+1));return;}
  if(value&&typeof value==="object"){
   const entries=Object.entries(value);const credentialRecord=entries.some(([key,v])=>["attribute","key","name"].includes(key.toLowerCase())&&typeof v==="string"&&sensitive(v));
   if(credentialRecord)return;
   entries.slice(0,20).forEach(([key,v])=>{if(sensitive(key)||(credentialRecord&&["value","values"].includes(key.toLowerCase())))return;visit(v,path?`${path}.${key.slice(0,60)}`:key.slice(0,60),depth+1);});return;
  }
  if(value==="[REDACTED]")return;
  rows.push([path||"Value",String(value??"—").slice(0,240)]);
 }
 visit(metadata,"",0);return rows;
}
export function AuditMetadata({value}:{value:unknown}) {
 const rows=safeMetadataRows(value);
 return rows.length?<details className="min-w-48 max-w-sm"><summary className="cursor-pointer text-brand-600">Safe metadata preview</summary><dl className="mt-2 space-y-2 text-xs">{rows.map(([key,v],i)=><div key={i}><dt className="break-all font-semibold">{key}</dt><dd className="break-all">{v}</dd></div>)}</dl><p className="mt-2 text-xs text-slate-500">Limited preview; sensitive fields and larger structures are omitted.</p></details>:<span className="text-xs text-slate-500">No displayable metadata</span>;
}
export function PlatformAudit() {
 const [draft,setDraft]=useState({organization:"",user:"",action:""});const [filters,setFilters]=useState(draft);
 return <><PageHeader title="Platform audit log" description="Cross-organization immutable audit history, newest first. Sensitive metadata is omitted." /><form className="flex flex-wrap items-end gap-3" onSubmit={e=>{e.preventDefault();setFilters(draft);}}>{(["organization","user","action"] as const).map(field=><div key={field}><label className="mb-1 block text-sm" htmlFor={`audit-${field}`}>{field==="user"?"Actor user ID":field==="organization"?"Organization ID":"Exact action"}</label><TextInput id={`audit-${field}`} type={field==="action"?"text":"number"} min={field==="action"?undefined:1} value={draft[field]} onChange={e=>setDraft(p=>({...p,[field]:e.target.value}))} /></div>)}<button type="submit" className="rounded-lg bg-brand-600 px-4 py-2 text-white focus-visible:outline-2">Apply filters</button><button type="button" onClick={()=>{setDraft({organization:"",user:"",action:""});setFilters({organization:"",user:"",action:""});}} className="rounded-lg border px-4 py-2">Reset</button></form>
 <PlatformList<PlatformAuditEvent> queryKey={platformKeys.audit} url={PLATFORM.audit} params={filters} columns={[
 {key:"time",header:"Timestamp",render:e=>dateTime(e.created_at)},
 {key:"actor",header:"Actor",render:e=>e.actor?`${e.actor.username} · ${e.actor.email}`:"System / deleted account"},
 {key:"org",header:"Organization",render:e=>e.organization_name??"Platform / deleted organization"},
 {key:"action",header:"Action",render:e=>e.action},
 {key:"resource",header:"Resource",render:e=>`${e.resource_type} ${e.resource_id}`},
 {key:"metadata",header:"Metadata",render:e=><AuditMetadata value={e.metadata} />},
 ]} /></>;
}
