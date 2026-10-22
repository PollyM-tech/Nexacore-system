import { Icon } from "@/shared/components/icons/Icon";
import type { IconName } from "@/shared/components/icons/Icon";

const FEATURES: { icon: IconName; title: string; text: string }[] = [
  { icon: "users", title: "Subscriber operations", text: "Manage PPPoE customers, packages, and connection credentials. Hotspot capabilities are being completed." },
  { icon: "router", title: "Network visibility", text: "Work with MikroTik routers, live session observations, and RADIUS accounting, with clear data-source status." },
  { icon: "billing", title: "Transparent billing", text: "Review invoices, payment history, outstanding amounts, and supported M-Pesa workflows." },
  { icon: "ticket", title: "Support workflows", text: "Track customer tickets, reply to issues, and send notifications through configured SMS providers." },
];

export function LandingFeatures() {
  return (
    <section id="features" className="mx-auto max-w-6xl scroll-mt-32 px-4 py-20 md:scroll-mt-24 md:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-bold text-ink-900 md:text-4xl">Everything you need, nothing you don't</h2>
        <p className="mt-3 text-slate-600">A shared operational workspace for ISP teams.</p>
      </div>
      <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-2xl border border-slate-200 bg-white p-6 transition hover:border-brand-500/40 hover:bg-slate-50">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/20 text-brand-700">
              <Icon name={f.icon} />
            </span>
            <h3 className="mt-4 font-bold text-ink-900">{f.title}</h3>
            <p className="mt-1.5 text-sm text-slate-600">{f.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
