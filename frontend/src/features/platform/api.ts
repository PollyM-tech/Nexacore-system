export const PLATFORM = {
  me:"/platform/me/", summary:"/platform/summary/", organizations:"/platform/organizations/",
  organization:(id:string|number)=>`/platform/organizations/${encodeURIComponent(id)}/`,
  members:(id:string|number)=>`/platform/organizations/${encodeURIComponent(id)}/members/`,
  member:(org:string|number,id:number)=>`/platform/organizations/${encodeURIComponent(org)}/members/${id}/`,
  users:"/platform/users/", audit:"/platform/audit/",
};
export const platformKeys = {
  me:["platform","me"] as const, summary:["platform","summary"] as const,
  organizations:["platform","organizations","list"] as const,
  organization:(id:string|number)=>["platform","organizations","detail",String(id)] as const,
  members:(id:string|number)=>["platform","members",String(id)] as const,
  users:["platform","users"] as const, audit:["platform","audit"] as const,
};
