import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { RadiusSessionPreview } from "@/shared/types/api";

export function useActiveRadiusSessions() {
  return useQuery({
    queryKey: ["radius-active-sessions", { limit: 8 }],
    queryFn: async () => (await api.get<RadiusSessionPreview>(API.radius.activeSessions, {
      params: { limit: 8 },
    })).data,
    refetchInterval: 30_000,
    retry: false,
  });
}
