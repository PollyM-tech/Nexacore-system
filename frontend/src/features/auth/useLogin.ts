import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";
import { ROUTES } from "@/shared/constants/routes";

type Credentials = { email: string; password: string };

export function useLogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  return useMutation({
    gcTime: 0,
    mutationFn: async (body: Credentials) => {
      await api.post(API.auth.login, body);
    },
    onSuccess: async () => {
      await queryClient.cancelQueries({ queryKey: ["platform"] });
      queryClient.removeQueries({ queryKey: ["platform"] });
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      const target = (location.state as { returnTo?: unknown } | null)?.returnTo;
      navigate(typeof target === "string" && /^\/superadmin(?:\/|$)/.test(target) && !target.includes("\\") ? target : ROUTES.dashboard);
    },
  });
}
