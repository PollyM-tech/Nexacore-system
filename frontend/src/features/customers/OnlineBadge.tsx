type Props = { online: boolean; ready: boolean; hasPppoe: boolean; error?: boolean; loading?: boolean };
export function OnlineBadge({ online, ready, hasPppoe, error, loading }: Props) {
  const label = loading ? "Checking" : error ? "Unavailable" : ready ? hasPppoe && online ? "Online" : "Not detected" : "Checking";
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${label === "Online" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{label}</span>;
}
