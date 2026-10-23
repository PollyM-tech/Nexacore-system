from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from organizations.models import Organization, OrganizationMembership
from auditlog.models import AuditLog


class LaunchSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_superuser(username="owner", email="owner@example.test", password="Strong!temporary8792")
        self.org = Organization.objects.create(name="Pilot ISP", slug="pilot")
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role="owner")
        self.client = APIClient()

    def test_public_signup_closed_even_for_superuser(self):
        before = get_user_model().objects.count()
        for authenticated in [False, True]:
            self.client.force_authenticate(self.user if authenticated else None)
            response = self.client.post("/api/auth/registration/", {"email": "new@example.test", "password1": "Strong!8792temporary", "password2": "Strong!8792temporary"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(get_user_model().objects.count(), before)

    def test_actual_cookie_login_and_csrf_protected_write(self):
        client = APIClient(enforce_csrf_checks=True)
        body = {"email": self.user.email, "password": "Strong!temporary8792"}
        self.assertEqual(client.post("/api/auth/login/", body).status_code, 403)
        self.assertEqual(client.get("/api/auth/csrf/").status_code, 200)
        csrf = client.cookies["csrftoken"].value
        response = client.post("/api/auth/login/", body, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200, response.data)
        cookie = response.cookies["auth-jwt"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(client.get("/api/auth/user/").status_code, 200)
        self.assertEqual(client.patch("/api/auth/user/", {"first_name": "No CSRF"}).status_code, 403)
        self.assertEqual(client.patch("/api/auth/user/", {"first_name": "Pilot"}, HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        self.assertEqual(client.patch("/api/auth/user/", {"first_name": "Bad origin"}, HTTP_X_CSRFTOKEN=csrf, HTTP_ORIGIN="https://untrusted.example").status_code, 403)
        self.assertEqual(client.post("/api/auth/token/refresh/", {}).status_code, 403)

    def test_superadmin_can_provision_standard_owner_with_safe_audit(self):
        self.client.force_authenticate(self.user)
        body = {"username": "pilot-owner", "email": "Pilot@example.test", "password": "Strong!temporary3892", "role": "owner", "is_superuser": True}
        response = self.client.post(f"/api/platform/organizations/{self.org.pk}/users/", body)
        self.assertEqual(response.status_code, 201, response.data)
        created = get_user_model().objects.get(username="pilot-owner")
        self.assertTrue(created.check_password(body["password"]))
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertEqual(created.email, "pilot@example.test")
        self.assertNotIn("password", str(response.data))
        self.assertNotIn(body["password"], str(list(AuditLog.objects.values_list("metadata", flat=True))))
        self.assertEqual(self.client.post(f"/api/platform/organizations/{self.org.pk}/users/", body).status_code, 400)

    def test_ordinary_owner_cannot_provision_global_user(self):
        self.user.is_superuser = False
        self.user.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(f"/api/platform/organizations/{self.org.pk}/users/", {}).status_code, 403)

    def test_invalid_password_or_role_does_not_create_account(self):
        self.client.force_authenticate(self.user)
        for password, role in [("123", "owner"), ("Strong!temporary3892", "superadmin")]:
            response = self.client.post(f"/api/platform/organizations/{self.org.pk}/users/", {"username": "invalid-user", "email": "invalid@example.test", "password": password, "role": role})
            self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username="invalid-user").exists())

    def test_bearer_api_client_not_subject_to_cookie_csrf(self):
        token = str(RefreshToken.for_user(self.user).access_token)
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.patch("/api/auth/user/", {"first_name": "Script"}).status_code, 200)

    def test_login_throttles_bad_attempts(self):
        for _ in range(10):
            self.client.post("/api/auth/login/", {"email": "absent@example.test", "password": "wrong"})
        self.assertEqual(self.client.post("/api/auth/login/", {"email": "absent@example.test", "password": "wrong"}).status_code, 429)

    def test_correct_secure_cookie_setting_is_configured(self):
        self.assertIn("AUTH_COOKIE_SECURE", settings.AUTH_KIT)
        self.assertNotIn("AUTH_JWT_COOKIE_SECURE", settings.AUTH_KIT)

    def test_health_is_non_sensitive(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"status", "release"})


    def test_logout_blacklists_refresh_token(self):
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        refresh = RefreshToken.for_user(self.user)
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["auth-jwt"] = str(refresh.access_token)
        client.cookies["auth-refresh-jwt"] = str(refresh)
        client.get("/api/auth/csrf/")
        csrf = client.cookies["csrftoken"].value
        response = client.post("/api/auth/logout/", {}, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists())
        self.assertIn(client.post("/api/auth/token/refresh/", {"refresh": str(refresh)}, HTTP_X_CSRFTOKEN=csrf).status_code, (400, 401))

    def test_password_change_revokes_existing_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        self.assertEqual(client.post("/api/auth/password/change/", {"old_password": "Strong!temporary8792", "new_password1": "New!secure789password", "new_password2": "New!secure789password"}).status_code, 200)
        self.assertEqual(client.get("/api/auth/user/").status_code, 401)
