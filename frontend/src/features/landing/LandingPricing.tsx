import { Icon } from "@/shared/components/icons/Icon";

const PLANS = [
  {
    name: "Hotspot Only", price: "1,500",
    description: "For hotspot operators managing users, payments, and access.",
    features: ["Hotspot customer management", "Packages and service access", "Payment and expiry tracking", "M-Pesa workflows", "Operational visibility"],
  },
  {
    name: "PPPoE Only", price: "2,000",
    description: "Reliable PPPoE subscriber management and network control.",
    features: ["PPPoE customer management", "FreeRADIUS authentication", "MikroTik integration", "Package and speed management", "M-Pesa payment workflows", "Billing and payment history", "Session and accounting visibility"],
  },
  {
    name: "Full Stack", price: "3,000",
    description: "One workspace for subscribers, billing, and network operations.",
    features: ["PPPoE and hotspot operations", "Customer and package management", "Billing and M-Pesa", "MikroTik routers", "Live sessions", "Tickets and SMS", "OLT / ONU operations", "Reporting and operational tools"],
  },
];
const quoteClass = "block rounded-xl px-4 py-2.5 text-center text-sm font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-300";

export function LandingPricing() {
  return (
    <section id="pricing" aria-labelledby="pricing-title" className="mx-auto max-w-5xl scroll-mt-32 px-4 py-12 md:scroll-mt-24 md:px-6">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-bold uppercase tracking-widest text-brand-700">Transparent pricing</p>
        <h2 id="pricing-title" className="mt-3 text-3xl font-bold text-ink-900 md:text-4xl">Plans visible <span className="text-accent-600">at a glance.</span></h2>
        <p className="mt-4 leading-relaxed text-slate-600">Clear starting prices for different ISP operations. Final pricing can vary depending on subscriber count, service type, onboarding requirements, and deployment size.</p>
      </div>
      <div className="mt-7 grid gap-4 lg:grid-cols-3">
        {PLANS.map((plan, index) => (
          <article key={plan.name} className={`flex min-w-0 flex-col rounded-2xl border p-4 sm:p-5 shadow-sm ${index === 1 ? "border-ink-900 bg-ink-900 text-white" : "border-slate-200 bg-white"}`}>
            <h3 className={`text-lg font-bold ${index === 1 ? "text-white" : "text-ink-900"}`}>{plan.name}</h3>
            <p aria-label={`From KES ${plan.price} / month`} className={`mt-3 ${index === 1 ? "text-white" : "text-ink-900"}`}><span className={`text-xs font-bold ${index === 1 ? "text-slate-200" : "text-brand-700"}`}>From </span>{" "}<span className="text-2xl font-extrabold tracking-tight">KES {plan.price}</span>{" "}<span className="ml-1 whitespace-nowrap text-xs">/ month</span></p>
            <p className={`mt-3 text-xs leading-relaxed ${index === 1 ? "text-slate-200" : "text-slate-600"}`}>{plan.description}</p>
            <ul className={`mb-5 mt-4 space-y-1.5 text-xs leading-5 ${index === 1 ? "text-slate-200" : "text-slate-600"}`}>
              {plan.features.map(feature => <li key={feature} className="flex items-start gap-2.5"><Icon name="check" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-500" /><span>{feature}</span></li>)}
            </ul>
            <a href="#contact" className={`${quoteClass} mt-auto ${index === 1 ? "bg-accent-600 text-white hover:bg-accent-700" : "border border-slate-300 text-ink-900 hover:bg-slate-50"}`}>Request Quote<span className="sr-only"> for {plan.name}</span></a>
          </article>
        ))}
      </div>
      <div className="mx-auto mt-6 max-w-3xl space-y-3 text-center text-sm leading-relaxed text-slate-600">
        <p>Final pricing depends on the number of active subscribers, service type, onboarding requirements, and deployment size.</p>
        <p>For larger networks, custom deployments, or enterprise requirements, contact us for a tailored quote.</p>
        <a href="#contact" className={`${quoteClass} mx-auto mt-5 w-fit bg-accent-600 text-white hover:bg-accent-700`}>Request Quote</a>
      </div>
      <aside className="mt-7 flex flex-col items-start justify-between gap-6 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 md:flex-row md:items-center">
        <div className="max-w-2xl"><h3 className="text-lg font-bold text-ink-900">Enterprise</h3><p className="mt-2 leading-relaxed text-slate-600">For larger ISPs, multi-site deployments, custom integrations, onboarding, or dedicated operational requirements.</p></div>
        <a href="#contact" className={`${quoteClass} shrink-0 border border-slate-300 text-ink-900 hover:bg-slate-50`}>Talk to Us</a>
      </aside>
    </section>
  );
}
