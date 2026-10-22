import { CustomersManager } from "@/features/customers/CustomersManager";
import { PageHeader } from "@/shared/components/layout/PageHeader";
export function CustomersPage() {
  return <div className="space-y-5"><PageHeader title="Customers" description="Subscriber accounts, subscriptions and detected sessions." /><CustomersManager /></div>;
}
