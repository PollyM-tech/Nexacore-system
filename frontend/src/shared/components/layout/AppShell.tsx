import { Drawer, DrawerHeader, DrawerItems } from "flowbite-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Brand } from "@/shared/components/layout/Brand";
import { SidebarNav } from "@/shared/components/layout/SidebarNav";
import { TopBar } from "@/shared/components/layout/TopBar";

export function AppShell() {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="navy-sidebar hidden border-r border-slate-200/70 bg-ink-900 text-white lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col dark:border-slate-800 dark:bg-ink-900">
        <div className="flex shrink-0 items-center gap-3 border-b border-slate-200/70 px-5 py-3 dark:border-slate-800">
          <Brand size="sidebar" />
          <p className="text-xs font-semibold leading-relaxed text-slate-200">ISP Management</p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <SidebarNav />
        </div>
        <div className="shrink-0 border-t border-slate-100 px-5 py-4 text-xs text-slate-300 dark:border-slate-800">Lintech Telecom · ISP workspace</div>
      </aside>

      <Drawer open={open} onClose={() => setOpen(false)} className="lg:hidden">
        <DrawerHeader title="Lintech navigation" titleIcon={() => null} />
        <DrawerItems>
          <SidebarNav onNavigate={() => setOpen(false)} />
        </DrawerItems>
      </Drawer>

      <div className="flex min-h-screen min-w-0 flex-col">
        <TopBar onMenuClick={() => setOpen(true)} />
        <main className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl animate-rise">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
