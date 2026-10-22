# Platform API foundation

All routes require an authenticated Django `is_superuser`. Organization membership
and `is_staff` do not grant platform access. Non-superusers receive HTTP 403;
unauthenticated requests receive the authentication layer's HTTP 401/403 response.
Existing tenant endpoints and `/api/auth/user/` are unchanged.

## Routes

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/api/platform/me/` | Platform identity, no membership required |
| GET | `/api/platform/summary/` | Cross-tenant aggregates |
| GET, POST | `/api/platform/organizations/` | Paginated organization list / create |
| GET, PATCH | `/api/platform/organizations/<id>/` | Organization detail / update |
| GET, POST | `/api/platform/organizations/<id>/members/` | Paginated memberships / add existing user |
| GET, PATCH, DELETE | `/api/platform/organizations/<id>/members/<membership_id>/` | Inspect / update / remove membership |
| GET | `/api/platform/users/` | Paginated safe user metadata |
| GET | `/api/platform/users/<id>/` | Safe user detail |
| GET | `/api/platform/audit/` | Paginated cross-tenant audit, including organization-null platform events |
| GET | `/api/platform/audit/<id>/` | Redacted audit detail |

Organization deletion and PUT, user mutations, audit mutations, impersonation,
password management, invitations, SaaS subscriptions, platform settings and health
checks are not implemented.

## Identity

```json
{
  "is_platform_admin": true,
  "user": {"id": 1, "email": "operator@example.test", "username": "operator", "first_name": "", "last_name": ""}
}
```

## Organizations

Fields: `id`, `name`, `slug`, `organization_type`, `status`, `is_active`,
`phone_number`, `email`, `country`, `currency`, `timezone`, `created_at`,
`updated_at`, `member_count`, `customer_count`, `router_count`, `package_count`.

Count fields are read-only and returned on list/detail/create/update. They count
all assigned records, including inactive records. Four correlated count
subqueries avoid both N+1 queries and multiplicative joins.

Search: `search` matches name/slug. Filters: `status`, `is_active`.
Types: `hotspot`, `pppoe`, `hybrid`. Statuses: `active`, `suspended`, `inactive`.

For platform writes, `active` sets `is_active=true`; suspended/inactive set false.
Writing only `is_active` sets status to active/inactive. Explicit conflicting
status/flag pairs return HTTP 400. This matters because existing tenant access
checks the active flag. Suspension blocks subsequent tenant organization
resolution; it does not terminate issued authentication cookies or PPPoE sessions.
Existing inconsistent records are not rewritten by reads.

## Memberships and users

Create a membership using `{"user_id": 2, "role": "admin", "is_active": true}`.
Users must already exist. Roles: owner/admin/technician/billing/support/viewer.
Responses contain `id`, nested safe `user` identity, `role`, `is_active`,
`created_at`, `updated_at`. User identity cannot be reassigned on PATCH.
Membership lookup always includes the route's organization; mismatches are 404.
Duplicates return HTTP 400 keyed by `user_id`.

The last active owner whose user account is active cannot be removed, disabled or
demoted. Platform membership mutations lock the parent organization transactionally
so concurrent changes to different owners serialize on databases with row locks.
A newly created organization can initially have no members; add its owner before
handing it over. This API cannot prevent direct database/admin edits or unrelated
user-account deactivation outside this workflow.

Platform user fields: identity fields above plus `is_active`, `is_superuser`,
`date_joined`, `last_login`, `membership_count`. Membership counts include inactive
memberships. `search` matches username/email/first_name/last_name. Password hashes,
tokens and write operations are not exposed.

## Summary

```json
{
  "organizations": {"total": 2, "active": 1},
  "users": {"total": 4},
  "customers": {"total": 20, "active": 18},
  "routers": {"total": 3, "active": 2},
  "packages": {"total": 5, "active": 4}
}
```

Each model uses a direct aggregate/count query, independent of tenant count.
Active organizations require both active status and flag. Active customers have
`customer_status=active`. Active routers/packages mean enabled configuration,
not live connectivity. Users means Django user accounts, not membership rows.

## Audit and pagination

Audit fields: `id`, `actor` (safe user identity or null), `actor_role`,
`organization` (ID or null), `organization_name`, `action`, `resource_type`,
`resource_id`, `created_at`, `metadata`.

Filters: `organization`, `user` (actor ID), `action`. Ordering is newest timestamp,
then newest ID. Free-form historical description/path/user-agent fields are
intentionally omitted. Metadata is recursively copied and redacted at read time
for secret-like keys, normalized spelling/case variations, nested arrays, and
credential attribute/value records. Redaction is key-based; arbitrary secrets
embedded in unrelated free-form values cannot be reliably identified. Existing
audit rows are not modified. Organization/member mutations add safe audit events
within the same transaction; no request body is logged.

All lists use the existing paginator: `page`, `page_size` (default 10, max 100).
Envelope: `count`, `next`, `previous`, `total_pages`, `current_page`, `results`.
No ordinary tenant endpoint accepts a new organization override.

## Tests

Run `python manage.py check` and `python manage.py test platform_api` from backend.
Broader tenant fixtures require a field-encryption key in the test process.
No schema changes or migrations are required by this package.
