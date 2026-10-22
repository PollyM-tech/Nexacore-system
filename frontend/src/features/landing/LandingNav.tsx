import { Brand } from "@/shared/components/layout/Brand";
import { ROUTES } from "@/shared/constants/routes";
const links = [["Features", "#features"], ["Pricing", "#pricing"], ["Workflow", "#workflow"], ["Contact", "#contact"]];

export function LandingNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 px-4 py-2 md:px-6">
        <a href="#" aria-label="Lintech home" className="shrink-0 focus-visible:outline-2 focus-visible:outline-brand-300"><Brand /></a>
        <nav aria-label="Public navigation" className="order-3 flex w-full items-center justify-between gap-3 overflow-x-auto py-3 text-sm font-bold text-slate-600 md:order-none md:w-auto md:gap-6 md:py-0">
          {links.map(([label, href]) => <a key={href} href={href} className="whitespace-nowrap rounded hover:text-ink-900 focus-visible:outline-2 focus-visible:outline-brand-300">{label}</a>)}
        </nav>
        <div className="flex flex-wrap items-center gap-2">
          <a href={ROUTES.portalLogin} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-bold text-ink-900 hover:bg-slate-50">Customer Login</a>
          <a href={ROUTES.login} className="rounded-xl bg-accent-600 px-3 py-2 text-sm font-bold text-white hover:bg-accent-700">Admin Login</a>
        </div>
      </div>
    </header>
  );
}
