#!/usr/bin/env python3
"""Build/verify matching release images and deploy only after a verified backup."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup import compose, make_backup, restore_check
from acceptance import main as acceptance


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def source_hash():
    paths = run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], capture_output=True).stdout.split(b"\0")
    digest = hashlib.sha256()
    for raw in sorted(set(paths)):
        if not raw:
            continue
        path = ROOT / os.fsdecode(raw)
        if path.is_file():
            digest.update(raw + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def image_id(name):
    return run(["docker", "image", "inspect", name, "--format", "{{.Id}}"], capture_output=True).stdout.decode().strip()


def build():
    digest = source_hash()
    release = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + digest[:12]
    env = dict(os.environ, LINTECH_RELEASE=release)
    command = compose(False)
    run(command + ["build", "backend", "frontend", "freeradius"], env=env)
    if source_hash() != digest:
        raise RuntimeError("Source changed during build; discard this release and build again.")
    acceptance(f"lintech-backend:{release}")
    from network_acceptance import main as network_acceptance
    network_acceptance(f"lintech-backend:{release}", f"lintech-freeradius:{release}")
    for script in ["check-admin.mjs", "check-platform.mjs", "check-landing.mjs", "check-currency.mjs"]:
        subprocess.run(["node", "scripts/" + script], cwd=ROOT / "frontend", check=True)
    run([sys.executable, "-m", "unittest", "ops.test_archive", "ops.test_production_config"])
    run(["git", "diff", "--check"])
    if source_hash() != digest:
        raise RuntimeError("Source changed during acceptance; build a fresh release.")
    images = {name: {"tag": f"lintech-{name}:{release}", "id": image_id(f"lintech-{name}:{release}")} for name in ["backend", "frontend", "freeradius"]}
    manifest = {"release": release, "source_sha256": digest, "created_at": datetime.now(timezone.utc).isoformat(), "images": images, "automated_acceptance": "passed", "network_acceptance": "passed-registered-NAS-hotspot-pppoe-disconnect", "browser_acceptance": "passed-Chromium-desktop-mobile", "live_provider_acceptance": "operator-required"}
    directory = ROOT / ".local/releases"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"{release}.json"
    path.write_text(json.dumps(manifest, indent=2))
    print(f"Validated release manifest: {path}")


def deploy(path, key_file, production):
    manifest = json.loads(Path(path).read_text())
    if manifest.get("automated_acceptance") != "passed":
        raise RuntimeError("Release has not passed automated acceptance.")
    for image in manifest["images"].values():
        if image_id(image["tag"]) != image["id"]:
            raise RuntimeError("An image tag changed after validation. Deployment refused.")
    env = dict(os.environ, LINTECH_RELEASE=manifest["release"])
    config = json.loads(run(compose(production) + ["config", "--format", "json"], env=env, capture_output=True).stdout)
    expected = config["services"]["backend"]["environment"]
    code = 'import os,json,django;os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings");django.setup();from django.conf import settings;print(json.dumps({"LINTECH_FIELD_ENCRYPTION_KEY":settings.LINTECH_FIELD_ENCRYPTION_KEY,"DJANGO_SECRET_KEY":settings.SECRET_KEY}))'
    current = json.loads(run(compose(production) + ["exec", "-T", "backend", "python", "-c", code], capture_output=True).stdout)
    if any(current[key] != expected.get(key) for key in current):
        raise RuntimeError("Deployment would change a running encryption/signing key. Refused; plan key rotation separately.")
    radius_secret = run(compose(production) + ["exec", "-T", "freeradius", "printenv", "RADIUS_SHARED_SECRET"], capture_output=True).stdout.decode().rstrip("\n")
    if radius_secret != config["services"]["freeradius"]["environment"]["RADIUS_SHARED_SECRET"]:
        raise RuntimeError("Deployment would change the running RADIUS secret. Refused; plan NAS rotation separately.")
    directory = ROOT / ".local/deployments"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    previous = run(compose(production) + ["ps", "--format", "json"], capture_output=True).stdout
    with os.fdopen(os.open(directory / (manifest["release"] + ".previous.json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        output.write(previous)
    # Do not derive the currently running release from mutable source or tags.
    run(compose(production) + ["stop", "qcluster"])
    env = dict(os.environ, LINTECH_RELEASE=manifest["release"])
    try:
        archive = make_backup(ROOT / ".local/backups", key_file, production)
        restore_check(archive, key_file)
        run(compose(production) + ["stop", "backend"])
        # Explicit one-shot migrations precede all new processes.
        run(compose(production) + ["run", "--rm", "--no-deps", "backend", "migrate"], env=env)
        run(compose(production) + ["up", "-d", "--no-build", "--wait", "--wait-timeout", "120", "backend", "qcluster", "frontend", "freeradius"], env=env)
        result = run(compose(production) + ["exec", "-T", "backend", "python", "-c", 'import os;print(os.environ.get("LINTECH_RELEASE", ""))'], env=env, capture_output=True)
        if result.stdout.decode().strip() != manifest["release"]:
            raise RuntimeError("Running release does not match the validated manifest.")
        print("PASS: verified-backup deployment completed. Run the manual acceptance checklist before a pilot.")
    except Exception:
        # Never auto-restore a database or blindly roll back schema changes.
        print("Deployment stopped. Keep traffic closed; inspect logs and follow the recovery runbook.", file=sys.stderr)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "deploy"])
    parser.add_argument("--manifest")
    parser.add_argument("--key-file")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    if args.action == "build":
        build()
    elif args.manifest and args.key_file:
        deploy(args.manifest, args.key_file, args.production)
    else:
        parser.error("deploy requires --manifest and --key-file")
