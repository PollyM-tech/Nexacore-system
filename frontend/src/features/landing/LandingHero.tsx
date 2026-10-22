import { ROUTES } from "@/shared/constants/routes";

export function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-white">
      <div aria-hidden="true" className="absolute -top-32 left-1/2 h-[32rem] w-[min(48rem,100%)] -translate-x-1/2 rounded-full bg-accent-100/70 blur-3xl" />
      <div aria-hidden="true" className="absolute right-0 top-20 h-72 w-72 rounded-full bg-accent-100/50 blur-3xl" />
      <div className="relative mx-auto max-w-5xl px-4 py-16 text-center md:py-24">
        <p className="inline-flex rounded-full border border-accent-500/20 bg-accent-50 px-4 py-1.5 text-sm font-bold text-ink-900">Modern ISP operations platform</p>
        <h1 className="mt-6 text-lg font-extrabold leading-[1.08] tracking-tight text-ink-900 sm:text-2xl md:text-3xl lg:text-4xl">Run your ISP from one <span>smart command center.</span></h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg font-bold leading-relaxed text-ink-900/80 md:text-xl">Lintech helps ISP teams manage PPPoE subscribers, payments, billing, tickets, routers, sessions, and daily network operations in one workspace, with hotspot capabilities being completed for hotspot-focused and combined deployments.</p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <a href={ROUTES.login} className="w-full rounded-xl bg-accent-600 px-7 py-3 text-base font-bold text-white transition hover:bg-accent-700 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-300 sm:w-auto">Staff Login</a>
          <a href="#pricing" className="w-full rounded-xl border border-slate-300 bg-white px-7 py-3 text-base font-bold text-ink-900 transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-300 sm:w-auto">View Pricing</a>
        </div>
      </div>
    </section>
  );
}
