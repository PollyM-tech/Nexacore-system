# Remaining ISP admin implementation report

This pass changes frontend code only. Existing Dashboard, Customer Management and Package Management source files were preserved. No dependencies were installed and no commits were created.

## Module outcome and API contracts

All paths below are relative to `/api`. Authentication and organization scoping remain server enforced through the existing cookie-based client. Organization IDs are not supplied by these forms. Backend role errors remain visible; the account API does not expose a trustworthy organization role for client-side permission inference.

| Module | Delivered | API sources | Limitations / blocked actions |
| --- | --- | --- | --- |
| Routers | Paginated inventory, create/edit, enabled configuration, stored status/last check, explicit API test with pending/result state, session link | GET/POST `/mikrotik/routers/`; PATCH `/mikrotik/routers/<id>/`; POST `/<id>/test_connection/` under that collection | Delete hidden: backend cascades RouterInfo without an assignment guard. Counts are not returned. TLS setup/testing disabled: connection code ignores persisted `use_ssl`. Existing SSL settings remain intact. |
| Live sessions | Separate RouterOS and RADIUS tabs; customer, username, IP, MAC, uptime, router, cumulative bytes; explicit snapshots | GET `/bandwidth/live/?router=<id>`; POST `/bandwidth/sync/`; GET `/radius/sessions/active/?limit=100` | No standalone authorized session-disconnect API. RouterOS partial failure cannot be attributed to individual routers. RADIUS preview is capped, not a full pageable list. No fake instantaneous rates. |
| Bandwidth reports | Existing report views retained with explicit loading/error states and snapshot semantics | GET `/bandwidth/summary/`, `/bandwidth/logs/`, `/bandwidth/top-users/`, `/bandwidth/router-summaries/`, `/bandwidth/export/` | Backend sums cumulative snapshots and can double-count bytes. Labels explicitly avoid accurate-consumption claims. |
| Payments / M-Pesa | Server pagination and method filtering; cash/M-Pesa/bank/card/adjustment/other; KES; receipt, operator, notes, timestamps; manual payment/adjustment validation | GET `/billing/billing/transactions/?payment_method=<method>&page=<n>&page_size=10`; POST `/billing/billing/add_transaction/`; GET `/customers/` for selection | Payment-attempt and reconciliation admin REST endpoints do not exist. Ledger receipts are shown; no invented M-Pesa attempts UI. Adjustments are explicitly not received income. |
| Billing | Paginated monthly bills and connection fees; billed/allocated/outstanding terminology; customer detail links; confirmed bulk monthly generation; connection-fee creation | GET `/billing/billing/monthly_bills/` with payment_status/billing_month/billing_year; GET `/billing/billing/connection_fees/`; POST `/billing/billing/generate_monthly_bills/`, `/billing/billing/generate_connection_fee/` | Invoice allocations are not cash received. Historical invoices are not rewritten by the frontend. |
| Zones | Server pagination, create/edit, customer option invalidation | GET/POST `/zones/`; PATCH `/zones/<id>/` | Delete hidden: zone FK cascades customers. No active flag or usage counts exist. Unsupported filters are not sent. |
| Tickets | Paginated status/priority filtering, creation, keyboard-accessible thread button, replies and status/priority changes with errors | GET/POST `/tickets/`; GET/PATCH `/tickets/<id>/`; POST `/tickets/<id>/reply/` | Exact states: open/in_progress/resolved/closed; priorities low/medium/high/urgent. No invented workflow. Deletion omitted in favor of closing tickets. |
| SMS | Compose, confirmed bulk send, provider submission history, templates, gateway configuration/test/default and explicit credential replacement | `/sms/gateways/`, `/sms/templates/`, `/sms/logs/`; GET `/sms/sms/providers/`; POST `/sms/sms/send/`, `/sms/gateways/<id>/test/`, `/sms/gateways/<id>/set_default/` | Submission success is not handset delivery. Missing/failed configuration disables sending. Actual provider success depends on deployed credentials and connectivity. |
| OLT / ONU | OLT inventory/create/edit, explicit SNMP test, stored ONU inventory/search/filter, explicit SNMP sync, RX/TX/model/last-seen fields | `/olt/devices/`, `/olt/onus/`; POST `/olt/devices/<id>/test_connection/`, `/olt/devices/<id>/sync_onus/` | Manual ONU create/edit/delete hidden: backend OLT tenant checks happen after saving and customer relations are not tenant-validated. Device deletion hidden to protect stored ONUs. Stored values are not claimed as continuous telemetry. |
| Scheduler | Corrected endpoint, read-only known task schedules, status and next run | GET `/scheduler/tasks/` | Global scheduler changes are platform-only. No last-run/result API or run-now action. No arbitrary execution UI. |
| Settings | Lintech account data only when available, unavailable role instead of fabricated Administrator, dark/light theme, sign-out | GET `/auth/user/`; existing POST `/auth/logout/` | No tenant settings update API is exposed here. No platform/superadmin settings added. |

