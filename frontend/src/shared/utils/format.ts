const kesNumber = new Intl.NumberFormat("en-KE", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const compactKesNumber = new Intl.NumberFormat("en-KE", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function monetaryAmount(value: unknown): number | null {
  if ((typeof value !== "number" && typeof value !== "string") ||
      (typeof value === "string" && value.trim() === "")) return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
}

/** Display Kenyan shillings without conversion; invalid/missing data stays unavailable. */
export function formatKES(value: unknown): string {
  const amount = monetaryAmount(value);
  return amount === null ? "—" : `KES ${kesNumber.format(amount).replace(/\.00$/, "")}`;
}

// Existing call sites share the same formatter, including customer portal screens.
export const kes = formatKES;
export const money = formatKES;

export function compactKes(value: unknown): string {
  const amount = monetaryAmount(value);
  return amount === null ? "—" : `KES ${compactKesNumber.format(amount)}`;
}
export const compact = compactKes;

export function bytes(value?: number | string): string {
  let n = Number(value) || 0;
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function bitrate(bitsPerSec: number): string {
  let n = Math.max(0, bitsPerSec);
  const units = ["bps", "Kbps", "Mbps", "Gbps"];
  let i = 0;
  while (n >= 1000 && i < units.length - 1) {
    n /= 1000;
    i += 1;
  }
  return `${n.toFixed(i >= 2 ? 2 : 0)} ${units[i]}`;
}


export function duration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const minutes = Math.floor(seconds / 60);
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  return `${days ? `${days}d ` : ""}${hours}h ${minutes % 60}m`;
}

export function dateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("en-KE", {
    dateStyle: "medium", timeStyle: "short",
  });
}
