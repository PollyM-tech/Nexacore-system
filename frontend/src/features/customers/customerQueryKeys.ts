import type { QueryClient } from "@tanstack/react-query";
export const customerKeys = {
  detail: (id?: string) => ["customer-detail", id] as const,
  live: (id: string) => ["customer-live", id] as const,
  summary: (id: string) => ["customer-radius-summary", id] as const,
  sessions: (id: string) => ["customer-radius-sessions", id] as const,
};
export async function invalidateCustomer(client: QueryClient, id?: string) {
  const keys: ReadonlyArray<readonly unknown[]> = [
    ["customers"], ["dashboard-summary"], ["customers-online"], ["radius-active-sessions"],
    ...(id ? [customerKeys.detail(id), customerKeys.live(id), customerKeys.summary(id), customerKeys.sessions(id)] : []),
  ];
  await Promise.all(keys.map((queryKey) => client.invalidateQueries({ queryKey })));
}