Complete supported workflows: billing, tickets, SMS configuration/submission, settings, and zone list/create/edit. Router, live-session, payments/M-Pesa and OLT/ONU modules are operational with the restrictions above; backend-only capabilities remain partial. Scheduler is intentionally read-only for normal ISP administrators.

## Shared behavior and security

- Added `AdminResourceList`: preserves server pagination metadata, debounces only supported backend search, provides retry/loading/error/empty states, and reuses horizontally scrollable tables. Unpaginated endpoints remain complete lists. Unsupported router/zone/ticket/payment search is not faked on a first page.
- Added `useAdminOptions`: exhausts paginated options safely and shares a query across consumers rather than fetching each customer separately.
- Added `useAdminCrud`: scoped invalidation, no broad cache clearing; completed credential-bearing mutation entries use zero garbage-collection retention and are reset when forms close.
- Added `CustomerLink`: maps internal invoice/ledger customer IDs to the existing external-ID detail route using one shared customer-list request, never N+1 detail calls.
- `FormModal` gained an optional submit-disabled flag so unavailable configuration can block submission without presenting it as a save in progress. Dismissal is also blocked while a submission is pending, preventing accidental loss of mutation feedback. Existing non-submitting callers retain their behavior.
- Router/OLT/provider secrets are never taken from read responses, rendered in inventory, logged, or persisted in browser storage. Passwords and sensitive provider configuration start masked; omitted replacement values preserve stored credentials. Provider credential replacement is explicit and requires complete input.
- Test errors use safe operational messages. SMS submission history does not expose raw provider responses. No callback token or provider key is displayed.
- Navigation now groups Overview, Subscribers, Network, Support and System, retaining the existing mobile drawer.
- KES replaces obsolete currency/method choices throughout touched operational screens. Shared byte/duration/date formatting is reused; API errors are not zero/offline/success states.

## Query invalidation

- Router mutations: router lists/options, customer router options, live RouterOS query and dashboard; explicit connection tests refresh stored status/dashboard.
- Payments: transactions, monthly bills, connection fees, customer list/detail/billing data, customer options and dashboard.
- Billing creation/generation: affected invoice queries, customer list/detail and dashboard.
- Zones: zones, complete zone options and customer form zone options.
- Tickets: lists, active detail/thread and dashboard after changes/replies.
- OLT/SNMP: devices and ONUs as relevant; options are invalidated after device mutations.
- SMS: templates/gateways and provider submission logs as relevant.

## Validation

- TypeScript with strict/no-unused checks: PASS.
- Production Vite build: PASS.
- `git diff --check`: PASS.
- `node scripts/check-admin.mjs` from frontend: PASS. Checks include router/provider secret omission, stored connection state, payment pagination/method filters, adjustment semantics, KES, RouterOS failure states, zone/ONU mutation restrictions, scheduler visibility, settings identity, complete option pagination and targeted invalidation. Source checks supplement secret-preservation assertions because Flowbite portals do not render open dialogs under SSR.
- Backend tracked diff fingerprint matches the pre-task fingerprint: `f3c287b12d03a920b53aa25dee03fa9b1aec85bbe3c20d912c0bc2cbfad3bb2b`. No backend files were edited.
- Browser automation unavailable: interactive modal behavior, desktop/mobile viewport layout, real tenant/role sessions and live integrations have not been browser-verified.
- Existing Vite chunk warning remains: roughly 1.08 MB minified / 314 KB gzip main JS. Route-based splitting is recommended later.

