import { useState } from "react";
import { Icon } from "@/shared/components/icons/Icon";

type Props = { id: string; label: string; value: string; onChange: (value: string) => void; required?: boolean };
export function PasswordInput({ id, label, value, onChange, required = true }: Props) {
  const [visible, setVisible] = useState(false);
  return <div>
    <label htmlFor={id} className="mb-1.5 block text-sm font-medium">{label}{required ? " *" : ""}</label>
    <div className="relative">
      <input id={id} type={visible ? "text" : "password"} autoComplete="new-password" required={required}
        maxLength={253} value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 pr-12 text-sm focus:border-brand-500 focus:outline-2 focus:outline-brand-500 dark:border-slate-700 dark:bg-ink-800" />
      <button type="button" aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible((v) => !v)}
        className="absolute right-1 top-1 rounded-lg p-2 text-slate-500 focus-visible:outline-2 focus-visible:outline-brand-500">
        <Icon name={visible ? "eyeOff" : "eye"} className="h-4 w-4" />
      </button>
    </div>
  </div>;
}
