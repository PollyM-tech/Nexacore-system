import { TextInput } from "flowbite-react";
import { useState } from "react";
import { Icon } from "@/shared/components/icons/Icon";
import { FormField } from "@/shared/components/ui/FormField";
import type { SmsProviderField } from "@/shared/types/api";

const JSON_KEYS = ["headers", "payload"];

type Props = { field: SmsProviderField; value: string; onChange: (v: string) => void };

export function GatewayField({ field, value, onChange }: Props) {
  const [show, setShow] = useState(false);
  const isJson = JSON_KEYS.includes(field.key);
  return (
    <FormField label={field.label} htmlFor={`provider-${field.key}`} required={field.required} full={isJson}>
      <TextInput id={`provider-${field.key}`} type={!show && (field.secret || isJson || field.key === "url") ? "password" : "text"} required={field.required}
        value={value} onChange={(e) => onChange(e.target.value)} autoComplete="new-password"
        rightIcon={() => <button type="button" aria-label={show ? "Hide credential" : "Show credential"} onClick={()=>setShow(s=>!s)} className="pointer-events-auto text-slate-400"><Icon name={show?"eyeOff":"eye"} className="h-4 w-4" /></button>} />
    </FormField>
  );
}
