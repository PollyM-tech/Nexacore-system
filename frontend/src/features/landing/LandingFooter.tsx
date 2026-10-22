import { Brand } from "@/shared/components/layout/Brand";
import { ROUTES } from "@/shared/constants/routes";

export function LandingFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-4 py-10 md:flex-row md:px-6">
        <Brand size="footer" />
        <nav className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-600">
          <a href="#features" className="hover:text-ink-900">Features</a>
          <a href="#pricing" className="hover:text-ink-900">Pricing</a>
          <a href="#workflow" className="hover:text-ink-900">Workflow</a>
          <a href="#contact" className="hover:text-ink-900">Contact</a>
          <a href={ROUTES.login} className="hover:text-ink-900">Admin Login</a>
          <a href={ROUTES.portalLogin} className="hover:text-ink-900">Customer Login</a>
        </nav>
        <p className="text-sm text-slate-600">© {new Date().getFullYear()} Lintech</p>
      </div>
    </footer>
  );
}
