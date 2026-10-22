import type { Column } from "@/shared/components/data/DataTable";
import { StatusBadge } from "@/shared/components/ui/StatusBadge";
import type { Package } from "@/shared/types/api";
import { kes } from "@/shared/utils/format";

export const billingCycles: Record<string, string> = { monthly: "Monthly", quarterly: "Quarterly", yearly: "Yearly" };
export const knownCount = (value: unknown): value is number => typeof value === "number" && Number.isInteger(value) && value >= 0;
export const packageColumns: Column<Package>[] = [
  { key: "name", header: "Package", render: (p) => <span className="font-medium text-slate-900 dark:text-white">{p.name}</span> },
  { key: "cycle", header: "Billing cycle", render: (p) => billingCycles[p.package_type ?? ""] ?? "Unknown" },
  { key: "speed", header: "Speed", render: (p) => <span className="whitespace-nowrap">{p.speed || "Unavailable"}</span> },
  { key: "price", header: "Price", align: "right", render: (p) => <span className="whitespace-nowrap font-semibold">{kes(p.price)}</span> },
  { key: "status", header: "Status", render: (p) => <StatusBadge status={p.is_active ? "active" : "inactive"} /> },
  { key: "customers", header: "Customers", align: "right", render: (p) => knownCount(p.customer_count) ? p.customer_count : "Unavailable" },
  { key: "radius", header: "RADIUS customers", align: "right", render: (p) => knownCount(p.radius_customer_count) ? p.radius_customer_count : "Unavailable" },
];
