from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountsTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        res = self.client.post(reverse("signup"), {
            "username": "alice", "email": "a@example.com",
            "password1": "Str0ng-pass-123", "password2": "Str0ng-pass-123",
        })
        self.assertRedirects(res, reverse("analyses:index"))
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_login_and_logout(self):
        User.objects.create_user("bob", password="Str0ng-pass-123")
        res = self.client.post(reverse("login"), {"username": "bob", "password": "Str0ng-pass-123"})
        self.assertRedirects(res, reverse("analyses:index"))
        res = self.client.post(reverse("logout"))
        self.assertRedirects(res, reverse("login"))

    def test_anonymous_redirected_from_index(self):
        res = self.client.get(reverse("analyses:index"))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse("login"), res["Location"])

    def test_anonymous_api_denied(self):
        res = self.client.get("/api/analyses/")
        self.assertIn(res.status_code, (401, 403))

    def test_me_api(self):
        User.objects.create_user("carol", password="Str0ng-pass-123")
        self.client.login(username="carol", password="Str0ng-pass-123")
        res = self.client.get(reverse("me"))
        self.assertEqual(res.json()["username"], "carol")
