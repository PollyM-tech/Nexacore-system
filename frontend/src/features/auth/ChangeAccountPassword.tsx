import { useState } from "react";
import { Alert, Button } from "flowbite-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { apiError } from "@/shared/utils/apiError";
import { PasswordInput } from "@/features/customers/PasswordInput";

export function ChangeAccountPassword() {
  const [oldPassword,setOldPassword]=useState("");
  const [newPassword,setNewPassword]=useState("");
  const [confirm,setConfirm]=useState("");
  const [validation,setValidation]=useState("");
  const change=useMutation({gcTime:0,mutationFn:async()=>{
    try {await api.post("/auth/password/change/",{old_password:oldPassword,new_password1:newPassword,new_password2:confirm});}
    catch(error){throw new Error(apiError(error,"Password could not be changed."));}
  },onSuccess:()=>{setOldPassword("");setNewPassword("");setConfirm("");}});
  return <form className="space-y-4" onSubmit={e=>{e.preventDefault();if(newPassword!==confirm){setValidation("New passwords must match.");return;}setValidation("");change.mutate();}}>
    <p className="text-sm text-slate-500">Changes your staff account password, not a subscriber’s PPPoE password. You will need to sign in again afterward.</p>
    {change.isSuccess&&<Alert color="success">Password changed. Sign out and sign in with your new password.</Alert>}
    {(validation||change.isError)&&<Alert color="failure">{validation||change.error?.message}</Alert>}
    <PasswordInput id="account-old-password" label="Current account password" value={oldPassword} onChange={setOldPassword} />
    <PasswordInput id="account-new-password" label="New account password" value={newPassword} onChange={setNewPassword} />
    <PasswordInput id="account-confirm-password" label="Confirm new account password" value={confirm} onChange={setConfirm} />
    <Button type="submit" color="primary" disabled={change.isPending}>{change.isPending?"Changing password…":"Change account password"}</Button>
  </form>;
}
