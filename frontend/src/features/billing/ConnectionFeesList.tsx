import { useState } from "react";
import { Button, TextInput } from "flowbite-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminResourceList } from "@/features/admin/AdminResourceList";
import { CustomerSearchSelect } from "@/features/payments/CustomerSearchSelect";
import { FormModal } from "@/shared/components/ui/FormModal";
import { billColumns } from "./billingColumns";
import { API } from "@/shared/api/endpoints";
import { api } from "@/shared/api/client";
import { apiError } from "@/shared/utils/apiError";
import type { MonthlyBill } from "@/shared/types/api";
export function ConnectionFeesList() {
  const [open,setOpen]=useState(false);const [customer,setCustomer]=useState("");const [amount,setAmount]=useState("");const qc=useQueryClient();
  const create=useMutation({mutationFn:()=>api.post(API.billing.generateConnectionFee,{customer_id:customer,total_amount:amount}),onSuccess:()=>{setOpen(false);setAmount("");for(const key of ["connection-fees","customer-detail","customers","dashboard-summary"])void qc.invalidateQueries({queryKey:[key]});}});
  return <><AdminResourceList<MonthlyBill> queryKey="connection-fees" url={API.billing.connectionFees} columns={billColumns} rowKey={r=>r.id} emptyTitle="No connection fees" emptyDescription="Connection-fee invoices appear here." toolbarAction={<Button onClick={()=>{create.reset();setOpen(true);}}>Create connection fee</Button>} />
    <FormModal open={open} onClose={()=>{if(!create.isPending)setOpen(false);}} title="Create connection-fee invoice" submitLabel="Create invoice" submitting={create.isPending} error={create.isError?apiError(create.error):null} onSubmit={e=>{e.preventDefault();if(customer && Number(amount)>0)create.mutate();}}>
      <div className="sm:col-span-2"><CustomerSearchSelect value={customer} onChange={setCustomer} /></div><label htmlFor="connection-fee-amount">Billed amount (KES)</label><TextInput id="connection-fee-amount" type="number" required min="0.01" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)} />
    </FormModal></>;
}
