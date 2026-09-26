import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";


function Icon({ name, size = 20 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };

  const icons = {
    dashboard: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),

    customers: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),

    services: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M8 9h8" />
        <path d="M8 13h5" />
        <path d="M8 17h3" />
      </>
    ),

    network: (
      <>
        <rect x="3" y="3" width="6" height="6" rx="1" />
        <rect x="15" y="3" width="6" height="6" rx="1" />
        <rect x="9" y="15" width="6" height="6" rx="1" />
        <path d="M9 6h6" />
        <path d="M6 9v3a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V9" />
      </>
    ),

    payments: (
      <>
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <path d="M2 10h20" />
        <path d="M6 15h4" />
      </>
    ),

    billing: (
      <>
        <path d="M6 2h9l5 5v15H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" />
        <path d="M14 2v6h6" />
        <path d="M8 13h8" />
        <path d="M8 17h5" />
      </>
    ),

    finance: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 5V3h10v2" />
        <path d="M3 10h18" />
        <path d="M8 15h8" />
      </>
    ),

    support: (
      <>
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      </>
    ),

    reports: (
      <>
        <path d="M4 19V5" />
        <path d="M4 19h17" />
        <rect x="7" y="11" width="3" height="5" />
        <rect x="12" y="8" width="3" height="8" />
        <rect x="17" y="5" width="3" height="11" />
      </>
    ),

    analytics: (
      <>
        <path d="M3 3v18h18" />
        <path d="m7 16 4-5 3 3 5-7" />
      </>
    ),

    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.7 1.7-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.04 1.56V20h-2.4v-.2a1.7 1.7 0 0 0-1.04-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-1.7-1.7.06-.06A1.7 1.7 0 0 0 8.4 15a1.7 1.7 0 0 0-1.56-1.04H6v-2.4h.2A1.7 1.7 0 0 0 7.76 10a1.7 1.7 0 0 0-.34-1.88l-.06-.06 1.7-1.7.06.06A1.7 1.7 0 0 0 11 6.4 1.7 1.7 0 0 0 12.04 4.84V4h2.4v.2A1.7 1.7 0 0 0 15.48 5.76a1.7 1.7 0 0 0 1.88-.34l.06-.06 1.7 1.7-.06.06A1.7 1.7 0 0 0 18.72 9a1.7 1.7 0 0 0 1.56 1.04h.2v2.4h-.2A1.7 1.7 0 0 0 19.4 15z" />
      </>
    ),

    menu: (
      <>
        <path d="M4 6h16" />
        <path d="M4 12h16" />
        <path d="M4 18h16" />
      </>
    ),

    bell: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
        <path d="M10 21h4" />
      </>
    ),

    chevron: (
      <>
        <path d="m6 9 6 6 6-6" />
      </>
    ),

    logout: (
      <>
        <path d="M10 17l5-5-5-5" />
        <path d="M15 12H3" />
        <path d="M21 19V5a2 2 0 0 0-2-2h-6" />
      </>
    ),

    wifi: (
      <>
        <path d="M5 12.55a11 11 0 0 1 14.08 0" />
        <path d="M8.5 16.05a6 6 0 0 1 7 0" />
        <path d="M12 19.5h.01" />
      </>
    ),

    router: (
      <>
        <rect x="3" y="7" width="18" height="10" rx="2" />
        <path d="M7 11h.01" />
        <path d="M11 11h.01" />
        <path d="M15 11h.01" />
        <path d="M12 17v4" />
        <path d="M8 21h8" />
      </>
    ),

    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m13 6 6 6-6 6" />
      </>
    ),
  };

  return <svg {...common}>{icons[name]}</svg>;
}


