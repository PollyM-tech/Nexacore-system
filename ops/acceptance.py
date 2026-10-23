#!/usr/bin/env python3
"""Run the complete backend suite in a disposable PostgreSQL network, not live DB."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid
from cryptography.fernet import Fernet


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def main(image, browser_only=False):
    suffix = uuid.uuid4().hex[:12]
    backend_name, frontend_name = "lintech-test-api-" + suffix, "lintech-test-web-" + suffix
    network, database = "lintech-test-" + suffix, "lintech-test-db-" + suffix
    run(["docker", "network", "create", "--internal", network], stdout=subprocess.DEVNULL)
    try:
        run(["docker", "run", "-d", "--network", network, "--name", database, "--tmpfs", "/var/lib/postgresql/data", "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "postgres:16-alpine"], stdout=subprocess.DEVNULL)
        for _ in range(60):
            if subprocess.run(["docker", "exec", database, "pg_isready", "-U", "postgres"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Acceptance database did not become ready.")
        with tempfile.NamedTemporaryFile(mode="w+", prefix="lintech-tests-", delete=True) as env:
            os.chmod(env.name, 0o600)
            env.write(f"DATABASE_URL=postgres://postgres@{database}:5432/postgres\nLINTECH_ENV=development\nDJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\nLINTECH_FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}\nDJANGO_DEBUG=False\nDJANGO_ALLOWED_HOSTS=testserver,localhost,frontend,backend\nLINTECH_ACCEPTANCE=1\nLINTECH_BROWSER_PASSWORD={secrets.token_urlsafe(24)}\n")
            env.flush()
            if not browser_only:
                run(["docker", "run", "--rm", "--network", network, "--env-file", env.name, image,
                     "python", "manage.py", "test", "core.test_production", "core.test_resource_safety", "hotspot", "customers", "organizations", "platform_api", "auditlog", "billing", "radius", "reports", "customer_portal", "payments", "sms", "olt", "scheduler", "bandwidth", "mikrotik", "--parallel", "4", "--noinput"])
            # The same immutable images are now exercised through actual browser HTTP traffic.
            run(["docker", "run", "--rm", "--network", network, "--env-file", env.name, image, "python", "manage.py", "migrate", "--noinput"])
            run(["docker", "run", "--rm", "--network", network, "--env-file", env.name, image, "python", "-m", "core.acceptance_seed"])
            # Exercise production proxy/cookie/cache settings behind an ephemeral TLS CA.
            env.seek(0)
            values = env.read().replace("LINTECH_ENV=development", "LINTECH_ENV=production")
            values = values.replace(f"postgres://postgres@{database}", f"postgres://postgres:{secrets.token_urlsafe(24)}@{database}")
            env.seek(0)
            env.truncate()
            env.write(values + "DJANGO_CSRF_TRUSTED_ORIGINS=https://frontend\nPUBLIC_BASE_URL=https://frontend\nLINTECH_BROWSER_BASE=https://frontend\n")
            env.flush()
            run(["docker", "run", "--rm", "--network", network, "--env-file", env.name, image, "python", "manage.py", "createcachetable"])
            root = Path(__file__).resolve().parents[1]
            with tempfile.NamedTemporaryFile(mode="w", prefix="lintech-test-caddy-", dir=root / ".local", delete=True) as caddy:
                caddy.write((root / "ops/Caddyfile.production").read_text().replace("{$PUBLIC_DOMAIN} {", "https://frontend {\n    tls internal"))
                caddy.flush()
                run(["docker", "run", "-d", "--network", network, "--network-alias", "backend", "--name", backend_name, "--env-file", env.name, image], stdout=subprocess.DEVNULL)
                run(["docker", "run", "-d", "--network", network, "--network-alias", "frontend", "--name", frontend_name,
                     "-v", caddy.name + ":/etc/caddy/Caddyfile:ro", image.replace("lintech-backend:", "lintech-frontend:")], stdout=subprocess.DEVNULL)
            for _ in range(60):
                if subprocess.run(["docker", "exec", backend_name, "curl", "-fsS", "http://localhost:8000/api/health/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Browser acceptance API did not become ready.")
            root = Path(__file__).resolve().parents[1]
            tools = Path(os.environ.get("LINTECH_PLAYWRIGHT_TOOLS", str(root / ".local/browser-tools"))).resolve()
            if not (tools / "node_modules/playwright/package.json").is_file():
                raise RuntimeError("Install the pinned temporary Playwright tool from the operations runbook before acceptance.")
            results = root / ".local/browser" / image.split(":")[-1]
            results.mkdir(parents=True, exist_ok=True, mode=0o700)
            run(["docker", "run", "--rm", "--ipc=host", "--network", network, "--env-file", env.name,
                 "-v", str(root / "ops") + ":/work/ops:ro", "-v", str(tools) + ":/tools:ro", "-v", str(results) + ":/results",
                 "mcr.microsoft.com/playwright:v1.64.1-noble", "node", "/work/ops/browser.mjs"])
        print("PASS: isolated browser acceptance. No live database or routers were used." if browser_only else "PASS: isolated PostgreSQL and browser acceptance. No live database or routers were used.")
    finally:
        subprocess.run(["docker", "rm", "--force", frontend_name, backend_name, database], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run(["docker", "network", "rm", network], stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--browser-only", action="store_true", help="Debug only; does not qualify a release manifest.")
    args = parser.parse_args()
    main(args.image, browser_only=args.browser_only)
