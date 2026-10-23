import { cloneElement,isValidElement,useId,useState,type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiError } from '@/shared/utils/apiError';
import { useSession } from '@/features/auth/useSession';

export function Field({label,children}:{label:string;children:ReactNode}) {
  const generated=useId();
  const control=isValidElement<{id?:string}>(children)?children:null;
  const id=control?.props.id??generated;
  return <div className="space-y-1.5 text-sm font-semibold"><label className="block" htmlFor={id}>{label}</label>{control?cloneElement(control,{id}):children}</div>;
}
export const inputClass='w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-ink-800';
export function useNetworkAction() {
  const client=useQueryClient();
  const [pending,setPending]=useState(false),[error,setError]=useState(''),[success,setSuccess]=useState('');
  async function run(operation:()=>Promise<void>,message='Saved.') {
    if(pending)return;
    setPending(true);setError('');setSuccess('');
    try {await operation(); await Promise.all(['hotspot','radius-nas','radius-disconnects','hotspot-plans','hotspot-batches','hotspot-vouchers','hotspot-sessions','hotspot-sales','hotspot-purchases'].map(key=>client.invalidateQueries({queryKey:[key]}))); await client.invalidateQueries({queryKey:['admin-options','hotspot-plans']});await client.invalidateQueries({queryKey:['admin-options','hotspot-batches']});await client.invalidateQueries({queryKey:['admin-options','routers']});setSuccess(message);}
    catch(e){setError(apiError(e,'Operation failed. Please try again.'));}
    finally{setPending(false);}
  }
  return {pending,error,success,run};
}
export function useHotspotRoles() {
  const role=useSession().user?.membership?.role;
  return {admin:!!role&&['owner','admin'].includes(role),billing:!!role&&['owner','admin','billing'].includes(role),network:!!role&&['owner','admin','technician'].includes(role)};
}
export function ActionNotice({action}:{action:ReturnType<typeof useNetworkAction>}){
  return <>{action.error&&<p role="alert" className="rounded-xl border border-red-200 p-3 text-sm text-red-700 dark:text-red-300">{action.error}</p>}{action.success&&<p role="status" className="rounded-xl border border-emerald-200 p-3 text-sm dark:text-emerald-200">{action.success}</p>}</>;
}
