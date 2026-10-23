import { useEffect, useRef, useState } from 'react';
import { useParams,Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'flowbite-react';
import { api } from '@/shared/api/client';
import { kes,bytes } from '@/shared/utils/format';
import { apiError } from '@/shared/utils/apiError';
import { Brand } from '@/shared/components/layout/Brand';
import { Field,inputClass } from '@/features/hotspot/shared';

type Offer={id:number;name:string;price:string;duration_seconds:number;quota_bytes:number|null};
export function HotspotPurchasePage(){
 const {nasId}=useParams();const [phone,setPhone]=useState(''),[plan,setPlan]=useState(''),[token,setToken]=useState(''),[code,setCode]=useState(''),[state,setState]=useState(''),[error,setError]=useState(''),[pending,setPending]=useState(false);
 const requestId=useRef(crypto.randomUUID());
 const offers=useQuery({queryKey:['hotspot-public-plans',nasId],queryFn:async()=> (await api.get<{isp:string;purchases_enabled:boolean;plans:Offer[]}>(`/hotspot/public/${nasId}/`)).data,retry:false});
 useEffect(()=>{if(!token||code)return;let live=true;let attempts=0;const poll=async()=>{try{const {data}=await api.post<{status:string;fulfilled:boolean;voucher_code:string|null}>('/hotspot/purchase-status/',{purchase_token:token});if(!live)return;setError('');setState(data.status);if(data.voucher_code){setCode(data.voucher_code);setToken('');setPhone('');}else if(['failed','cancelled','timeout'].includes(data.status)){setToken('');requestId.current=crypto.randomUUID();setError('Payment did not complete. No voucher was activated.');}}catch{if(live)setError('Could not check payment status. Keep this page open and try checking again.');}attempts++;if(attempts>=60&&live){setToken('');setError('Payment is still unconfirmed. Contact your ISP with your M-Pesa receipt before paying again.');}};void poll();const timer=setInterval(()=>void poll(),5000);return()=>{live=false;clearInterval(timer);};},[token,code]);
 return <main className="min-h-screen bg-white px-4 py-10 text-slate-900 dark:bg-ink-950 dark:text-white"><div className="mx-auto max-w-lg space-y-6"><Brand/><h1 className="text-3xl font-bold">Buy a Hotspot voucher</h1><p>Internet access from {offers.data?.isp??'your ISP'}. This is a subscriber purchase, not a Lintech SaaS subscription.</p>
 {offers.isLoading&&<p role="status">Loading plans…</p>}{offers.isError&&<p role="alert">Plans unavailable. Confirm the purchase link with your ISP. <button className="underline" onClick={()=>void offers.refetch()}>Retry</button></p>}
 {offers.data&&!offers.data.purchases_enabled&&<p role="status">Online purchase is not available yet. Obtain a voucher directly from your ISP.</p>}
 {error&&<p role="alert" className="rounded-xl border border-orange-300 p-3">{error}</p>}
 {!code&&<form className="card-surface space-y-4 p-5" onSubmit={async e=>{e.preventDefault();if(pending||token)return;setPending(true);setError('');try{const {data}=await api.post<{purchase_token:string;status:string}>(`/hotspot/public/${nasId}/`,{plan_id:Number(plan),phone_number:phone,request_id:requestId.current});setToken(data.purchase_token);setState(data.status);}catch(e){setError(apiError(e,'Could not request payment. Check your phone before retrying.'));}finally{setPending(false);}}}>
 <Field label="Internet plan"><select className={inputClass} required value={plan} disabled={!!token} onChange={e=>{setPlan(e.target.value);requestId.current=crypto.randomUUID();}}><option value="">Choose a plan</option>{offers.data?.plans.map(p=><option value={p.id} key={p.id}>{p.name} · {kes(p.price)} · {p.duration_seconds/60} min · {p.quota_bytes?bytes(p.quota_bytes):'Unlimited data'}</option>)}</select></Field>
 <Field label="M-Pesa phone number"><input className={inputClass} type="tel" inputMode="tel" placeholder="0712345678" pattern="(254|0)[17][0-9]{8}" required value={phone} disabled={!!token} onChange={e=>{setPhone(e.target.value);requestId.current=crypto.randomUUID();}}/></Field>
 <p className="text-sm">Approve the prompt on your phone. Enter your M-Pesa PIN only in the phone’s M-Pesa prompt. Keep this page open to receive your voucher.</p>
 <Button type="submit" disabled={pending||!!token||offers.isError||offers.isLoading||!offers.data?.purchases_enabled}>{pending?'Requesting…':token?'Waiting for payment…':'Request M-Pesa payment'}</Button>
 {token&&<p role="status">Payment state: {state}. Voucher issued only after confirmed successful payment.</p>}</form>}
 {code&&<section className="card-surface space-y-4 p-5" aria-label="Purchased voucher"><h2 className="text-xl font-bold">Your voucher is ready</h2><p className="break-all rounded-xl border p-3 font-mono font-bold">{code}</p><p>Return to the Wi-Fi login page. Enter this voucher code as both username and password. Validity starts on successful login; one device per voucher.</p><Button onClick={()=>void navigator.clipboard.writeText(code).catch(()=>setError('Copy unavailable. Select the code above.'))}>Copy voucher code</Button><Button color="light" onClick={()=>{setCode('');setState('');requestId.current=crypto.randomUUID();}}>Clear voucher from screen</Button></section>}
 <p className="text-sm text-slate-500">If payment succeeds but no code appears, contact your ISP with the receipt. Do not pay repeatedly.</p><Link to="/" className="font-semibold underline">Back to Lintech</Link></div></main>;
}
