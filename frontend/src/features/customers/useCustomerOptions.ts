import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { Package, Paginated, Router, Zone } from "@/shared/types/api";

async function allOptions<T>(url: string): Promise<T[]> {
  const rows: T[] = [];
  for (let page = 1; ; page++) {
    const { data } = await api.get<Paginated<T> | T[]>(url, { params: { page, page_size: 100 } });
    if (Array.isArray(data)) return data;
    rows.push(...data.results);
    if (!data.next) return rows;
  }
}
export function useCustomerOptions() {
  const zones = useQuery({ queryKey: ["customer-options", "zones"], queryFn: () => allOptions<Zone>(API.zones) });
  const packages = useQuery({ queryKey: ["customer-options", "packages"], queryFn: () => allOptions<Package>(API.packages) });
  const routers = useQuery({ queryKey: ["customer-options", "routers"], queryFn: () => allOptions<Router>(API.routers) });
  return { zones: zones.data ?? [], packages: packages.data ?? [], routers: routers.data ?? [],
    isLoading: zones.isLoading || packages.isLoading || routers.isLoading,
    isError: zones.isError || packages.isError || routers.isError,
    retry: () => { void zones.refetch(); void packages.refetch(); void routers.refetch(); },
  };
}
