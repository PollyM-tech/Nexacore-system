# Registered NAS and Hotspot pilot

Gunicorn access logging redacts callback tokens and authentication headers.
This is Django/DRF, using the existing Lintech organizations and React admin UI.
ISP accounts remain administrator-created. This does not add Lintech SaaS billing.
Network hardware, Wi-Fi, address pools, NAT and forwarding remain with the ISP.

## What is implemented

- Tenant-scoped NAS registration with an encrypted, write-only secret per NAS.
- IPv4 source identity, optional exact NAS-Identifier and optional PPPoE router
  attachment. The source IP and router attachment are immutable after enrollment.
- FreeRADIUS dynamic clients fetched from the private authenticated bridge, cached
  for at most 60 seconds. Disabled NAS/tenants are rejected by each authorization.
- PAP/CHAP voucher authentication; existing PPPoE Cleartext-Password and rate replies.
- Plan CRUD, frozen voucher entitlements, batches up to 200, audited code export,
  CSV/print and explicit single-voucher recovery. Codes are bearer credentials.
- Wall-clock validity beginning at successful authentication; reconnecting does
  not extend expiry. One MAC/device and one concurrent session per voucher.
- Session-Timeout, customer upload/download Mikrotik-Rate-Limit and remaining
  combined-byte Mikrotik-Total-Limit/Gigawords. Counters are cumulative usage.
- Start/interim/Stop accounting with monotonic counters and 64-bit octet handling.
- Signed RFC 5176 Disconnect-Request with Message-Authenticator, response digest/MA
  checks, ACK/NAK/timeout events, exponential backoff and five attempts per budget.
  An explicit audited operator retry grants another five attempts, retaining history.
- Authenticated ACK is distinct from Accounting Stop. Quota vouchers wait for final
  Stop before allocating another session so lost final counters cannot create extra
  quota. Stale accounting is shown as stale, never treated as proof of disconnection.
- Subscriber M-Pesa purchases use the ISP's configured Hotspot/both shortcode.
  Durable intents, retry keys, phone throttles, callback routing, provider query
  confirmation in production and idempotent voucher issuance are included.
- Cash receipts and confirmed M-Pesa sales appear in the Hotspot receipts view.
  Generated/unsold vouchers are not revenue. Hotspot sales are a separate ledger
  from PPPoE invoice allocation and the existing PPPoE dashboard income cards.

## Before switching an existing server

The default is `LINTECH_RADIUS_ISOLATED=0`: existing PPPoE client configuration stays
in use. New Hotspot STK requests are blocked in this mode. Prepare and inspect plans
and NAS records first; do not sell vouchers until the registered-NAS pilot passes.

1. Take and verify an encrypted backup. Use the matching-image release workflow.
   Apply the new `radius` and `hotspot` migrations. They create new managed tables;
   they do not rename/drop the existing FreeRADIUS accounting or credential tables.
2. Give every NAS a unique IP on the approved trusted network, preferably a
   WireGuard VPN with peer source-IP anti-spoofing. Register the IP, actual router
   identity if used, its own strong 32–128 character secret, and incoming UDP port.
   Link every existing RADIUS PPPoE router to its NAS before changing the mode.
   For a new AAA-only setup, select **Create a RADIUS-only PPPoE router entry**.
   It needs no RouterOS administrator credentials; select that entry when creating
   RADIUS subscribers. RouterOS live telemetry is unavailable unless you separately
   configure API access. Use RADIUS session/accounting status instead.
   Shared NAT public addresses cannot identify multiple NAS devices securely.
3. `RADIUS_CLIENT_NETWORK` must cover those assigned IPs. The source IP and reported
   NAS-IP-Address must match. It is a server-level allowlist, never `0.0.0.0/0`.
   Restrict UDP 1812/1813 and outgoing disconnect access to known VPN peers.
4. Set a strong independent `LINTECH_RADIUS_INTERNAL_TOKEN` on API, worker and
   FreeRADIUS. Never put it in frontend code or a NAS. Private bridge routes under
   `/api/internal/` are rejected by both public Caddy configurations.
5. Configure each NAS with the matching RADIUS source IP, individual secret and
   Message-Authenticator support. Use the setup instructions in **RADIUS NAS**.
   We explicitly configure incoming port 3799; MikroTik may otherwise default to
   1700. Limit that listener to the Lintech server address.
