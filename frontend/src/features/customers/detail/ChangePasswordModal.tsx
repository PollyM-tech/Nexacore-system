import { useState } from "react";
import { Modal, ModalHeader, ModalBody, Button, Alert } from "flowbite-react";
import { useQueryClient } from "@tanstack/react-query";
import { PasswordInput } from "../PasswordInput";
import { invalidateCustomer } from "../customerQueryKeys";
import { api } from "@/shared/api/client";
import { API } from "@/shared/api/endpoints";

export function ChangePasswordModal({ customerId, onClose }: { customerId: string; onClose: () => void }) {
  const client = useQueryClient();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [warning, setWarning] = useState(false);
  const close = () => { if (pending) return; setPassword(""); setConfirm(""); onClose(); };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pending) return;
    if (!password.trim() || password !== confirm) { setError("Enter a non-empty password and an identical confirmation."); return; }
    setError(""); setPending(true);
    try {
      // Do not use a cached mutation for credentials, including its variables/errors.
      const { data } = await api.post<{ warning?: string }>(API.customerConnection(customerId), { pppoe_pass: password });
      setPassword(""); setConfirm(""); setWarning(!!data.warning); setSuccess(true);
      void invalidateCustomer(client, customerId);
    } catch { setPassword(""); setConfirm(""); setError("Password change could not be confirmed. Check your permissions and try again."); }
    finally { setPending(false); }
  };
  return <Modal show onClose={close} dismissible={!pending} size="lg"><ModalHeader>Change PPPoE password</ModalHeader>
    {success ? <ModalBody><div role="status" className="space-y-4"><p>{warning ? "Password saved locally, but router synchronization needs attention. The router password may still be unchanged." : "PPPoE password updated."}</p><p className="text-sm text-slate-500">An existing session is not disconnected automatically. The new password is used on the next authentication.</p><Button color="primary" onClick={close}>Done</Button></div></ModalBody> : <form onSubmit={(e) => { void submit(e); }}><ModalBody><div className="space-y-4">
      <p className="text-sm text-slate-500">This explicitly replaces the PPPoE password. The stored password cannot be retrieved.</p>
      {error ? <Alert color="failure">{error}</Alert> : null}
      <fieldset disabled={pending} className="space-y-4"><PasswordInput id="replace-pppoe-password" label="New password" value={password} onChange={setPassword} /><PasswordInput id="confirm-pppoe-password" label="Confirm password" value={confirm} onChange={setConfirm} /></fieldset>
      <div className="flex flex-wrap justify-end gap-3"><Button color="light" type="button" disabled={pending} onClick={close}>Cancel</Button><Button color="primary" type="submit" disabled={pending}>{pending ? "Changing…" : "Change password"}</Button></div>
    </div></ModalBody></form>}
  </Modal>;
}
