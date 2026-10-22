import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { Package, Paginated } from "@/shared/types/api";

export const packageKeys = {
  all: ["packages"] as const,
  list: (search: string, status: string, page: number) => ["packages", "list", { search, status, page }] as const,
  detail: (id: number | undefined) => ["packages", "detail", id] as const,
};
export function usePackages(search: string, status: string, page: number) {
  return useQuery({
    queryKey: packageKeys.list(search, status, page),
    queryFn: async ({ signal }) => (await api.get<Paginated<Package>>(API.packages, {
      signal, params: { search: search || undefined, is_active: status || undefined, page, page_size: 10, ordering: "name" },
    })).data,
  });
}
export function usePackageDetail(id: number | undefined) {
  return useQuery({ queryKey: packageKeys.detail(id), enabled: id !== undefined, staleTime: 0, refetchOnWindowFocus: false, refetchOnReconnect: false,
    queryFn: async ({ signal }) => (await api.get<Package>(`${API.packages}${id}/`, { signal })).data });
}
export function usePackageMutations() {
  const qc = useQueryClient();
  const invalidate = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: packageKeys.all }),
      qc.invalidateQueries({ queryKey: ["customer-options", "packages"] }),
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] }),
    ]);
  };
  const save = useMutation({ mutationFn: ({ id, body }: { id?: number; body: Record<string, unknown> }) =>
    id === undefined ? api.post(API.packages, body) : api.patch(`${API.packages}${id}/`, body), onSuccess: invalidate });
  const remove = useMutation({ mutationFn: (id: number) => api.delete(`${API.packages}${id}/`), onSuccess: invalidate });
  const status = useMutation({ mutationFn: ({ id, active }: { id: number; active: boolean }) =>
    api.patch(`${API.packages}${id}/`, { is_active: active }), onSuccess: invalidate });
  return { save, remove, status };
}
