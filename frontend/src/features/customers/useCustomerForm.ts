import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { ROUTES } from "@/shared/constants/routes";
import type { CustomerDetail } from "@/shared/types/api";
import { useCustomerOptions } from "./useCustomerOptions";
import { customerKeys, invalidateCustomer } from "./customerQueryKeys";
import { useCustomerDetail } from "./detail/useCustomerDetail";

const EMPTY = {
  customer_id: "", customer_name: "", phone_number: "", phone_number2: "", nid: "", address: "",
  zone: "", package: "", billing_day: "1", authentication_mode: "radius", router: "",
  profile_name: "", pppoe_name: "", pppoe_pass: "",
};
type FormState = typeof EMPTY;
export function useCustomerForm() {
  const { customerId } = useParams();
  const isEdit = !!customerId;
  const navigate = useNavigate();
  const client = useQueryClient();
  const options = useCustomerOptions();
  const detail = useCustomerDetail(customerId);
  const [f, setF] = useState<FormState>({ ...EMPTY });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ id: string; username?: string; mode?: string | null } | null>(null);
  const set = (key: keyof FormState) => (e: { target: { value: string } }) => setF((prev) => ({ ...prev, [key]: e.target.value }));
  const setPassword = (value: string) => setF((prev) => ({ ...prev, pppoe_pass: value }));
  useEffect(() => {
    if (isEdit && detail.data) {
      const d = detail.data;
      setF({ ...EMPTY, customer_id: d.customer_id, customer_name: d.customer_name, phone_number: d.phone_number,
        phone_number2: d.phone_number2 ?? "", nid: d.nid ?? "", address: d.address,
        zone: d.zone ? String(d.zone) : "", package: d.package ? String(d.package) : "",
        authentication_mode: d.router_info?.authentication_mode ?? "local_secret",
      });
    }
  }, [isEdit, detail.data]);
  const radius = f.authentication_mode === "radius";
  const profiles = useQuery({
    queryKey: ["router-profiles", f.router],
    queryFn: async () => (await api.get<{ profiles?: string[] }>(API.routerProfiles(f.router))).data.profiles ?? [],
    enabled: !isEdit && !radius && !!f.router,
    retry: false,
  });
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    setError(null);
    if (!isEdit && (radius || !!f.router) && !f.pppoe_pass.trim()) {
      setError("Enter a PPPoE password containing at least one non-whitespace character."); return;
    }
    if (radius && (!f.package || (!isEdit && !f.router))) {
      setError("RADIUS requires an active package and a router."); return;
    }
    if (!isEdit && !radius && f.router && !f.pppoe_name.trim()) {
      setError("Enter a PPPoE username when provisioning a local-secret connection."); return;
    }
    setSubmitting(true);
    try {
      // Credential requests deliberately bypass useMutation: mutation variables
      // are retained by TanStack Query. Passwords stay only in this form/request.
      if (isEdit) {
        await api.patch(API.customerDetail(customerId!), {
          customer_name: f.customer_name, phone_number: f.phone_number,
          phone_number2: f.phone_number2 || null, nid: f.nid || null, address: f.address,
          zone: Number(f.zone), package: f.package ? Number(f.package) : null,
        });
        void invalidateCustomer(client, customerId);
        navigate(`${ROUTES.customers}/${encodeURIComponent(customerId!)}`);
      } else {
        const connection = radius
          ? { authentication_mode: "radius", router_id: Number(f.router), pppoe_pass: f.pppoe_pass }
          : { authentication_mode: "local_secret", router_id: f.router ? Number(f.router) : null,
              ...(f.router ? { pppoe_name: f.pppoe_name, pppoe_pass: f.pppoe_pass, profile_name: f.profile_name || undefined } : {}) };
        const { data } = await api.post<Pick<CustomerDetail, "customer_id" | "router_info">>(API.customers, {
          customer_id: f.customer_id || undefined, customer_name: f.customer_name, phone_number: f.phone_number,
          phone_number2: f.phone_number2 || null, nid: f.nid || null, address: f.address,
          zone_id: Number(f.zone), package_id: f.package ? Number(f.package) : null,
          billing_day: Number(f.billing_day), ...connection,
        });
        setCreated({ id: data.customer_id, username: data.router_info?.pppoe_name, mode: data.router_info?.authentication_mode });
        setPassword("");
        void invalidateCustomer(client, data.customer_id);
      }
    } catch (err) {
      // Do not retain Axios errors/config (which contain the request password),
      // or echo arbitrary backend exception text in credential flows.
      const data = (err as { response?: { status?: number; data?: unknown } })?.response;
      if (data?.status === 400 && data.data && typeof data.data === "object") {
        const fields = Object.keys(data.data).filter((key) => ["customer_id", "customer_name", "nid", "phone_number", "phone_number2", "address", "zone", "zone_id", "package", "package_id", "router_id", "pppoe_name", "pppoe_pass", "billing_day", "router_info"].includes(key));
        setError(fields.length ? `Could not save. Check: ${fields.map((key) => key.replaceAll("_", " ")).join(", ")}. Package must be active for RADIUS; connection provisioning must succeed.` : "Unable to save this customer. Verify the details and try again.");
      } else setError("Unable to save this customer. Check access and connectivity, then try again.");
    }
    finally { setSubmitting(false); }
  };
  const finish = () => { setPassword(""); if (created) navigate(`${ROUTES.customers}/${encodeURIComponent(created.id)}`); };
  return { f, set, setPassword, radius, isEdit, options, submit, submitting, error, created, finish,
    detailLoading: isEdit && detail.isLoading, detailError: isEdit && detail.isError,
    retryDetail: () => { void client.invalidateQueries({ queryKey: customerKeys.detail(customerId) }); },
    profiles: profiles.data ?? [], profilesLoading: profiles.isFetching, profilesError: profiles.isError,
    cancel: () => { setPassword(""); navigate(ROUTES.customers); },
  };
}
