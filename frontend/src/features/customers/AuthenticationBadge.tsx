export function AuthenticationBadge({ mode }: { mode?: string | null }) {
  const label = mode === "radius" ? "RADIUS" : mode === "local_secret" ? "Local secret" : "Unconfigured / Unknown";
  return <span className="inline-flex whitespace-nowrap rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">{label}</span>;
}
