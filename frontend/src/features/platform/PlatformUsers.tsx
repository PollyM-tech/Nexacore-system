import { PageHeader } from "@/shared/components/layout/PageHeader";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import type { Column } from "@/shared/components/data/DataTable";
import { dateTime } from "@/shared/utils/format";
import { PLATFORM, platformKeys } from "./api";
import { PlatformList } from "./PlatformList";
import type { PlatformUser } from "./types";
export const platformUserColumns:Column<PlatformUser>[]=[
 {key:"user",header:"User",render:u=><div>{u.username}<p className="text-xs text-slate-500">{u.email||"No email"}</p></div>},
 {key:"name",header:"Name",render:u=>`${u.first_name} ${u.last_name}`.trim()||"—"},
 {key:"active",header:"Account",render:u=><StatusBadge status={u.is_active?"active":"inactive"} />},
 {key:"platform",header:"Platform privilege",render:u=>u.is_superuser?"Platform administrator":"Standard account"},
 {key:"memberships",header:"Memberships",render:u=>u.membership_count ?? "Unavailable"},
 {key:"joined",header:"Joined",render:u=>dateTime(u.date_joined)},
 {key:"last",header:"Last login",render:u=>dateTime(u.last_login)},
];
export function PlatformUsers() {return <><PageHeader title="Platform users" description="Read-only account inventory. User creation, invitations and credential management are not available in this API." /><PlatformList<PlatformUser> queryKey={platformKeys.users} url={PLATFORM.users} columns={platformUserColumns} searchLabel="Search username, email or name" /></>;}
