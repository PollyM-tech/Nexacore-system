import { useEffect, useState, type ReactNode } from "react";
import { Button, TextInput } from "flowbite-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { TablePagination } from "@/shared/components/data/TablePagination";
import { TableSkeleton } from "@/shared/components/ui/TableSkeleton";
import { EmptyState } from "@/shared/components/ui/EmptyState";
import type { Paginated } from "@/shared/types/api";
import { PlatformError, httpStatus } from "./PlatformFeedback";
type Params=Record<string,string|number|undefined>;
export function usePlatformList<T>(queryKey:readonly unknown[],url:string,params:Params) {
 return useQuery({queryKey:[...queryKey,params],queryFn:async({signal})=>(await api.get<Paginated<T>>(url,{signal,params})).data,retry:false});
}
export function PlatformList<T extends {id:number}>({queryKey,url,columns,searchLabel,filters,params={},action,emptyTitle="No records found"}:{queryKey:readonly unknown[];url:string;columns:Column<T>[];searchLabel?:string;filters?:ReactNode;params?:Params;action?:ReactNode;emptyTitle?:string}) {
 const [page,setPage]=useState(1);const [input,setInput]=useState("");const [search,setSearch]=useState("");const filterKey=JSON.stringify(params);
 useEffect(()=>{setPage(1);},[filterKey]);
 useEffect(()=>{const timer=setTimeout(()=>{setSearch(input.trim());setPage(1);},300);return()=>clearTimeout(timer);},[input]);
 const clean=Object.fromEntries(Object.entries(params).filter(([,v])=>v!==""&&v!==undefined));
 const q=usePlatformList<T>(queryKey,url,{...clean,page,page_size:10,...(searchLabel&&search?{search}:{})});
 const totalPages=q.data?Math.max(1,Math.ceil(q.data.count/10)):1;
 useEffect(()=>{if(q.data&&page>totalPages)setPage(totalPages);if(q.isError&&httpStatus(q.error)===404&&page>1)setPage(1);},[q.data,q.isError,q.error,page,totalPages]);
 return <div className="min-w-0 space-y-4"><div className="flex flex-wrap items-end justify-between gap-3"><div className="flex flex-wrap items-end gap-3">{searchLabel&&<TextInput aria-label={searchLabel} placeholder={searchLabel} value={input} onChange={e=>setInput(e.target.value)} />}{filters}</div>{action}</div>
 {q.isPending?<TableSkeleton />:q.isError?<PlatformError error={q.error} retry={()=>void q.refetch()} />:!q.data?.results.length?<EmptyState title={emptyTitle} description="No matching platform records were returned." />:<><DataTable columns={columns} rows={q.data.results} rowKey={r=>r.id} /><TablePagination page={page} totalPages={totalPages} onPage={setPage} rangeLabel={`${q.data.count} records`} /></>}
 <Button type="button" color="light" size="xs" disabled={q.isFetching} onClick={()=>void q.refetch()}>Refresh</Button></div>;
}
