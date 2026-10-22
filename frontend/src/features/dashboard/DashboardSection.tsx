import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ChartCard } from "@/shared/components/ui/ChartCard";

type Props = {
  title: string;
  description: string;
  to?: string;
  linkLabel?: string;
  loading: boolean;
  error: boolean;
  empty: boolean;
  emptyMessage: string;
  onRetry: () => void;
  children: ReactNode;
};

export function DashboardSection(props: Props) {
  return (
    <ChartCard title={props.title} subtitle={props.description}
      action={props.to ? <Link className="shrink-0 text-xs font-semibold text-brand-600 hover:underline" to={props.to}>{props.linkLabel} →</Link> : undefined}>
      {props.error ? (
        <div role="alert" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
          <p>This section is unavailable. Its current data could not be verified.</p>
          <button type="button" className="mt-2 font-semibold underline" onClick={props.onRetry}>Try again</button>
        </div>
      ) : props.loading ? (
        <div role="status" aria-label={`Loading ${props.title}`} className="space-y-3 py-3">
          {[0, 1, 2].map((i) => <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />)}
        </div>
      ) : props.empty ? <p className="py-8 text-center text-sm text-slate-500">{props.emptyMessage}</p> : props.children}
    </ChartCard>
  );
}
