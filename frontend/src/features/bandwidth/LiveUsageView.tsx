import { Alert, Button, TabItem, Tabs } from "flowbite-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { useAdminOptions } from "@/features/admin/useAdminOptions";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { bytes, duration, dateTime } from "@/shared/utils/format";
import { apiError } from "@/shared/utils/apiError";
import type { RadiusSession, RadiusSessionPreview, Router } from "@/shared/types/api";
import { ActiveSessionsTable } from "./ActiveSessionsTable";
import { useLiveBandwidth } from "./useLiveBandwidth";
const radiusColumns: Column<RadiusSession>[] = [
 {key:"customer",header:"Customer",render:r=>r.customer_name || "Unmapped"},
 {key:"username",header:"Username",render:r=>r.username},
 {key:"ip",header:"IP / MAC",render:r=><div>{r.ip_address || "—"}<p className="text-xs">{r.mac_address || "—"}</p></div>},
 {key:"router",header:"Router",render:r=>r.router_name || r.nas_ip_address || "—"},
 {key:"duration",header:"Duration",render:r=>duration(r.duration_seconds)},
 {key:"down",header:"Download",render:r=>bytes(r.download_bytes)},
 {key:"up",header:"Upload",render:r=>bytes(r.upload_bytes)},
 {key:"updated",header:"Last accounting update",render:r=>dateTime(r.updated_at)},
 {key:"online",header:"Accounting state",render:r=>r.online?"Online · accounting confirmed":"Not accounting-confirmed"},
];
function RadiusMonitor() {
 const q=useQuery({queryKey:["radius-active-sessions",{limit:100}],queryFn:async({signal})=>(await api.get<RadiusSessionPreview>(API.radius.activeSessions,{signal,params:{limit:100}})).data,refetchInterval:30000,retry:false});
 return <div className="space-y-3"><p className="text-sm text-slate-500">RADIUS accounting · up to 100 recent active sessions. Counters are cumulative, typically updated every five minutes, not instantaneous throughput. This table is separate from RouterOS observations.</p><Button size="xs" color="light" onClick={()=>void q.refetch()}>Refresh accounting</Button><ListPageSection isLoading={q.isLoading} isError={q.isError} errorMessage="RADIUS accounting unavailable." isEmpty={!q.data?.results.length} emptyTitle="No fresh accounting sessions" emptyDescription="No active sessions were returned by RADIUS."><DataTable columns={radiusColumns} rows={q.data?.results ?? []} rowKey={r=>r.id} /></ListPageSection></div>;
}
export function LiveUsageView() {
 const [params]=useSearchParams();const [routerId,setRouterId]=useState(params.get("router") ?? "");const [search,setSearch]=useState("");const [tab,setTab]=useState(0);
 const {data,query}=useLiveBandwidth(routerId,tab===0);const routers=useAdminOptions<Router>("routers",API.routers);const qc=useQueryClient();
 const sync=useMutation({mutationFn:async()=>(await api.post<{recorded:number}>(API.bandwidth.sync,{router:routerId || undefined})).data,onSuccess:()=>{void qc.invalidateQueries({queryKey:["bandwidth-summary"]});void qc.invalidateQueries({queryKey:["bandwidth-logs"]});}});
 return <Tabs aria-label="Session data source" variant="underline" onActiveTabChange={setTab}>
 <TabItem active title="RouterOS live"><div className="space-y-4">
 <p className="text-sm text-slate-500">RouterOS observations refresh every 25 seconds. Download/upload are cumulative session counters, not rates. API failures can undercount sessions. “No sessions” does not prove subscribers are offline. No safe standalone disconnect endpoint is available.</p>
 {routers.isError && <Alert color="failure">Router choices unavailable.</Alert>}
 {sync.isError && <Alert color="failure">{apiError(sync.error)}</Alert>}
 {sync.isSuccess && <Alert color="success">Snapshot request completed: {sync.data.recorded} sessions recorded. This is not a connectivity guarantee.</Alert>}
 <Button size="xs" color="light" onClick={()=>void query.refetch()}>Refresh RouterOS</Button>
 <ListPageSection isLoading={query.isLoading} isError={query.isError} errorMessage="RouterOS live data unavailable; check RADIUS accounting independently." isEmpty={false} emptyTitle="" emptyDescription="">
 {data && <>{!data.router_connected && <Alert color="warning">Unable to verify sessions: no selected router API responded. RADIUS accounting may still confirm connectivity.</Alert>}{data.router_connected && <p className="text-sm">Observed sessions: {data.online_clients}. Router coverage may be partial; the backend does not report individual router failures.</p>}
 {data.router_connected && <ActiveSessionsTable sessions={data.sessions} search={search} onSearch={setSearch} routerId={routerId} onRouterChange={setRouterId} routerOptions={(routers.data ?? []).map(r=>({value:String(r.id),label:r.name}))} onSync={()=>{if(window.confirm("Save a RouterOS accounting snapshot for reporting?"))sync.mutate();}} syncing={sync.isPending} />}
 {!data.router_connected && <select aria-label="Select router to verify" value={routerId} onChange={e=>setRouterId(e.target.value)} className="rounded-lg border-slate-300 dark:bg-slate-900"><option value="">All enabled routers</option>{routers.data?.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select>}</>}
 </ListPageSection></div></TabItem>
 <TabItem title="RADIUS accounting">{tab===1 && <RadiusMonitor />}</TabItem>
 </Tabs>;
}
