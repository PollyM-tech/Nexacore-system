import os
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from backend.config.production import apply


class ProductionConfigurationTests(unittest.TestCase):
    def setup_settings(self):
        key = Fernet.generate_key().decode()
        env = {"LINTECH_ENV": "production", "DJANGO_SECRET_KEY": "long-unique-production-secret-example-with-many-characters-9876543210", "LINTECH_FIELD_ENCRYPTION_KEY": key, "DATABASE_URL": "postgres://test:test@db/test", "DJANGO_ALLOWED_HOSTS": "billing.example.net", "DJANGO_CSRF_TRUSTED_ORIGINS": "https://billing.example.net"}
        settings = {"SECRET_KEY": env["DJANGO_SECRET_KEY"], "LINTECH_FIELD_ENCRYPTION_KEY": key, "DEBUG": False, "ALLOWED_HOSTS": [env["DJANGO_ALLOWED_HOSTS"]], "CSRF_TRUSTED_ORIGINS": [env["DJANGO_CSRF_TRUSTED_ORIGINS"]], "DATABASES": {"default": {"ENGINE": "django.db.backends.postgresql", "PASSWORD": "long-database-password-123456789"}}, "REST_FRAMEWORK": {}, "AUTH_KIT": {}}
        return env, settings

    def test_production_has_secure_cookies_redirects_and_shared_throttling(self):
        env, settings = self.setup_settings()
        with patch.dict(os.environ, env, clear=True):
            apply(settings)
        for name in ["SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"]:
            self.assertTrue(settings[name])
        self.assertTrue(settings["AUTH_KIT"]["AUTH_COOKIE_SECURE"])
        self.assertGreater(settings["SECURE_HSTS_SECONDS"], 0)
        self.assertEqual(settings["CACHES"]["default"]["BACKEND"], "django.core.cache.backends.db.DatabaseCache")

    def test_bad_production_settings_fail_closed(self):
        for field, value in [("DEBUG", True), ("ALLOWED_HOSTS", ["*"]), ("SECRET_KEY", "change-me"), ("CSRF_TRUSTED_ORIGINS", ["http://billing.example.net"]), ("LINTECH_FIELD_ENCRYPTION_KEY", "invalid")]:
            env, settings = self.setup_settings()
            settings[field] = value
            with patch.dict(os.environ, env, clear=True), self.assertRaises(ImproperlyConfigured):
                apply(settings)

    def test_missing_production_configuration_fails_closed(self):
        _, settings = self.setup_settings()
        with patch.dict(os.environ, {"LINTECH_ENV": "production"}, clear=True), self.assertRaises(ImproperlyConfigured):
            apply(settings)

    def test_localhost_is_not_forced_to_https(self):
        settings = {"DEBUG": True}
        with patch.dict(os.environ, {"LINTECH_ENV": "development"}, clear=True):
            apply(settings)
        self.assertEqual(settings, {"DEBUG": True})
