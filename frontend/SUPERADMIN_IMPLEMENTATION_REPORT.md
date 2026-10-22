# Superadmin frontend implementation

## Routes and identity

Added `/superadmin`, `/superadmin/organizations`, `/superadmin/organizations/:id`,
`/superadmin/users`, `/superadmin/audit`, and `/superadmin/settings`. Unknown routes
inside the platform area return to its dashboard through the same platform guard.

`usePlatformMe` calls GET `/api/platform/me/`. The guard shows loading while
checking, sends HTTP 401 to the existing `/admin/login` flow with an internal
return destination, shows Access Denied for 403 or a non-true authorization flag,
and shows retryable generic errors. Backend platform permissions remain final.
Tenant roles, staff flags, email and organization membership are never used to
infer platform privilege. Identity has a 30-second freshness window and refreshes
through normal query focus behavior; the shell shares the same identity query.

Existing login still defaults to `/admin`. Only an explicit guarded platform
return destination changes that destination. Successful login cancels/removes the
platform query namespace before continuing, so earlier account data is not reused.
Existing logout behavior is reused. The ISP account menu offers Platform
Administration only after `/platform/me/` confirms access. No tenant switching or
second authentication mechanism is introduced.

## Implemented areas and exact sources

| Area | API source | Behavior |
| --- | --- | --- |
| Dashboard | GET `/api/platform/summary/` | Total/active ISPs, total users, total/active customers, enabled routers, total packages. Enabled routers are configuration counts, not online/health claims. No fabricated charts. |
| Organizations | GET/POST `/api/platform/organizations/`, GET/PATCH `/api/platform/organizations/<id>/` | Server pagination, supported name/slug search and status filter, backend usage counts, linked detail, create/edit. No delete action. |
| Organization detail | GET `/api/platform/organizations/<id>/` | Identity, status/access flag, dates, contacts, locale and assigned record counts, plus nested membership management. |
| Memberships | GET/POST `/api/platform/organizations/<id>/members/`, PATCH/DELETE `/api/platform/organizations/<id>/members/<member_id>/` | Paginated members, existing-user picker using the paginated platform users API, exact roles, active/inactive changes and confirmed removal. Last-owner and duplicate errors remain visible. No invitations, user creation or identity reassignment. |
| Users | GET `/api/platform/users/` | Server pagination/search; safe names, email, account state, platform privilege, membership counts, joined/last-login dates. Read-only, no credential fields or user-edit/delete controls. |
| Audit | GET `/api/platform/audit/` | Server pagination, newest-first backend ordering, exact organization/user/action filters; actor, organization, action, resource, timestamp and bounded safe metadata preview. |
| Settings | No API request | Honest deployment-configuration placeholder. No editable settings or environment values. |

Organization create/edit fields are name, slug, organization_type, status, email
and phone_number. Backend locale defaults remain authoritative. Status is sent
without an independently conflicting is_active flag; only changed edit fields
are submitted. Suspension/deactivation require confirmation and explain retained
tenant data and unchanged PPPoE sessions. New organization success opens its
detail so an existing owner can be added; no account is created automatically.

Member roles are owner/admin/technician/billing/support/viewer. Role changes and
deactivation require confirmation; removal has a named confirmation modal. The
UI never overrides last-owner errors. An inactive selected user is identified as
inactive. Backend validation remains authoritative.

## Query, error and security behavior

- All platform data uses `platform`-prefixed TanStack Query keys. Ordinary tenant
  endpoints and keys are not reused for platform totals or management.
- Organization mutations invalidate organization lists/detail, platform summary
  and audit. Membership mutations additionally invalidate the organization's
  members and platform users, including paginated picker queries.
- No whole-cache clearing was added. Login removes only the platform namespace
  for account-transition safety; data mutations use targeted invalidation.
- Loading, empty, 400 validation, 401 authentication, 403 authorization, 404
  missing-resource and generic network/server failures have explicit states.
  Failed queries never become zero metrics or empty-success screens.
- Audit metadata is React-escaped, traversed with bounded depth/node/row/string
  limits, and defensively omits credential-like keys, redacted values and
  attribute/value credential records. No raw JSON dump or unsafe HTML is used.
  Request paths/descriptions omitted by the API are not rendered.
- No password inputs, token storage, organization impersonation or arbitrary
  organization overrides on tenant APIs were added. Platform requests only use
  `/api/platform/*`; organization IDs are explicit platform resource paths/filters.
- Separate platform navigation contains dashboard, organizations, users, audit
  and settings. It reuses Lintech styling, dark mode and the below-lg drawer.
- Shared pagination buttons now explicitly use type=button: paging within the
  membership user picker cannot accidentally submit the surrounding form.
- Existing ISP screens are unchanged apart from requested shared login/account
  navigation and pagination fixes. Public and customer portal pages are untouched.

## Validation

- Strict TypeScript / unused-import checks: PASS through `npm run build`.
- Production build: PASS; existing main-bundle warning remains (about 1.10 MB
  minified / 320 KB gzip). No dependencies were installed.
- `git diff --check`: PASS.
- `node scripts/check-platform.mjs`: PASS. Includes ordinary-user denial,
  affirmative platform authorization, failed summary states, organization counts,
  no organization-delete action, read-only users, last-owner error rendering,
  bounded/escaped/redacted audit previews, pagination/filter request parameters,
  targeted invalidation and shared form-pagination safety.
- `node scripts/check-admin.mjs`: PASS. Existing ISP-admin assertions retained.
- All existing ISP-admin routes still compile in the production build.
- Backend tracked diff fingerprint remains unchanged:
  `31ab88bcc3d88175b77403b94b93106f08ae6d132c9cc0f805911824d7bb1397`.
- Browser automation was not performed, as requested. SSR assertions cannot
  replace later interactive modal/mobile/login acceptance testing.

## Remaining backend gaps

Invitations/new-user provisioning, SaaS plans/subscriptions, editable platform
settings, real health endpoints and secure support-session/impersonation APIs
remain absent and are not simulated. Organization deletion is intentionally
unsupported. Last-owner protection remains server-enforced within platform API
workflows; direct database/admin edits are outside that guarantee. Key-based
redaction cannot identify arbitrary secrets hidden under unrelated free-text keys.

## Exact files added

- `frontend/src/features/platform/api.ts`
- `frontend/src/features/platform/types.ts`
- `frontend/src/features/platform/queries.ts`
- `frontend/src/features/platform/PlatformFeedback.tsx`
- `frontend/src/features/platform/PlatformProtectedRoute.tsx`
- `frontend/src/features/platform/PlatformShell.tsx`
- `frontend/src/features/platform/PlatformList.tsx`
- `frontend/src/features/platform/PlatformDashboard.tsx`
- `frontend/src/features/platform/OrganizationForm.tsx`
- `frontend/src/features/platform/Organizations.tsx`
- `frontend/src/features/platform/OrganizationMembers.tsx`
- `frontend/src/features/platform/PlatformUsers.tsx`
- `frontend/src/features/platform/PlatformAudit.tsx`
- `frontend/scripts/check-platform.mjs`
- `frontend/SUPERADMIN_IMPLEMENTATION_REPORT.md`

## Exact existing files modified

- `frontend/src/app/router.tsx`
- `frontend/src/features/auth/useLogin.ts`
- `frontend/src/features/auth/LoginForm.tsx`
- `frontend/src/shared/components/layout/UserMenu.tsx`
- `frontend/src/shared/components/data/TablePagination.tsx`
