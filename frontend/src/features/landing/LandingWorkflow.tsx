const steps = [
  { title: "Discuss your operation", text: "Tell us about your services, network size, existing equipment, and onboarding needs." },
  { title: "Agree on your deployment", text: "Review the available capabilities and receive a quote tailored to your ISP, including any hotspot rollout requirements." },
  { title: "Bring your team into Lintech", text: "Plan onboarding and manage subscribers, billing, payments, and operational tools in a shared workspace." },
];
export function LandingWorkflow() {
  return <section id="workflow" aria-labelledby="workflow-title" className="mx-auto max-w-6xl scroll-mt-32 px-4 py-20 md:scroll-mt-24 md:px-6"><p className="text-sm font-bold uppercase tracking-widest text-brand-700">A practical workflow</p><h2 id="workflow-title" className="mt-3 text-3xl font-bold md:text-4xl">From your requirements to daily operations.</h2><ol className="mt-10 grid gap-6 md:grid-cols-3">{steps.map((step, index) => <li key={step.title} className="rounded-2xl border border-slate-200 bg-white p-6"><span className="text-sm font-bold text-brand-700">0{index + 1}</span><h3 className="mt-4 text-lg font-bold">{step.title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{step.text}</p></li>)}</ol></section>;
}
