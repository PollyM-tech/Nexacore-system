import { LandingWorkflow } from "@/features/landing/LandingWorkflow";
import { LandingContact } from "@/features/landing/LandingContact";
import { LandingNav } from "@/features/landing/LandingNav";
import { LandingHero } from "@/features/landing/LandingHero";
import { LandingFeatures } from "@/features/landing/LandingFeatures";
import { LandingPricing } from "@/features/landing/LandingPricing";
import { LandingFooter } from "@/features/landing/LandingFooter";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white font-bold text-ink-900">
      <LandingNav />
      <main>
        <LandingHero />
        <LandingFeatures />
        <LandingPricing />
        <LandingWorkflow />
        <LandingContact />
      </main>
      <LandingFooter />
    </div>
  );
}
