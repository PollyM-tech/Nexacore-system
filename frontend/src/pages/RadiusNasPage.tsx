import { useState } from 'react';
import { Button } from 'flowbite-react';
import { Link } from 'react-router-dom';
import { api } from '@/shared/api/client';
import { PageHeader } from '@/shared/components/layout/PageHeader';
import { AdminResourceList } from '@/features/admin/AdminResourceList';
import { useAdminOptions } from '@/features/admin/useAdminOptions';
import { PasswordInput } from '@/features/customers/PasswordInput';
import { Field,inputClass,useNetworkAction,ActionNotice,useHotspotRoles } from '@/features/hotspot/shared';

type Nas={id:number;public_id:string;name:string;source_ip:string;identifier:string;router:number|null;disconnect_port:number;is_active:boolean;hotspot_enabled:boolean};
type Disconnect={id:number;nas:number;session_id:string;reason:string;status:string;attempts:number;max_attempts:number;last_error:string;events:{number:number;result:string;error_cause:number|null}[]};
export function RadiusNasPage(){
 const roles=useHotspotRoles(),action=useNetworkAction();
 const [editing,setEditing]=useState<Nas|null|undefined>(),[secret,setSecret]=useState(''),[setup,setSetup]=useState<Nas|null>(null);
 const routers=useAdminOptions<{id:number;name:string}>('routers','/mikrotik/routers/');
 return <div className="space-y-6"><PageHeader title="RADIUS NAS devices" description="Your network hardware stays under your control. Register its unique VPN/source IP and RADIUS secret here."/>
 <p className="text-sm text-slate-500">Each NAS needs its own address and secret. Enable registered-NAS mode with Lintech after enrolling existing PPPoE routers. Secret rotation can take up to 60 seconds to reach the RADIUS client cache.</p>
 <ActionNotice action={action}/>
 {roles.admin&&<Button color="primary" onClick={()=>{setEditing(null);setSecret('');}}>Add NAS device</Button>}
 {editing!==undefined&&<form className="card-surface grid gap-4 p-5 md:grid-cols-2" key={editing?.id??'new'} onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);const body={create_pppoe_router:!editing&&data.get('create_pppoe_router')==='on',name:data.get('name'),identifier:data.get('identifier'),source_ip:data.get('source_ip'),router:data.get('router')?Number(data.get('router')):null,disconnect_port:Number(data.get('disconnect_port')),is_active:data.get('active')==='on',hotspot_enabled:data.get('hotspot')==='on',...(secret?{shared_secret:secret}:{})};void action.run(async()=>{if(editing)await api.patch(`/radius/nas/${editing.id}/`,body);else await api.post('/radius/nas/',body);setSecret('');setEditing(undefined);},'NAS saved. Configure the same secret and source address on your device.');}}>
 <Field label="Device name"><input className={inputClass} name="name" defaultValue={editing?.name} required maxLength={100}/></Field>
 <Field label="Unique NAS / VPN IPv4 address"><input className={inputClass} name="source_ip" defaultValue={editing?.source_ip} readOnly={!!editing} required/></Field>
 <Field label="NAS identifier (router identity, optional)"><input className={inputClass} name="identifier" defaultValue={editing?.identifier} maxLength={64}/></Field>
 <Field label="Existing PPPoE router attachment (optional)"><select className={inputClass} name="router" defaultValue={editing?.router??''} disabled={!!editing}><option value="">Hotspot-only NAS</option>{routers.data?.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></Field>
 {!editing&&<label className="flex gap-2"><input type="checkbox" name="create_pppoe_router"/>Create a RADIUS-only PPPoE router entry (no router API credentials)</label>}
 {editing&&<input type="hidden" name="router" value={editing.router??''}/>}
 <Field label="Incoming disconnect UDP port"><input className={inputClass} type="number" name="disconnect_port" min={1024} max={65535} defaultValue={editing?.disconnect_port??3799} required/></Field>
 <PasswordInput id="nas-secret" label={editing?'Replace shared secret (leave empty to keep)':'RADIUS shared secret (32–128 characters)'} required={!editing} value={secret} onChange={setSecret}/>
 <label className="flex items-center gap-2"><input name="active" type="checkbox" defaultChecked={editing?.is_active??true}/>Enabled for authentication</label>
 <label className="flex items-center gap-2"><input name="hotspot" type="checkbox" defaultChecked={editing?.hotspot_enabled??true}/>Allow Hotspot vouchers</label>
 <div className="flex gap-2 md:col-span-2"><Button type="submit" color="primary" disabled={action.pending||(!editing&&!!routers.isError)}>Save NAS</Button><Button type="button" color="light" onClick={()=>{setSecret('');setEditing(undefined);}}>Cancel</Button></div>
 {routers.isError&&<p role="alert">Router choices unavailable. Retry the page before attaching a PPPoE router.</p>}
 </form>}
 <AdminResourceList<Nas> queryKey="radius-nas" url="/radius/nas/" rowKey={r=>r.id} emptyTitle="No registered NAS devices" emptyDescription="Register a uniquely addressed NAS to enable isolated RADIUS services." columns={[
 {key:'name',header:'NAS',render:r=><div className="font-semibold">{r.name}<p className="text-xs text-slate-500">{r.source_ip}</p></div>},
 {key:'state',header:'Configuration',render:r=><span>{r.is_active?'Enabled':'Disabled'} · {r.hotspot_enabled?'Hotspot allowed':'PPPoE only'}</span>},
 {key:'port',header:'Disconnect port',render:r=>r.disconnect_port},
 {key:'actions',header:'Actions',render:r=><div className="flex flex-wrap gap-2"><Button size="xs" color="light" onClick={()=>setSetup(r)}>Setup</Button>{roles.admin&&<Button size="xs" color="light" onClick={()=>{setEditing(r);setSecret('');}}>Edit</Button>}</div>}]}/>
 {setup&&<section className="card-surface space-y-3 p-5" aria-label="NAS setup instructions"><h2 className="text-lg font-bold">Configure {setup.name}</h2><p className="text-sm">Replace RADIUS_SERVER_IP and YOUR_SHARED_SECRET on your own MikroTik. Use your existing Hotspot profile name. Restrict incoming disconnect traffic to the Lintech server/VPN address.</p><pre className="overflow-x-auto rounded-xl bg-slate-100 p-4 text-xs dark:bg-ink-800">{`/radius add address=RADIUS_SERVER_IP service=ppp,hotspot secret="YOUR_SHARED_SECRET" src-address=${setup.source_ip} require-message-auth=yes-for-request-resp\n/radius incoming set accept=yes port=${setup.disconnect_port}\n/ppp aaa set use-radius=yes accounting=yes interim-update=1m\n/ip hotspot profile set [find name="YOUR_HOTSPOT_PROFILE"] use-radius=yes radius-accounting=yes radius-interim-update=1m`}</pre><p className="text-sm">Keep local router administrator credentials. Local subscriber secrets matching RADIUS usernames can bypass RADIUS: resolve conflicts during the pilot. Disable MAC/cookie login methods that would bypass voucher checks; configure a trusted HTTPS Hotspot login with login-by=https. The voucher is also the username, so HTTP-CHAP alone does not conceal the code.</p><Link className="font-semibold underline" to={`/hotspot/${setup.public_id}`}>Open this NAS’s voucher purchase page</Link><Button color="light" disabled={action.pending} onClick={()=>void action.run(async()=>{const response=await api.get(`/radius/nas/${setup.id}/captive-template/`,{responseType:"blob"});const url=URL.createObjectURL(response.data);const link=document.createElement("a");link.href=url;link.download="login.html";link.click();URL.revokeObjectURL(url);},"Captive portal template downloaded. Keep the stock MikroTik md5.js beside login.html.")}>Download captive login template</Button><Button color="light" onClick={()=>setSetup(null)}>Close setup</Button></section>}
 <h2 className="text-xl font-bold">Disconnect requests</h2><p className="text-sm text-slate-500">Acknowledged means the NAS confirmed disconnection. A timeout does not prove that a subscriber went offline. Accounting Stop remains a separate event.</p>
 <AdminResourceList<Disconnect> queryKey="radius-disconnects" url="/radius/disconnects/" rowKey={r=>r.id} emptyTitle="No disconnect requests" emptyDescription="Suspensions, voucher expiry and operator actions appear here." columns={[
 {key:'session',header:'Session / NAS',render:r=><span>{r.session_id}<small className="block">NAS #{r.nas}</small></span>},{key:'reason',header:'Reason',render:r=>r.reason},{key:'status',header:'Result',render:r=><span className="font-semibold">{r.status.replaceAll('_',' ')}</span>},{key:'tries',header:'Attempts',render:r=><div>{r.attempts} / {r.max_attempts}{r.events.map(e=><p className="text-xs" key={e.number}>#{e.number} {e.result}{e.error_cause?` (${e.error_cause})`:''}</p>)}</div>},
 {key:'actions',header:'Action',render:r=>roles.network&&['failed','retry'].includes(r.status)?<Button size="xs" disabled={action.pending} onClick={()=>void action.run(async()=>{await api.post(`/radius/disconnects/${r.id}/retry/`);},'Retry queued.')}>Retry</Button>:<span>—</span>}]}/>
 </div>;
}
