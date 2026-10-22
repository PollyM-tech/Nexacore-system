import { Tabs, TabItem } from "flowbite-react";
import { MonthlyBillsList } from "@/features/billing/MonthlyBillsList";
import { ConnectionFeesList } from "./ConnectionFeesList";
import { PaymentsHistory } from "@/features/payments/PaymentsHistory";

export function BillingTabs() {
  return (
    <Tabs variant="underline" aria-label="Billing tabs">
      <TabItem active title="Monthly Bills">
        <MonthlyBillsList />
      </TabItem>
      <TabItem title="Connection fees"><ConnectionFeesList /></TabItem>
      <TabItem title="Payments">
        <PaymentsHistory />
      </TabItem>
    </Tabs>
  );
}
