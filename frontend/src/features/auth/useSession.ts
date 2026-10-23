import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";

type User = { email?: string; pk?: number; username?: string; first_name?: string; last_name?: string; is_platform_admin?: boolean; membership?: { role: string; role_label: string; organization: { id: number; name: string; slug?: string } } | null };

export function useSession() {
  const query = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      const { data } = await api.get<User>(API.auth.user);
      return data;
    },
    retry: false,
  });

  return {
    user: query.data,
    isLoading: query.isLoading,
    isAuthenticated: !!query.data && !query.isError,
    refetch: query.refetch,
  };
}
