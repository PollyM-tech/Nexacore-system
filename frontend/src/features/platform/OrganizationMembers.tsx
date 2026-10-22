import { Button, Select } from "flowbite-react";
import { useState } from "react";
import { PLATFORM, platformKeys } from "./api";
import { PlatformList } from "./PlatformList";
import { useMembershipMutation } from "./queries";
import { platformError } from "./PlatformFeedback";
import { FormModal } from "@/shared/components/ui/FormModal";
import { FormField } from "@/shared/components/ui/FormField";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import { dateTime } from "@/shared/utils/format";
import type { Membership, MemberRole, PlatformUser } from "./types";
export const memberRoles:MemberRole[]=["owner","admin","technician","billing","support","viewer"];
type Action={kind:"add"}|{kind:"edit"|"remove";member:Membership};
export function OrganizationMembers({orgId}:{orgId:string}) {
 const [action,setAction]=useState<Action|null>(null);
 return <section className="space-y-4"><h2 className="text-xl font-semibold">Organization members</h2><p className="text-sm text-slate-500">Add existing users only. The backend protects the last active owner; there is no invitation flow.</p>
 <PlatformList<Membership> queryKey={platformKeys.members(orgId)} url={PLATFORM.members(orgId)} action={<Button onClick={()=>setAction({kind:"add"})}>Add existing user</Button>} columns={[
 {key:"user",header:"User",render:m=><div>{m.user.username}<p className="text-xs">{m.user.email}</p></div>},
 {key:"role",header:"Role",render:m=>m.role},
 {key:"active",header:"Membership",render:m=><StatusBadge status={m.is_active?"active":"inactive"} />},
 {key:"joined",header:"Joined",render:m=>dateTime(m.created_at)},
 {key:"actions",header:"Actions",render:m=><div className="flex gap-2"><Button type="button" size="xs" color="light" onClick={()=>setAction({kind:"edit",member:m})}>Edit membership</Button><Button type="button" size="xs" color="failure" onClick={()=>setAction({kind:"remove",member:m})}>Remove membership</Button></div>},
 ]} />{action&&<MembershipForm orgId={orgId} action={action} onClose={()=>setAction(null)} />}</section>;
}
function MembershipForm({orgId,action,onClose}:{orgId:string;action:Action;onClose:()=>void}) {
 const member=action.kind==="add"?undefined:action.member;
 const [user,setUser]=useState<PlatformUser|null>(null);const [role,setRole]=useState<MemberRole>(member?.role??"viewer");const [active,setActive]=useState(member?.is_active??true);
 const mutation=useMembershipMutation(orgId);
 return <FormModal open onClose={onClose} title={action.kind==="remove"?"Remove organization membership":member?`Edit membership · ${member.user.username}`:"Add existing user"} submitting={mutation.isPending} submitDisabled={action.kind==="add"&&!user} error={mutation.isError?platformError(mutation.error):null} submitLabel={action.kind==="remove"?"Remove membership":member?"Save membership":"Add membership"} onSubmit={e=>{
  e.preventDefault();if(action.kind==="remove"&&member){mutation.mutate({id:member.id,remove:true},{onSuccess:onClose});return;}
  if(!member&&!user)return;
  if(member&&((member.is_active&&!active)||member.role!==role)&&!window.confirm(`Change access for ${member.user.username}? The backend will reject changes that leave no active owner.`))return;
  mutation.mutate({id:member?.id,body:{...(!member?{user_id:user!.id}:{}),role,is_active:active}},{onSuccess:onClose});
 }}>
 {action.kind==="remove"?<p className="sm:col-span-2">Remove {member?.user.username} from this organization? Their user account remains. The last active owner cannot be removed.</p>:<>
 {action.kind==="add"&&<div className="sm:col-span-2">{user?<div className="flex flex-wrap items-center gap-3"><p>Selected: {user.username} · {user.email}{!user.is_active?" · User account inactive":""}</p><Button type="button" size="xs" color="light" onClick={()=>setUser(null)}>Choose another user</Button></div>:<PlatformList<PlatformUser> queryKey={platformKeys.users} url={PLATFORM.users} searchLabel="Find an existing platform user" columns={[{key:"user",header:"Existing user",render:u=><div>{u.username}<p className="text-xs">{u.email}</p></div>},{key:"select",header:"Select",render:u=><Button type="button" size="xs" color="light" onClick={()=>setUser(u)}>Choose {u.username}</Button>}]} />}</div>}
 <FormField label="Role" htmlFor="membership-role"><Select id="membership-role" value={role} onChange={e=>setRole(e.target.value as MemberRole)}>{memberRoles.map(r=><option value={r} key={r}>{r}</option>)}</Select></FormField>
 <FormField label="Membership state" htmlFor="membership-active"><Select id="membership-active" value={String(active)} onChange={e=>setActive(e.target.value==="true")}><option value="true">Active</option><option value="false">Inactive</option></Select></FormField>
 </>}
 </FormModal>;
}
