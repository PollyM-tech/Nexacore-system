import { Button, Select } from "flowbite-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PlatformList } from "./PlatformList";
import { PLATFORM, platformKeys } from "./api";
import { OrganizationForm } from "./OrganizationForm";
import { OrganizationMembers } from "./OrganizationMembers";
import { usePlatformOrganization } from "./queries";
import { PlatformError } from "./PlatformFeedback";
import { PageHeader } from "@/shared/components/layout/PageHeader";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { TableSkeleton } from "@/shared/components/ui/TableSkeleton";
import type { Column } from "@/shared/components/data/DataTable";
import { dateTime } from "@/shared/utils/format";
import type { Organization } from "./types";
const count=(n:unknown)=>typeof n==="number"&&Number.isFinite(n)?n:"Unavailable";
const columns:Column<Organization>[]=[
 {key:"name",header:"Organization",render:o=><Link className="font-medium text-brand-600 underline" to={`/superadmin/organizations/${o.id}`}>{o.name}</Link>},
 {key:"slug",header:"Slug",render:o=>o.slug},
 {key:"status",header:"Status / access",render:o=><div><StatusBadge status={o.status} /><p className="mt-1 text-xs">{o.is_active?"Enabled":"Disabled"}</p></div>},
 {key:"members",header:"Members",render:o=>count(o.member_count)},
 {key:"customers",header:"Customers",render:o=>count(o.customer_count)},
 {key:"routers",header:"Routers",render:o=>count(o.router_count)},
 {key:"packages",header:"Packages",render:o=>count(o.package_count)},
 {key:"created",header:"Created",render:o=>dateTime(o.created_at)},
];
export function OrganizationsManager() {
 const [status,setStatus]=useState("");const [form,setForm]=useState<Organization|"new"|null>(null);
 return <><PageHeader title="ISP organizations" description="Platform-managed tenants. Organization deletion is unavailable." /><PlatformList<Organization> queryKey={platformKeys.organizations} url={PLATFORM.organizations} columns={[...columns,{key:"actions",header:"Actions",render:o=><Button type="button" size="xs" color="light" onClick={()=>setForm(o)}>Edit organization</Button>}]} searchLabel="Search organization name or slug" params={{status}} filters={<Select aria-label="Organization status filter" value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="inactive">Inactive</option></Select>} action={<Button onClick={()=>setForm("new")}>Create organization</Button>} />{form!==null&&<OrganizationForm initial={form==="new"?undefined:form} onClose={()=>setForm(null)} />}</>;
}
export function OrganizationDetail() {
 const {id=""}=useParams();const q=usePlatformOrganization(id);const [edit,setEdit]=useState(false);const o=q.data;
 if(q.isPending)return <TableSkeleton />;if(q.isError)return <PlatformError error={q.error} retry={()=>void q.refetch()} />;if(!o)return null;
 return <><Link to="/superadmin/organizations" className="text-brand-600 underline">All organizations</Link><PageHeader title={o.name} description={`Organization ${o.id} · ${o.slug}`} /><div className="grid gap-4 md:grid-cols-2"><section className="card-surface space-y-3 p-5"><h2 className="font-semibold">Organization overview</h2><StatusBadge status={o.status} /><p>Organization access: {o.is_active?"Enabled":"Disabled"}</p><p>Created: {dateTime(o.created_at)}</p><p>Updated: {dateTime(o.updated_at)}</p><p>{o.email||"No contact email"} · {o.phone_number||"No contact phone"}</p><p>{o.country} · {o.currency} · {o.timezone}</p><Button color="light" onClick={()=>setEdit(true)}>Edit organization</Button></section><section className="card-surface space-y-3 p-5"><h2 className="font-semibold">Assigned records</h2>{[["Members",o.member_count],["Customers",o.customer_count],["Routers",o.router_count],["Packages",o.package_count]].map(([label,n])=><p key={label}>{label}: {count(n)}</p>)}<p className="text-xs text-slate-500">Counts include inactive assigned records. No tenant secrets or subscriber operations are exposed here.</p></section></div><OrganizationMembers orgId={id} />{edit&&<OrganizationForm initial={o} onClose={()=>setEdit(false)} />}</>;
}
