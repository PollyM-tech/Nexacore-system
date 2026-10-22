import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { LiveUsage } from "./types";
export type ThroughputPoint = { t: number; down: number; up: number };
export function useLiveBandwidth(routerId: string, enabled = true) {
  const query=useQuery({queryKey:["bandwidth-live",routerId],queryFn:async({signal})=>(await api.get<LiveUsage>(API.bandwidth.live,{signal,params:routerId?{router:routerId}:{}})).data,enabled,refetchInterval:enabled?25000:false,retry:false});
  return {data:query.data,query};
}
