import { useEffect, useState, type ReactNode } from "react";
import { Button, TextInput } from "flowbite-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { TablePagination } from "@/shared/components/data/TablePagination";
import { apiError } from "@/shared/utils/apiError";
import type { Paginated } from "@/shared/types/api";
import type { IconName } from "@/shared/components/icons/Icon";

// Only these endpoints implement DRF SearchFilter. Others deliberately have no
// search control: filtering just the first server page would be misleading.
const searchable: string[] = [API.sms.templates, API.sms.logs, API.olt.devices, API.olt.onus];
type Props<T> = {
  queryKey: string; url: string; columns: Column<T>[]; rowKey: (row: T) => string | number;
  searchPlaceholder?: string; emptyTitle: string; emptyDescription: string; emptyIcon?: IconName;
  toolbarAction?: ReactNode; filters?: ReactNode; params?: Record<string, string | number | undefined>;
};
export function AdminResourceList<T extends object>(props: Props<T>) {
  const [page, setPage] = useState(1);
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const paramsKey = JSON.stringify(props.params ?? {});
  useEffect(() => { setPage(1); }, [paramsKey]);
  useEffect(() => { const timer = setTimeout(() => { setSearch(input.trim()); setPage(1); }, 300); return () => clearTimeout(timer); }, [input]);
  const params = Object.fromEntries(Object.entries(props.params ?? {}).filter(([, value]) => value !== "" && value !== undefined));
  const query = useQuery({ queryKey: [props.queryKey, "admin-list", { page, search, ...params }],
    queryFn: async ({ signal }) => (await api.get<Paginated<T> | T[]>(props.url, { signal, params: { ...params, page, page_size: 10, ...(search ? { search } : {}) } })).data });
  useEffect(() => {
    if (page > 1 && query.isError && (query.error as {response?:{status?:number}})?.response?.status === 404) setPage(1);
  }, [page, query.isError, query.error]);
  const data = query.data;
  const rows = Array.isArray(data) ? data : data?.results ?? [];
  const count = Array.isArray(data) ? data.length : data?.count ?? 0;
  const totalPages = Array.isArray(data) ? 1 : Math.max(1, Math.ceil(count / 10));
  useEffect(() => { if (data && page > totalPages) setPage(totalPages); }, [data, page, totalPages]);
  return <div className="min-w-0 space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-2">{searchable.includes(props.url) && <TextInput aria-label={props.searchPlaceholder ?? "Search"} placeholder={props.searchPlaceholder} value={input} onChange={(e) => setInput(e.target.value)} />}{props.filters}</div>
      {props.toolbarAction}
    </div>
    {query.isError && <Button color="light" onClick={() => void query.refetch()}>Retry</Button>}
    <ListPageSection isLoading={query.isLoading} isError={query.isError} errorMessage={apiError(query.error, "Could not load this list.")} isEmpty={rows.length === 0} emptyTitle={props.emptyTitle} emptyDescription={props.emptyDescription} emptyIcon={props.emptyIcon}>
      <DataTable columns={props.columns} rows={rows} rowKey={props.rowKey} />
      <TablePagination page={page} totalPages={totalPages} onPage={setPage} rangeLabel={`${count} records`} />
    </ListPageSection>
  </div>;
}
