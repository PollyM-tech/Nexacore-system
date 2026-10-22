import { SchedulerTaskList } from "@/features/scheduler/SchedulerTaskList";
import { PageHeader } from "@/shared/components/layout/PageHeader";

export function SchedulerPage() {
  return (
    <>
      <PageHeader title="Scheduler" description="Automated billing and network maintenance jobs." />
      <p className="mb-4 text-sm text-slate-500">Read-only global schedule visibility. Schedule changes are restricted to Lintech platform administrators. Last-run results and run-now actions are not exposed here.</p>
      <SchedulerTaskList />
    </>
  );
}
