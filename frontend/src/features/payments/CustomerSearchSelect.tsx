import { Button, Select, TextInput } from "flowbite-react";
import { useId, useState } from "react";
import { API } from "@/shared/api/endpoints";
import { useAdminOptions } from "@/features/admin/useAdminOptions";
import type { Customer } from "@/shared/types/api";
export function CustomerSearchSelect({value,onChange}: {value:string;onChange:(id:string)=>void}) {
  const query = useAdminOptions<Customer>("customers",API.customers);
  const [search,setSearch] = useState("");
  const id=useId();
  const rows=(query.data ?? []).filter(c=>c.customer_id === value || `${c.customer_id} ${c.customer_name} ${c.phone_number}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="space-y-2">
    <label htmlFor={`${id}-search`} className="text-sm">Find customer</label><TextInput id={`${id}-search`} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Name, customer ID or phone" />
    <label htmlFor={id} className="text-sm">Selected customer</label><Select id={id} required disabled={query.isLoading || query.isError} value={value} onChange={e=>onChange(e.target.value)}><option value="">{query.isLoading ? "Loading customers…" : "Choose a customer"}</option>{rows.map(c=><option key={c.id} value={c.customer_id}>{c.customer_id} · {c.customer_name}</option>)}</Select>
    {query.isError && <div role="alert">Customer list unavailable. <Button size="xs" color="light" onClick={()=>void query.refetch()}>Retry</Button></div>}
  </div>;
}
