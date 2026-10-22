import type { ReactNode } from "react";
import { Brand } from "@/shared/components/layout/Brand";
import { Icon } from "@/shared/components/icons/Icon";

const HIGHLIGHTS = [
  "Realtime PPPoE & bandwidth control",
  "Automated monthly billing runs",
  "Customer support ticketing",
];

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-slate-200 bg-white p-12 text-ink-900 lg:flex">
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-brand-50 blur-3xl" />
        <div className="absolute -bottom-24 -left-10 h-72 w-72 rounded-full bg-accent-100/40 blur-3xl" />
        <div className="relative z-10"><Brand size="login" /></div>
        <div className="relative z-10 max-w-md py-10">
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-brand-700">Lintech ISP Management</p>
          <h2 className="text-3xl font-bold leading-tight">Run your ISP from one calm dashboard.</h2>
          <ul className="mt-8 space-y-4">
            {HIGHLIGHTS.map((h) => (
              <li key={h} className="flex items-center gap-3 text-slate-600">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-100 text-accent-700">
                  <Icon name="bolt" className="h-3.5 w-3.5" />
                </span>
                {h}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative z-10 text-sm text-slate-500">© {new Date().getFullYear()} Lintech</p>
      </div>
      <div className="flex items-center justify-center bg-white p-6 dark:bg-ink-950">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 sm:p-9 dark:border-slate-700 dark:bg-ink-900 dark:shadow-none"><div className="mb-6 flex justify-center lg:hidden"><Brand size="footer" /></div>{children}</div>
      </div>
    </div>
  );
}