## Recommended cleanup before another product area

1. Browser-test every admin route at desktop/mobile widths using owner, technician, billing, support and viewer accounts.
2. Fix backend TLS handling, ONU tenant validation, assigned-router/zone deletion guards and accurate bandwidth delta reporting before enabling blocked capabilities.
3. Add tenant-scoped M-Pesa attempts/reconciliation and scheduler result APIs only if required operationally.
4. Verify deployed SMS/SNMP/RouterOS/M-Pesa integrations using controlled records; review the complete existing uncommitted work before committing.
5. Split admin routes into lazy bundles once functional acceptance is complete.

## Exact files changed in this pass

- `frontend/ADMIN_IMPLEMENTATION_REPORT.md`
- `frontend/scripts/check-admin.mjs`
- `frontend/src/features/admin/AdminResourceList.tsx`
- `frontend/src/features/admin/CustomerLink.tsx`
- `frontend/src/features/admin/useAdminCrud.ts`
- `frontend/src/features/admin/useAdminOptions.ts`
- `frontend/src/features/bandwidth/ActiveSessionsTable.tsx`
- `frontend/src/features/bandwidth/LiveUsageView.tsx`
- `frontend/src/features/bandwidth/ReportSummaryCards.tsx`
- `frontend/src/features/bandwidth/UsageReportsView.tsx`
- `frontend/src/features/bandwidth/useLiveBandwidth.ts`
- `frontend/src/features/billing/BillingTabs.tsx`
- `frontend/src/features/billing/ConnectionFeesList.tsx`
- `frontend/src/features/billing/GenerateBillsModal.tsx`
- `frontend/src/features/billing/MonthlyBillsList.tsx`
- `frontend/src/features/billing/billingColumns.tsx`
- `frontend/src/features/olt/OltDeviceForm.tsx`
- `frontend/src/features/olt/OltDevicesManager.tsx`
- `frontend/src/features/olt/OnuForm.tsx`
- `frontend/src/features/olt/OnusManager.tsx`
- `frontend/src/features/olt/onuColumns.tsx`
- `frontend/src/features/payments/CustomerSearchSelect.tsx`
- `frontend/src/features/payments/PaymentForm.tsx`
- `frontend/src/features/payments/PaymentsHistory.tsx`
- `frontend/src/features/payments/paymentColumns.tsx`
- `frontend/src/features/routers/RouterForm.tsx`
- `frontend/src/features/routers/RoutersManager.tsx`
- `frontend/src/features/routers/routerColumns.tsx`
- `frontend/src/features/scheduler/SchedulerTaskCard.tsx`
- `frontend/src/features/scheduler/useSchedulerTasks.ts`
- `frontend/src/features/sms/AudienceFields.tsx`
- `frontend/src/features/sms/GatewayField.tsx`
- `frontend/src/features/sms/MessageEditor.tsx`
- `frontend/src/features/sms/SmsCompose.tsx`
- `frontend/src/features/sms/SmsGatewayForm.tsx`
- `frontend/src/features/sms/SmsGateways.tsx`
- `frontend/src/features/sms/SmsHistory.tsx`
- `frontend/src/features/sms/SmsTemplateForm.tsx`
- `frontend/src/features/sms/SmsTemplates.tsx`
- `frontend/src/features/sms/smsLogColumns.tsx`
- `frontend/src/features/tickets/TicketDetail.tsx`
- `frontend/src/features/tickets/TicketForm.tsx`
- `frontend/src/features/tickets/TicketsManager.tsx`
- `frontend/src/features/tickets/ticketColumns.tsx`
- `frontend/src/features/zones/ZoneForm.tsx`
- `frontend/src/features/zones/ZonesManager.tsx`
- `frontend/src/features/zones/zoneColumns.tsx`
- `frontend/src/pages/BandwidthLivePage.tsx`
- `frontend/src/pages/PaymentsPage.tsx`
- `frontend/src/pages/SchedulerPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/SmsPage.tsx`
- `frontend/src/shared/api/endpoints.ts`
- `frontend/src/shared/components/ui/FormModal.tsx`
- `frontend/src/shared/constants/nav.ts`
- `frontend/src/shared/types/api.ts`
