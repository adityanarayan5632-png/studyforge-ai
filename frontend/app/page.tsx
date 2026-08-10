import { PublicNavbar } from "@/components/layout/PublicNavbar";
import { Footer } from "@/components/layout/Footer";
import { Hero } from "@/components/landing/Hero";
import { FeatureGrid } from "@/components/landing/FeatureGrid";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { PricingTiers } from "@/components/landing/PricingTiers";
import { CTASection } from "@/components/landing/CTASection";

export default function LandingPage() {
  return (
    <>
      <PublicNavbar />
      <main className="flex-1">
        <Hero />
        <FeatureGrid />
        <HowItWorks />
        <PricingTiers />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
