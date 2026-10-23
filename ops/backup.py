#!/usr/bin/env python3
"""Encrypted PostgreSQL backups and isolated restore drills; never restores over live data."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive import decrypt, encrypt, key_from_file

ROOT = Path(__file__).resolve().parents[1]


def compose(production=False):
    return ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.production.yml" if production else "docker-compose.override.yml"]


def run(command, **kwargs):
    return subprocess.run(command, check=True, cwd=ROOT, **kwargs)


def private_output(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb")


def make_backup(directory, key_file, production=False):
    cipher = key_from_file(key_file)
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_mode & 0o077:
        raise ValueError("Backup directory must be private (chmod 700).")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    archive = directory / f"{stamp}.dump.enc"
    command = compose(production) + ["exec", "-T", "db", "sh", "-c", 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner']
    with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE) as dump:
        with private_output(archive) as output:
            encrypt(dump.stdout, output, cipher)
        if dump.wait() != 0:
            archive.unlink(missing_ok=True)
            raise RuntimeError("Database backup failed.")
    # Escrow the effective encryption key, not merely a possibly stale host .env.
    code = 'import os,json,django;os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings");django.setup();from django.conf import settings;print(json.dumps({"field_encryption_key":settings.LINTECH_FIELD_ENCRYPTION_KEY,"django_secret_key":settings.SECRET_KEY,"release":getattr(settings,"LINTECH_RELEASE","legacy")}))'
    result = run(compose(production) + ["exec", "-T", "backend", "python", "-c", code], capture_output=True)
    secrets = json.loads(result.stdout)
    secrets["environment_file"] = (ROOT / ".env").read_text() if (ROOT / ".env").exists() else None
    with private_output(directory / f"{stamp}.secrets.enc") as output:
        encrypt(io.BytesIO(json.dumps(secrets).encode()), output, cipher)
    print(f"Encrypted backup created: {archive}")
    return archive


def restore_check(archive, key_file):
    cipher = key_from_file(key_file)
    archive = Path(archive).resolve()
    secrets_file = archive.with_name(archive.name.replace(".dump.enc", ".secrets.enc"))
    secrets_buffer = io.BytesIO()
    with secrets_file.open("rb") as source:
        decrypt(source, secrets_buffer, cipher)
    secrets = json.loads(secrets_buffer.getvalue())
    name = "lintech-restore-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryFile() as dump:
        with archive.open("rb") as source:
            decrypt(source, dump, cipher)
        dump.seek(0)
        run(["docker", "run", "--detach", "--name", name, "--network", "none", "--tmpfs", "/var/lib/postgresql/data", "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-e", "POSTGRES_DB=verify", "postgres:16-alpine"], stdout=subprocess.DEVNULL)
        try:
            for _ in range(60):
                if subprocess.run(["docker", "exec", name, "pg_isready", "-U", "postgres", "-d", "verify"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Isolated restore database did not start.")
            run(["docker", "exec", "-i", name, "pg_restore", "-U", "postgres", "-d", "verify", "--exit-on-error", "--no-owner", "--no-privileges"], stdin=dump, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            sql = "SELECT 'customers=' || count(*) FROM customers_customerprofile; SELECT 'payments=' || count(*) FROM billing_paymenttransaction; SELECT 'organizations=' || count(*) FROM organizations_organization; SELECT 'radius_sessions=' || count(*) FROM radacct;"
            counts = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "verify", "-Atc", sql], capture_output=True).stdout.decode().strip()
            # Confirm the escrowed field key can decrypt an actual restored credential, when present.
            encrypted = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "verify", "-Atc", "SELECT pppoe_pass FROM mikrotik_routerinfo WHERE pppoe_pass LIKE 'lintech:v1:%' LIMIT 1"], capture_output=True).stdout.decode().strip()
            if encrypted:
                from cryptography.fernet import Fernet
                Fernet(secrets["field_encryption_key"].encode()).decrypt(encrypted.removeprefix("lintech:v1:").encode())
            print("PASS: authenticated archive, PostgreSQL restore, core/RADIUS tables and key escrow.")
            print(counts)
            evidence = {"checked_at": datetime.now(timezone.utc).isoformat(), "release": secrets["release"], "counts": counts.splitlines(), "encrypted_credential_verified": bool(encrypted)}
            evidence_path = archive.with_name(archive.name + ".verified.json")
            if evidence_path.exists():
                evidence_path = archive.with_name(archive.name + "." + uuid.uuid4().hex[:8] + ".verified.json")
            with private_output(evidence_path) as output:
                output.write(json.dumps(evidence, indent=2).encode())
        finally:
            run(["docker", "rm", "--force", name], stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "verify"])
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--directory", default=".local/backups")
    parser.add_argument("--archive")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    if args.action == "create":
        make_backup(args.directory, args.key_file, args.production)
    elif args.archive:
        restore_check(args.archive, args.key_file)
    else:
        parser.error("verify requires --archive")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Subprocess output/arguments may contain secrets. Never dump them.
        print(f"Backup operation failed ({type(error).__name__}). Live data was not restored or deleted.", file=sys.stderr)
        sys.exit(1)
