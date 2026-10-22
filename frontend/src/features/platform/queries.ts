import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { PLATFORM, platformKeys as keys } from "./api";
import type { Organization, PlatformMe, PlatformSummary } from "./types";
export function usePlatformMe() {
  return useQuery({queryKey:keys.me,queryFn:async({signal})=>(await api.get<PlatformMe>(PLATFORM.me,{signal})).data,retry:false,staleTime:30_000});
}
export function usePlatformSummary() {
  return useQuery({queryKey:keys.summary,queryFn:async({signal})=>(await api.get<PlatformSummary>(PLATFORM.summary,{signal})).data,retry:false});
}
export function usePlatformOrganization(id:string) {
  return useQuery({queryKey:keys.organization(id),queryFn:async({signal})=>(await api.get<Organization>(PLATFORM.organization(id),{signal})).data,retry:false});
}
export function useOrganizationMutation() {
 const qc=useQueryClient();
 return useMutation({mutationFn:async({id,body}:{id?:number;body:Record<string,unknown>})=>(id===undefined?await api.post<Organization>(PLATFORM.organizations,body):await api.patch<Organization>(PLATFORM.organization(id),body)).data,
 onSuccess:async(org)=>{await Promise.all([keys.organizations,keys.organization(org.id),keys.summary,keys.audit].map(queryKey=>qc.invalidateQueries({queryKey})));}});
}
export function useMembershipMutation(orgId:string) {
 const qc=useQueryClient();
 return useMutation({mutationFn:async({id,body,remove}:{id?:number;body?:Record<string,unknown>;remove?:boolean})=>{
  if(remove&&id!==undefined)return api.delete(PLATFORM.member(orgId,id));
  if(id!==undefined)return api.patch(PLATFORM.member(orgId,id),body);
  return api.post(PLATFORM.members(orgId),body);
 },onSuccess:async()=>{await Promise.all([keys.members(orgId),keys.organization(orgId),keys.organizations,keys.users,keys.summary,keys.audit].map(queryKey=>qc.invalidateQueries({queryKey})));}});
}
