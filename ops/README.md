# Lintech release, backup and pilot runbook

Do not expose the development stack publicly. Local ports bind to 127.0.0.1.
Staff JWT refresh tokens are now blacklisted on logout, and password changes revoke
existing access tokens. Existing staff sessions must sign in again after this release.
The token-blacklist app adds its vendor migrations; the RADIUS migration is state-only.

A public deployment requires an owned domain with DNS pointed at the server.
No domain has been purchased yet. The .net suffix alone cannot be configured for TLS.

## Release identity and acceptance

Use one reviewed checkout. Never copy individual files into running containers.
`ops/release.py build` creates source-hash/timestamp tags and an image-ID manifest,
then tests those images against disposable PostgreSQL and real Chromium. Browser
acceptance uses production secure-cookie/proxy/cache settings with an isolated
internal TLS CA. It does not substitute for validating a public certificate. The worker
and API use exactly the same backend image. Frontend and FreeRADIUS use matching tags.
The release manifest supports dirty local source through a full source fingerprint;
a production handover should also record the reviewed Git commit.

Operations tools use Python 3 with cryptography. Locally use `backend/.venv/bin/python`.
On a deployment operator host, create `.ops-venv` and install `ops/requirements.txt`.
Docker Compose v2, Git and Node are required on the release build host. Browser tests
use an isolated container and a pinned tool installed outside application dependencies:

```bash
npm install --prefix .local/browser-tools --no-save --no-package-lock playwright@1.64.1
docker pull mcr.microsoft.com/playwright:v1.64.1-noble
backend/.venv/bin/python ops/release.py build
```

This checks every backend module in a private PostgreSQL network, real staff/customer
login, CSRF, tenant denial, browser desktop/mobile navigation, dark mode, customer
support tickets/replies, superadmin permission checks and staff provisioning. No live
router or payment-provider request is made. Evidence is under `.local/browser/` and
`.local/releases/`. Image IDs are checked again before deployment; changed tags abort.

## Encrypted backups and key escrow

Create a backup key once, with owner-only file permissions. The key is independent
of Django/field encryption. NEVER overwrite the existing key or print it in logs.
Keep an offline/password-manager copy away from both the server and backup storage.

```bash
mkdir -m 700 -p .local
# Exclusive creation: refuses to overwrite an existing key.
backend/.venv/bin/python -c 'import os; from cryptography.fernet import Fernet; f=os.fdopen(os.open(".local/backup.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"); f.write(Fernet.generate_key()); f.close()'
backend/.venv/bin/python ops/backup.py create --key-file .local/backup.key
backend/.venv/bin/python ops/backup.py verify --key-file .local/backup.key --archive .local/backups/NAME.dump.enc
```

A pair consists of `.dump.enc` (PostgreSQL custom archive) and `.secrets.enc`
(effective field key, Django key, release and host .env). Both are authenticated,
stream-encrypted and mode 600; the directory must be 700. Keep both together, and
store the backup key separately. RADIUS tables and encrypted provider credentials
are included in the database dump. There are currently no persistent user-uploaded
media volumes; add media backup if uploads are introduced.

Verification decrypts to an unlinked temporary file, creates a disposable PostgreSQL
container with **no network and no ports**, restores there, reads core and RADIUS
row counts and decrypts a restored PPPoE credential using the escrowed key when one
exists. It never restores onto the live database. Container removal only deletes
the temporary drill container. A `.verified.json` file records successful recovery.
Tampering, truncation, reordered frames, a wrong key or extra bytes fail validation.

Set up daily backups before an external pilot; use the systemd examples in this
folder with paths adjusted to your server. Copy the encrypted pairs off-host over
an authenticated channel after each successful backup. Keep at least 7 daily and
4 weekly copies; verify a fresh restore weekly. The exact off-host destination is
operator configuration, not an unverified claim made by these scripts.

## Safe local update

```bash
backend/.venv/bin/python ops/release.py deploy \
  --manifest .local/releases/RELEASE.json --key-file .local/backup.key
```

The worker stops first. A fresh backup is created and successfully restored in the
isolated drill before API shutdown/migrations. Migrations run once as an explicit
job, then API, worker, frontend and RADIUS start from the verified release. This is
a short maintenance window, not a zero-downtime deploy. Stop user traffic during it.
Readiness checks the database and exposes only status and release ID. The API and
worker must have identical image IDs; confirm with `docker compose images` using
`LINTECH_RELEASE=RELEASE` and the explicit compose files used for deployment.

The RADIUS initial migration records unmanaged model state only; `sqlmigrate radius
0001` produces no table DDL. Existing FreeRADIUS tables remain untouched. On a brand
new server, initialize the PostgreSQL FreeRADIUS schema from the exact shipped
FreeRADIUS image before enabling authentication. Do not assume Django creates it.

## Public HTTPS deployment (after domain purchase)

1. Set `PUBLIC_DOMAIN` to the exact owned host, e.g. `billing.YOUR-DOMAIN.net`.
2. Point A/AAAA DNS at the server. Publish 80/443 for Caddy; Caddy obtains and renews
   certificates and redirects HTTP. Remove AAAA if IPv6 is not routed correctly.
3. Set strong unique `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`,
   `LINTECH_FIELD_ENCRYPTION_KEY` and `RADIUS_SHARED_SECRET`. Do not rotate existing
   field encryption keys without a re-encryption plan. Preserve the key escrow.
