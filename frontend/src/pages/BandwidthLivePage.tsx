import { LiveUsageView } from "@/features/bandwidth/LiveUsageView";
import { PageHeader } from "@/shared/components/layout/PageHeader";

export function BandwidthLivePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Sessions"
        description="Separate RouterOS observations and RADIUS accounting for source-aware connection monitoring."
      />
      <LiveUsageView />
    </div>
  );
}
