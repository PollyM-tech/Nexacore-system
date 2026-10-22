import { DarkThemeToggle } from "flowbite-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Icon } from "@/shared/components/icons/Icon";
import { UserMenu } from "@/shared/components/layout/UserMenu";
import { MAIN_NAV } from "@/shared/constants/nav";

type Props = { onMenuClick: () => void };
export function TopBar({ onMenuClick }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const current = [...MAIN_NAV].sort((a,b) => b.to.length-a.to.length).find(item => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`));
  return (
    <header className="sticky top-0 z-20 flex min-h-20 items-center justify-between gap-3 border-b border-slate-200/70 bg-white/95 px-4 py-3 backdrop-blur-xl md:px-6 dark:border-slate-700/60 dark:bg-ink-900/95">
      <div className="flex min-w-0 items-center gap-3">
        <button type="button" onClick={onMenuClick} className="rounded-xl border border-slate-200 p-2 text-slate-600 lg:hidden dark:border-slate-700 dark:text-slate-200" aria-label="Open menu"><Icon name="menu" className="h-5 w-5" /></button>
        <div className="min-w-0"><p className="truncate text-[11px] font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-300">Lintech<span className="hidden sm:inline"> ISP Management</span></p><p className="mt-1 truncate text-sm font-semibold text-slate-900 dark:text-white">{current?.label || "ISP workspace"}</p></div>
      </div>
      <div className="flex shrink-0 items-center gap-2 md:gap-4">
        <form role="search" className="relative hidden md:block" onSubmit={e=>{e.preventDefault();navigate(`/admin/customers${search.trim()?`?q=${encodeURIComponent(search.trim())}`:""}`);setSearch("");}}><label htmlFor="workspace-customer-search" className="sr-only">Search customers</label><input id="workspace-customer-search" type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Find a customer…" className="w-44 rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-3 pr-10 text-sm focus:border-brand-500 focus:bg-white xl:w-60 dark:border-slate-700 dark:bg-ink-950" /><button type="submit" aria-label="Search customers" className="absolute right-2 top-2.5 rounded p-0.5 text-slate-500"><Icon name="search" className="h-4 w-4" /></button></form>
        <Link to="/admin/customers" aria-label="Find customers" className="rounded-lg p-2 text-slate-500 md:hidden"><Icon name="search" className="h-5 w-5" /></Link>

        <DarkThemeToggle className="rounded-lg" />
        <UserMenu />
      </div>
    </header>
  );
}
