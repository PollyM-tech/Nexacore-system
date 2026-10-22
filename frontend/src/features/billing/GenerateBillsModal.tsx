import { Alert, Select, TextInput } from "flowbite-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { FormField } from "@/shared/components/ui/FormField";
import { FormModal } from "@/shared/components/ui/FormModal";
import { apiError } from "@/shared/utils/apiError";

const MONTHS = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];
const now = new Date();

export function GenerateBillsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [year, setYear] = useState(String(now.getFullYear()));
  const [done, setDone] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () => api.post(API.billing.generateMonthlyBills, {
      billing_month: Number(month), billing_year: Number(year),
    }).then((r) => r.data),
    onSuccess: (data: { bills_created?: number }) => {
      ["monthly-bills", "dashboard-summary", "customer-detail", "customers"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      setDone(typeof data.bills_created === "number" ? `${data.bills_created} monthly bills generated.` : "Generation completed; count unavailable.");
    },
  });

  const close = () => { if (!mut.isPending) { setDone(null); mut.reset(); onClose(); } };

  return (
    <FormModal open={open} onClose={close} title="Generate monthly bills"
      onSubmit={(e) => { e.preventDefault(); if (window.confirm(`Generate monthly bills for ${MONTHS[Number(month)-1]} ${year}? Existing bills are skipped.`)) mut.mutate(); }} submitting={mut.isPending}
      submitLabel="Generate" error={mut.isError ? apiError(mut.error) : null}>
      {done ? <Alert color="success" className="sm:col-span-2">{done}</Alert> : null}
      <FormField label="Billing month" htmlFor="generatebillsmodal-billing-month">
        <Select id="generatebillsmodal-billing-month" value={month} onChange={(e) => setMonth(e.target.value)}>
          {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
        </Select>
      </FormField>
      <FormField label="Billing year" htmlFor="generatebillsmodal-billing-year">
        <TextInput id="generatebillsmodal-billing-year" type="number" value={year} onChange={(e) => setYear(e.target.value)} />
      </FormField>
    </FormModal>
  );
}