6. Arrange a short maintenance window and set `LINTECH_RADIUS_ISOLATED=1` consistently
   on API, worker and FreeRADIUS, then recreate them from one validated release.
   This replaces the legacy subnet-wide shared-secret client. Do not rotate secrets
   silently or change modes before the hardware is configured.
7. Enable the global **Hotspot expiry and RADIUS disconnect retries** scheduler task
   as platform administrator, or run the idempotent command:

   ```bash
   docker compose exec backend python manage.py install_hotspot_schedule
   ```

   It runs every minute. Keep the Django-Q worker running; monitor failed requests.
8. Set `PUBLIC_BASE_URL=https://YOUR_OWNED_DOMAIN`. Configure/test the ISP-owned Daraja
   credentials and callback reachability. This is independent of Lintech's pending
   SaaS paybill. Online checkout stays unavailable without configuration.

## Captive portal

In **RADIUS NAS → Setup**, download the NAS-specific `login.html` template. Upload it
alongside the stock MikroTik `md5.js` in the intended Hotspot HTML directory. It
supports PAP/CHAP, but requires a properly configured HTTPS captive portal.
Because the voucher is also the username, HTTP-CHAP alone does not conceal the
code. Configure a valid NAS Hotspot DNS name/certificate and `login-by=https`;
the template refuses to submit over plain HTTP.
Disable cookie/MAC/trial/local-user paths that bypass the intended RADIUS checks.
Keep router administrator access separate. Do not remove administrator accounts.

Allow the Lintech purchase hostname through the Hotspot walled garden, including
its HTTPS assets/DNS. The purchase page never asks for an M-Pesa PIN. The customer
returns to captive login with the voucher; it is entered as username and password.
The customer purchase token/code remains only in that page's memory. If they close
it after paying, authorized ISP billing staff can recover the paid voucher through
an audited action using the purchase/receipt. Do not charge again automatically.
Ambiguous STK submission failures need provider verification; Lintech never retries
an ambiguous charge silently. A successful STK query without a receipt remains
unfulfilled until the callback supplies a valid receipt.

## Validation and release gate

`ops/release.py build` now includes the full regression suite, desktop/mobile browser
flows and `ops/network_acceptance.py` using the exact images. The latter creates a
private disposable database and NAS simulators and sends actual PAP, CHAP, accounting
and Disconnect packets through FreeRADIUS. It does not contact a real NAS or Daraja.
Voucher codes are also RADIUS usernames and can occur in the restricted FreeRADIUS
accounting database; treat database/log access and exports as credential access.
Private failure logs can contain disposable test credentials; do not publish them.

Before selling to any ISP, test one real MikroTik:

- Invalid, revoked, expired and another ISP's voucher must fail.
- First successful login activates once. Reconnect must preserve expiry.
- Measure asymmetric upload/download speeds and inspect the returned attributes.
- Let Session-Timeout expire on the NAS; confirm internet actually stops.
- Consume a small quota, verify the NAS enforces the byte limit, verify accounting
  direction and Gigawords, and confirm reconnect cannot restore consumed quota.
- Try a second device and concurrent login. Check accounting Start/interim/Stop.
- Revoke a live voucher and suspend a PPPoE subscriber. Verify ACK and real traffic
  loss. Test a wrong incoming port/secret and blocked route; inspect timeout/retry.
- Restore connectivity and use the audited retry. Test late/duplicate accounting.
- Complete one authorized live M-Pesa purchase and one cancellation. Check one
  receipt, one issued voucher, correct tenant and usable network access.

## Deliberate limits

This MVP uses Disconnect messages, not in-place CoA speed changes. Plan edits apply
to future vouchers; PPPoE changes take effect on reauthentication. It does not set
up the ISP's Hotspot bridge/DHCP/NAT/VPN, public signup, SaaS subscriptions, multi-
device vouchers, RadSec, HA RADIUS or a full cross-product financial statement.
Real hardware, payment provider and public HTTPS acceptance remain operator gates.

Protocol references: [MikroTik RADIUS](https://help.mikrotik.com/docs/spaces/ROS/pages/328097/RADIUS),
[Hotspot](https://help.mikrotik.com/docs/spaces/ROS/pages/56459266/HotSpot+-+Captive+portal),
[RFC 5176](https://www.freeradius.org/rfc/rfc5176.html).