4. Set the actual trusted NAS/VPN subnet in `RADIUS_CLIENT_NETWORK`. Firewall UDP
   1812/1813 to known NAS/VPN addresses; never allow all internet sources. Use VPN
   access for MikroTik/OLT management until verified RouterOS TLS is completed.
5. Use `--production` on deploy. This explicitly excludes the local compose
   override. PostgreSQL and Django are not published. HTTPS proxy headers are
   trusted only because Caddy is the sole public entry point.
6. Production settings reject DEBUG, wildcard hosts, weak Django keys, missing
   encryption keys, missing database configuration and non-HTTPS origins. JWT,
   session and CSRF cookies become Secure. Cookie-based writes and login/refresh
   require CSRF. The frontend fetches/echoes the token automatically.
7. Production creates `lintech_cache` for shared per-IP login throttling. DRF
   throttling is defense-in-depth, not a DDoS control; configure edge/firewall
   limits too. Public registration stays denied. Only a superadmin can create
   ISP staff through an organization's **Create staff account** action. An ISP
   owner/admin can create its subscribers using existing Customer Management.
8. Run `check --deploy --tag security`. HSTS starts at 3600 seconds and deliberately
   does **not** include subdomains or preload. W005/W021 are retained warnings,
   not silenced: enable those options only after confirming every affected host
   uses HTTPS and understanding that preload has long-lived consequences.
9. Validate a real HTTPS staff login, customer login and secure cookies before
   opening pilot access. No script can validate a certificate for an unowned host.

## Recovery / rollback

Keep the previous image IDs and release manifest, encrypted pair, backup key and
escrow available before each update. Do not use `docker compose down -v`.

If deployment fails, keep traffic closed and the worker stopped. Inspect only
sanitized logs. If migrations are backwards compatible, restart the previous
image IDs and re-check health. Do not blindly roll back a schema or replay old
payments. If a database restore is required, first preserve a new encrypted copy
of current state, run the isolated verification, agree the recovery point and
pause provider callbacks/settlement. Restore into a **new** database, supply the
matching escrowed field key, test it, then explicitly switch the application.
The supplied verify command never overwrites production on your behalf.

## Final operator acceptance before external pilot

- Verify domain/TLS, cookie security, both login flows, sign-out and expiry.
- Create one new ISP and a standard owner; confirm it cannot access another ISP.
- Create a controlled RADIUS subscriber, authenticate from its real router, and
  verify start, interim, stop and stale accounting. Test explicit password and
  package changes without resetting the other credentials.
- Run one controlled payment, repeat the callback and confirm exactly one ledger
  receipt/allocation. Check failed/cancelled callbacks and reconciliation recovery.
- Check one scheduled billing run, SMS submission and failed-provider behavior.
- Raise a customer ticket; reply as ISP support; confirm the customer sees it.
- Confirm backup timer success, off-host copy, restore evidence and monitoring of
  API/worker/database/RADIUS failures. Assign an operator to check alarms daily.

The pilot should use a small group and manual review of invoices/payments. Hotspot
completion, automated Lintech SaaS subscription collection, accurate bandwidth
snapshot-delta reports, secure impersonation and RouterOS TLS remain separate work;
keep unsupported actions disabled. These are not secretly implemented by release tooling.


## Additional operating notes

- Django uses `Africa/Nairobi` by default (override `DJANGO_TIME_ZONE` if needed).
  Backup names and machine-readable release evidence use UTC timestamps.
- Never merely change POSTGRES_PASSWORD against an initialized database volume:
  PostgreSQL does not rotate its existing role password from that environment
  variable. Use a planned database role password change, then update the matching
  connection configuration and restart API/worker/RADIUS together. Production
  refuses passwords shorter than 20 characters. Use URL-safe characters or URL
  encode the password in DATABASE_URL.
- Staff can change their initial password in Admin Settings; this is separate
  from subscriber PPPoE replacement. ISP organization codes are visible there for
  customer portal onboarding. Email delivery/recovery requires a configured and
  tested SMTP provider; do not promise invitations or recovery email until tested.
- Run Django's `flushexpiredtokens` maintenance command daily after deploying
  token blacklisting. Test accounts and browser artifacts contain only disposable
  acceptance data; real customer credentials must not enter screenshots or logs.
- Dependency advisories are checked with `npm audit`. The deepmerge-ts 8.0.2
  override avoids a vulnerable recursive merge without downgrading Flowbite's
  component API; build, SSR and browser checks verify the supported plain-object
  theme configuration. Recheck advisories when preparing each release.

## Dependency and deployment status

Docker builds install the pinned `backend/requirements.txt`; the historical
`backend/uv.lock` is not the production dependency source. Do not deploy from that
older lock without regenerating and auditing it. Both backend and frontend
dependencies were updated against their advisory databases. The upgraded
cryptography library successfully restored a backup created by the older version
and decrypted its existing stored PPPoE credential without re-encrypting live data.

A release is deployable only after its matching images pass full PostgreSQL and
HTTPS browser acceptance. Deployment checks existing encryption/signing keys and
the NAS shared secret against the target configuration, and refuses accidental
rotation. Previous service image information is recorded under `.local/deployments/`.
Local checks alone do not constitute production sign-off.

Off-server storage is undecided. The backup timer templates have not been installed
on a production host. Keep an independent copy of the backup key and choose a
remote destination before accepting production customer data.

Registered-NAS / Hotspot onboarding, safety gates and real-router tests are documented
in [HOTSPOT.md](HOTSPOT.md). Use that runbook before enabling registered-NAS mode.
