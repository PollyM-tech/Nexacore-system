export type PlatformIdentity = { id: number; username: string; email: string; first_name: string; last_name: string };
export type PlatformMe = { is_platform_admin: boolean; user: PlatformIdentity };
export type PlatformUser = PlatformIdentity & { is_active: boolean; is_superuser: boolean; membership_count: number; date_joined: string; last_login: string | null };
export type Organization = {
  id: number; name: string; slug: string; organization_type: "hotspot" | "pppoe" | "hybrid";
  status: "active" | "suspended" | "inactive"; is_active: boolean;
  phone_number: string; email: string; country: string; currency: string; timezone: string;
  created_at: string; updated_at: string; member_count: number; customer_count: number; router_count: number; package_count: number;
};
export type MemberRole = "owner" | "admin" | "technician" | "billing" | "support" | "viewer";
export type Membership = { id: number; user: PlatformIdentity; role: MemberRole; is_active: boolean; created_at: string; updated_at: string };
export type PlatformSummary = { organizations: Totals; users: {total:number}; customers: Totals; routers: Totals; packages: Totals };
type Totals = {total:number;active:number};
export type PlatformAuditEvent = {id:number;actor:PlatformIdentity|null;actor_role:string;organization:number|null;organization_name:string|null;action:string;resource_type:string;resource_id:string;created_at:string;metadata:unknown};