const navigation = [
  {
    label: "Main",
    items: [
      {
        label: "Dashboard",
        icon: "dashboard",
        path: "/isp",
      },
    ],
  },

{
  label: "Customers",
  items: [
    {
      label: "Customers",
      icon: "customers",
      children: [
        {
          label: "All Customers",
          path: "/isp/customers",
        },
        {
          label: "Add Customer",
          path: "/isp/customers/new",
        },
        {
          label: "PPPoE Customers",
          path: "/isp/customers/pppoe",
        },
        {
          label: "Hotspot Customers",
          path: "/isp/customers/hotspot",
        },
        {
          label: "Static Customers",
          path: "/isp/customers/static",
        },
      ],
    },
  ],
},

  {
    label: "Services & Plans",
    items: [
      {
        label: "Services & Plans",
        icon: "services",
        children: [
          "Plans",
          "PPPoE Plans",
          "Hotspot Plans",
          "Static Plans",
          "DHCP Plans",
          "Bandwidth Profiles",
          "FUP",
        ],
      },
    ],
  },

{
  label: "Network",
  items: [
    {
      label: "Network",
      icon: "network",
      children: [
        "Network",
        "Routers",
        "IP Pools",
        "Alerts",
        "Router Guard",
        "Load Balancing",
        "Anti-VPN",
        "Self Install",
        "Router Setup",
        "Troubleshooting",
        "Port Forwarding",
        "Fiber Map",
      ],
    },
  ],
},

{
  label: "Access & Authentication",
  items: [
    {
      label: "Access Services",
      icon: "wifi",
      children: [
        "RADIUS",
        "PPPoE",
        "Hotspot",
        "Static IP",
        "DHCP",
      ],
    },
  ],
},

  {
    label: "Payments & Billing",
    items: [
      {
        label: "Payments",
        icon: "payments",
        children: [
          "M-Pesa",
          "Transactions",
          "Payment Logs",
          "Reconciliation",
        ],
      },
      {
        label: "Billing",
        icon: "billing",
        children: [
          "Invoices",
          "Payments",
          "Overdue",
          "Statements",
        ],
      },
    ],
  },

  {
    label: "Finance",
    items: [
      {
        label: "Finance",
        icon: "finance",
        children: [
          "Expenses",
          "Expense Categories",
          "Sales Agents",
          "Commissions",
        ],
      },
    ],
  },

  {
    label: "Support",
    items: [
      {
        label: "Support",
        icon: "support",
        children: [
          "Tickets",
          "Escalations",
          "SMS",
          "Email",
          "WhatsApp",
        ],
      },
    ],
  },

  {
    label: "Reports & Analytics",
    items: [
      {
        label: "Reports",
        icon: "reports",
        children: [
          "Revenue",
          "Customers",
          "Plans",
          "Payments",
          "Network",
          "Usage",
        ],
      },
      {
        label: "Analytics",
        icon: "analytics",
        children: [
          "Revenue",
          "Customer Growth",
          "Customer Churn",
          "Payment Collection",
          "Router Performance",
        ],
      },
    ],
  },

  {
    label: "System",
    items: [
      {
        label: "Settings",
        icon: "settings",
        children: [
          "Organization",
          "Users",
          "Billing",
          "Network",
          "Security",
        ],
      },
    ],
  },
];


