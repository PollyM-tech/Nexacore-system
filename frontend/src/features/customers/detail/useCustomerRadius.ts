import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { RadiusCustomerSummary, RadiusSessionPreview } from "@/shared/types/api";
import { customerKeys } from "../customerQueryKeys";
export function useCustomerRadiusSummary(id: string, enabled: boolean) {
  return useQuery({ queryKey: customerKeys.summary(id), queryFn: async () => (await api.get<RadiusCustomerSummary>(API.radius.customerSummary(id))).data,
    enabled, refetchInterval: 30_000, staleTime: 20_000, retry: false });
}
export function useCustomerRadiusSessions(id: string) {
  return useQuery({ queryKey: customerKeys.sessions(id), queryFn: async () => (await api.get<RadiusSessionPreview & { customer_id: string }>(API.radius.customerSessions(id), { params: { limit: 20 } })).data,
    refetchInterval: 30_000, retry: false });
}
