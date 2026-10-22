import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import type { Paginated, Transaction } from "@/shared/types/api";
export function useCustomerPayments(id: string, page: number) {
  return useQuery({ queryKey: ["transactions", { customer_id: id, page, page_size: 10 }],
    queryFn: async () => (await api.get<Paginated<Transaction>>(API.billing.transactions, { params: { customer_id: id, page, page_size: 10 } })).data });
}