function SidebarItem({
  item,
  openMenu,
  setOpenMenu,
}) {
  const navigate = useNavigate();

  const hasChildren =
    item.children?.length > 0;

  const isOpen =
    openMenu === item.label;

  if (!hasChildren) {
    return (
      <button
        type="button"
        onClick={() => {
          if (item.path) {
            navigate(item.path);
          }
        }}
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
      >
        <Icon
          name={item.icon}
          size={18}
        />

        <span>{item.label}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() =>
          setOpenMenu(
            isOpen ? null : item.label
          )
        }
        className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
      >
        <span className="flex items-center gap-3">
          <Icon
            name={item.icon}
            size={18}
          />

          <span>{item.label}</span>
        </span>

        <span className="text-xs">
          {isOpen ? "−" : "+"}
        </span>
      </button>

      {isOpen && (
        <div className="ml-6 mt-1 space-y-1 border-l border-slate-700 pl-3">
          {item.children.map((child) => {
            const label =
              typeof child === "string"
                ? child
                : child.label;

            const path =
              typeof child === "string"
                ? null
                : child.path;

            return (
              <button
                key={label}
                type="button"
                onClick={() => {
                  if (path) {
                    navigate(path);
                  }
                }}
                className="flex w-full items-center rounded-lg px-3 py-2 text-left text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white"
              >
                {label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Sidebar({
  mobileOpen,
  setMobileOpen,
  organizationName,
}) {
  const [openMenu, setOpenMenu] = useState(null);

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/60 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-slate-950 text-white transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 ${
          mobileOpen
            ? "translate-x-0"
            : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="flex h-20 shrink-0 items-center border-b border-slate-800 px-5">
          <div>
            <div className="text-xl font-bold tracking-wide">
              LINTECH
            </div>

            <div className="mt-0.5 text-xs text-slate-400">
              ISP Management Platform
            </div>
          </div>
        </div>

        {/* Organization */}
        <div className="border-b border-slate-800 px-4 py-4">
          <div className="rounded-xl bg-slate-900 px-3 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Organization
            </div>

            <div className="mt-1 truncate text-sm font-semibold text-white">
              {organizationName}
            </div>

            <div className="mt-1 text-xs text-emerald-400">
              Organization Portal
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {navigation.map((section) => (
            <div
              key={section.label}
              className="mb-5"
            >
              <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                {section.label}
              </div>

              <div className="space-y-1">
                {section.items.map((item) => (
                  <SidebarItem
                    key={item.label}
                    item={item}
                    openMenu={openMenu}
                    setOpenMenu={setOpenMenu}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom */}
        <div className="border-t border-slate-800 p-3">
          <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-400">
            Lintech ISP Portal
          </div>
        </div>
      </aside>
    </>
  );
}


function StatCard({
  title,
  value,
  description,
  icon,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">
            {title}
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-900">
            {value}
          </p>
        </div>

        <div className="rounded-xl bg-slate-100 p-3 text-slate-700">
          <Icon name={icon} size={20} />
        </div>
      </div>

      <p className="mt-3 text-xs text-slate-400">
        {description}
      </p>
    </div>
  );
}


function DashboardCard({
  title,
  description,
  children,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">
          {title}
        </h3>

        <p className="mt-1 text-xs text-slate-500">
          {description}
        </p>
      </div>

      <div className="p-5">
        {children}
      </div>
    </div>
  );
}


export default function OrganizationDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const organizationName =
    user?.organization?.name ||
    "Your Organization";

  const fullName =
    user?.full_name ||
    "Organization Admin";

  const initials = fullName
    .split(" ")
    .map((part) => part.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();


  function handleLogout() {
    logout();

    navigate(
      "/login",
      { replace: true }
    );
  }


  return (
    <div className="flex min-h-screen bg-slate-50">

      {/* Sidebar */}
      <Sidebar
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        organizationName={organizationName}
      />


      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">

        {/* Topbar */}
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">

          <div className="flex items-center gap-3">

            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
              aria-label="Open navigation"
            >
              <Icon name="menu" size={22} />
            </button>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                ISP Portal
              </p>

              <h1 className="text-lg font-semibold text-slate-900">
                Dashboard
              </h1>
            </div>

          </div>


          <div className="flex items-center gap-3">

            {/* Notifications */}
            <button
              type="button"
              className="relative rounded-xl p-2.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              aria-label="Notifications"
            >
              <Icon name="bell" size={20} />

              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </button>


            {/* Profile */}
            <div className="relative">

              <button
                type="button"
                onClick={() =>
                  setProfileOpen(!profileOpen)
                }
                className="flex items-center gap-3 rounded-xl px-2 py-1.5 hover:bg-slate-100"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
                  {initials}
                </div>

                <div className="hidden text-left sm:block">
                  <div className="text-sm font-semibold text-slate-900">
                    {fullName}
                  </div>

                  <div className="text-xs text-slate-500">
                    Organization Admin
                  </div>
                </div>

                <Icon
                  name="chevron"
                  size={15}
                />
              </button>


              {profileOpen && (
                <div className="absolute right-0 top-14 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">

                  <div className="border-b border-slate-100 px-3 py-2">
                    <p className="text-xs text-slate-400">
                      Signed in as
                    </p>

                    <p className="mt-1 truncate text-sm font-medium text-slate-900">
                      {user?.email}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-red-600 hover:bg-red-50"
                  >
                    <Icon
                      name="logout"
                      size={17}
                    />

                    Sign out
                  </button>

                </div>
              )}

            </div>

          </div>

        </header>


        {/* Content */}
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">

          {/* Welcome */}
          <div className="mb-7">

            <p className="text-sm text-slate-500">
              Welcome back, {fullName.split(" ")[0]}.
            </p>

            <h2 className="mt-1 text-2xl font-bold text-slate-900">
              {organizationName}
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Here's an overview of your ISP operations.
            </p>

          </div>


          {/* Stats */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

            <StatCard
              title="Total Customers"
              value="—"
              description="Customer data will appear here."
              icon="customers"
            />

            <StatCard
              title="Online Customers"
              value="—"
              description="Live connection data."
              icon="wifi"
            />

            <StatCard
              title="Monthly Revenue"
              value="—"
              description="Payment data will appear here."
              icon="payments"
            />

            <StatCard
              title="Active Services"
              value="—"
              description="Active subscriber services."
              icon="services"
            />

          </div>


          {/* Main grid */}
          <div className="mt-6 grid gap-6 xl:grid-cols-3">

            {/* Connection overview */}
            <div className="xl:col-span-2">

              <DashboardCard
                title="Connection Overview"
                description="Current subscriber connection status."
              >

                <div className="grid gap-4 sm:grid-cols-3">

                  <div className="rounded-xl bg-slate-50 p-5">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-white p-2 text-slate-700 shadow-sm">
                        <Icon name="wifi" size={18} />
                      </div>

                      <span className="text-sm font-medium text-slate-600">
                        Online
                      </span>
                    </div>

                    <p className="mt-4 text-2xl font-bold text-slate-900">
                      —
                    </p>
                  </div>


                  <div className="rounded-xl bg-slate-50 p-5">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-white p-2 text-slate-700 shadow-sm">
                        <Icon name="router" size={18} />
                      </div>

                      <span className="text-sm font-medium text-slate-600">
                        Offline
                      </span>
                    </div>

                    <p className="mt-4 text-2xl font-bold text-slate-900">
                      —
                    </p>
                  </div>


                  <div className="rounded-xl bg-slate-50 p-5">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-white p-2 text-slate-700 shadow-sm">
                        <Icon name="services" size={18} />
                      </div>

                      <span className="text-sm font-medium text-slate-600">
                        Suspended
                      </span>
                    </div>

                    <p className="mt-4 text-2xl font-bold text-slate-900">
                      —
                    </p>
                  </div>

                </div>

              </DashboardCard>

            </div>


            {/* Network status */}
            <DashboardCard
              title="Network Status"
              description="Your connected infrastructure."
            >

              <div className="space-y-4">

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
                      <Icon name="router" size={18} />
                    </div>

                    <div>
                      <p className="text-sm font-medium text-slate-800">
                        Routers
                      </p>

                      <p className="text-xs text-slate-500">
                        Network devices
                      </p>
                    </div>
                  </div>

                  <span className="text-sm font-semibold text-slate-900">
                    —
                  </span>
                </div>


                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
                      <Icon name="wifi" size={18} />
                    </div>

                    <div>
                      <p className="text-sm font-medium text-slate-800">
                        PPPoE
                      </p>

                      <p className="text-xs text-slate-500">
                        Active sessions
                      </p>
                    </div>
                  </div>

                  <span className="text-sm font-semibold text-slate-900">
                    —
                  </span>
                </div>


                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
                      <Icon name="wifi" size={18} />
                    </div>

                    <div>
                      <p className="text-sm font-medium text-slate-800">
                        Hotspot
                      </p>

                      <p className="text-xs text-slate-500">
                        Active sessions
                      </p>
                    </div>
                  </div>

                  <span className="text-sm font-semibold text-slate-900">
                    —
                  </span>
                </div>

              </div>

            </DashboardCard>

          </div>


          {/* Lower grid */}
          <div className="mt-6 grid gap-6 lg:grid-cols-2">

            <DashboardCard
              title="Recent Payments"
              description="Latest customer payment activity."
            >

              <div className="flex min-h-44 items-center justify-center text-center">

                <div>
                  <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                    <Icon name="payments" size={20} />
                  </div>

                  <p className="text-sm font-medium text-slate-700">
                    No payment data yet
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    Transactions will appear here once
                    payments are connected.
                  </p>
                </div>

              </div>

            </DashboardCard>


            <DashboardCard
              title="Recent Customers"
              description="Latest subscriber accounts."
            >

              <div className="flex min-h-44 items-center justify-center text-center">

                <div>
                  <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                    <Icon name="customers" size={20} />
                  </div>

                  <p className="text-sm font-medium text-slate-700">
                    No customer activity yet
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    Customer records will appear here.
                  </p>
                </div>

              </div>

            </DashboardCard>

          </div>


          {/* Service summary */}
          <div className="mt-6">

            <DashboardCard
              title="Service Overview"
              description="Subscriber services by access method."
            >

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

                {[
                  ["PPPoE", "wifi"],
                  ["Hotspot", "wifi"],
                  ["Static IP", "network"],
                  ["DHCP", "network"],
                ].map(([label, icon]) => (
                  <div
                    key={label}
                    className="rounded-xl border border-slate-200 p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
                        <Icon name={icon} size={18} />
                      </div>

                      <span className="text-xs text-slate-400">
                        Active
                      </span>
                    </div>

                    <p className="mt-4 text-sm font-semibold text-slate-900">
                      {label}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      —
                    </p>
                  </div>
                ))}

              </div>

            </DashboardCard>

          </div>


          {/* Footer */}
          <footer className="py-8 text-center text-xs text-slate-400">
            Lintech ISP Management Platform
          </footer>

        </main>

      </div>

    </div>
  );
}