import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import type { Paginated } from "@/shared/types/api";
export function useAdminOptions<T>(key: string, url: string) {
  return useQuery({ queryKey: ["admin-options", key], queryFn: async ({signal}): Promise<T[]> => {
    const rows: T[] = [];
    for (let page = 1; ; page++) {
      const {data} = await api.get<T[] | Paginated<T>>(url,{signal,params:{page,page_size:100}});
      if (Array.isArray(data)) return data;
      rows.push(...data.results);
      if (!data.next) return rows;
    }
  } });
}
