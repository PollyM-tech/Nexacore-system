import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";

export function useAdminCrud(key: string, url: string) {
  const qc = useQueryClient();
  const onSuccess = async () => {
    const keys: (readonly unknown[])[] = [[key], ["admin-options", key]];
    if (key === "routers") keys.push(["customer-options", "routers"], ["bandwidth-live"], ["dashboard-summary"]);
    if (key === "zones") keys.push(["customer-options", "zones"]);
    if (key === "tickets") keys.push(["dashboard-summary"]);
    if (key === "onus") keys.push(["olt-devices"]);
    await Promise.all(keys.map(queryKey => qc.invalidateQueries({ queryKey })));
  };
  // Do not retain router/provider secrets in completed mutation cache entries.
  const create = useMutation({ gcTime: 0, mutationFn: (body: unknown) => api.post(url, body).then(r => r.data), onSuccess });
  const update = useMutation({ gcTime: 0, mutationFn: ({ id, body }: { id: number | string; body: unknown }) => api.patch(`${url}${id}/`, body).then(r => r.data), onSuccess });
  const remove = useMutation({ mutationFn: (id: number | string) => api.delete(`${url}${id}/`), onSuccess });
  return { create, update, remove };
}
