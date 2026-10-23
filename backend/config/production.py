"""Fail-closed production configuration. Local development stays HTTP-compatible."""
import os
import ipaddress
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet


def apply(settings):
    if os.environ.get("LINTECH_ENV", "development") != "production":
        return
    required = ["DJANGO_SECRET_KEY", "LINTECH_FIELD_ENCRYPTION_KEY", "DATABASE_URL", "DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS"]
    if any(not os.environ.get(name, "").strip() for name in required):
        raise ImproperlyConfigured("Production requires explicit secrets, database, hosts and trusted HTTPS origins.")
    secret = settings["SECRET_KEY"]
    if len(secret) < 50 or len(set(secret)) < 5 or secret.startswith("django-insecure-"):
        raise ImproperlyConfigured("Production requires a strong Django secret key.")
    if settings["DEBUG"] or "*" in settings["ALLOWED_HOSTS"]:
        raise ImproperlyConfigured("Production prohibits DEBUG and wildcard hosts.")
    if any(not origin.startswith("https://") or "*" in origin for origin in settings["CSRF_TRUSTED_ORIGINS"]):
        raise ImproperlyConfigured("Production trusted origins must be explicit HTTPS origins.")
    try:
        Fernet(settings["LINTECH_FIELD_ENCRYPTION_KEY"].encode())
    except (ValueError, TypeError):
        raise ImproperlyConfigured("Production requires a valid field encryption key.") from None
    if settings["DATABASES"]["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise ImproperlyConfigured("Production requires PostgreSQL.")
    if len(settings["DATABASES"]["default"].get("PASSWORD", "")) < 20:
        raise ImproperlyConfigured("Production requires a strong database password (at least 20 characters).")
    if settings.get('RADIUS_ISOLATED'):
        if len(settings.get('RADIUS_INTERNAL_TOKEN', '')) < 32:
            raise ImproperlyConfigured('Registered-NAS mode requires a strong internal RADIUS bridge token.')
        try:
            network = ipaddress.ip_network(settings.get('RADIUS_NAS_NETWORK', ''))
            if network.version != 4 or not 8 <= network.prefixlen <= 31:
                raise ValueError()
        except ValueError:
            raise ImproperlyConfigured('Registered-NAS mode requires an explicit trusted IPv4 NAS/VPN subnet (/8 through /31).') from None
    settings.update(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "lintech_cache", "TIMEOUT": 300, "OPTIONS": {"MAX_ENTRIES": 10000}}},
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        SECURE_HSTS_SECONDS=int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "3600")),
        SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
        SECURE_HSTS_PRELOAD=False,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_CONTENT_TYPE_NOSNIFF=True,
        SECURE_REFERRER_POLICY="same-origin",
        SECURE_REDIRECT_EXEMPT=[r"^api/health/$", r"^api/internal/radius/"],
    )
    settings["REST_FRAMEWORK"]["DEFAULT_RENDERER_CLASSES"] = ["rest_framework.renderers.JSONRenderer"]
    settings["AUTH_KIT"]["AUTH_COOKIE_SECURE"] = True
