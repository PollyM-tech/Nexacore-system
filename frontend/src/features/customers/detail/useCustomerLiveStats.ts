import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { LiveStats } from "@/shared/types/api";
import { customerKeys } from "../customerQueryKeys";
export function useCustomerLiveStats(id: string) {
  return useQuery({ queryKey: customerKeys.live(id), queryFn: async () => (await api.get<LiveStats>(API.customerLiveStats(id))).data,
    refetchInterval: 25_000, staleTime: 20_000, retry: false });
}
