import { usePlatformMe } from "@/features/platform/queries";
import { Avatar, Dropdown, DropdownDivider, DropdownHeader, DropdownItem } from "flowbite-react";
import { useNavigate } from "react-router-dom";
import { useLogout } from "@/features/auth/useLogout";
import { useSession } from "@/features/auth/useSession";
import { ROUTES } from "@/shared/constants/routes";

export function UserMenu() {
  const logout = useLogout();
  const platform = usePlatformMe();
  const navigate = useNavigate();
  const { user } = useSession();
  const email = user?.email || "Account information unavailable";

  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || user?.email || "Lintech account";
  const isPlatformAdmin = user?.is_platform_admin === true || (platform.isSuccess && platform.data.is_platform_admin === true);
  const tenantRole = user?.membership?.role_label;
  const role = [isPlatformAdmin ? "Superadmin" : null, tenantRole].filter(Boolean).join(" · ") || "Role unavailable";
  const initials = name.split(/\s+/).map(part => part[0]).join("").slice(0, 2).toUpperCase();

  return (
    <Dropdown
      arrowIcon={false}
      inline
      label={<span className="flex items-center gap-2"><Avatar rounded size="sm" placeholderInitials={initials} /><span className="hidden max-w-40 text-left sm:block"><span className="block truncate text-sm font-semibold">{name}</span><span className="block text-xs text-slate-500 dark:text-slate-400">{role}</span></span></span>}
    >
      <DropdownHeader>
        <span className="block text-sm font-semibold">{name}</span>
        <span className="block truncate text-sm text-slate-500">{email}</span>
        <span className="block text-xs text-slate-500">{role}</span>
        {user?.membership && <span className="block text-xs text-slate-500">{user.membership.organization.name}</span>}
      </DropdownHeader>
      <DropdownItem onClick={() => navigate(ROUTES.settings)}>Profile</DropdownItem>
      <DropdownItem onClick={() => navigate(ROUTES.settings)}>Settings</DropdownItem>
      {isPlatformAdmin && <DropdownItem onClick={() => navigate("/superadmin")}>Platform Administration</DropdownItem>}
      <DropdownDivider />
      <DropdownItem onClick={() => logout.mutate()}>Sign out</DropdownItem>
    </Dropdown>
  );
}
