import os
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from core.settings import (
    _environment_flag,
    _environment_list,
    _required_secret_key,
)


class SecurityEnvironmentSettingsTests(SimpleTestCase):
    def test_secret_key_is_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesMessage(
                ImproperlyConfigured, "DJANGO_SECRET_KEY must be set"
            ):
                _required_secret_key()

    def test_secret_key_is_trimmed(self):
        with patch.dict(os.environ, {"DJANGO_SECRET_KEY": "  test-secret  "}):
            self.assertEqual(_required_secret_key(), "test-secret")

    def test_debug_defaults_to_false(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_environment_flag("DJANGO_DEBUG", default=False))

    def test_boolean_environment_values_are_parsed_strictly(self):
        for value in ("1", "true", "YES", "on"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"DJANGO_DEBUG": value}
            ):
                self.assertTrue(_environment_flag("DJANGO_DEBUG"))

        for value in ("0", "false", "NO", "off"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"DJANGO_DEBUG": value}
            ):
                self.assertFalse(_environment_flag("DJANGO_DEBUG"))

    def test_invalid_boolean_environment_value_fails_fast(self):
        with patch.dict(os.environ, {"DJANGO_DEBUG": "sometimes"}):
            with self.assertRaisesMessage(
                ImproperlyConfigured, "DJANGO_DEBUG must be one of"
            ):
                _environment_flag("DJANGO_DEBUG")

    def test_allowed_hosts_are_trimmed_and_empty_entries_removed(self):
        with patch.dict(
            os.environ,
            {"DJANGO_ALLOWED_HOSTS": " example.com, , api.example.com "},
        ):
            self.assertEqual(
                _environment_list("DJANGO_ALLOWED_HOSTS", default=[]),
                ["example.com", "api.example.com"],
            )

    def test_empty_allowed_hosts_environment_value_fails_fast(self):
        with patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": " , "}):
            with self.assertRaisesMessage(
                ImproperlyConfigured, "DJANGO_ALLOWED_HOSTS must contain"
            ):
                _environment_list("DJANGO_ALLOWED_HOSTS", default=[])

    def test_default_allowed_hosts_are_local_only(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                _environment_list(
                    "DJANGO_ALLOWED_HOSTS",
                    default=["localhost", "127.0.0.1", "testserver"],
                ),
                ["localhost", "127.0.0.1", "testserver"],
            )

    def test_cookie_transport_security_tracks_debug_mode(self):
        self.assertEqual(settings.SESSION_COOKIE_SECURE, not settings.DEBUG)
        self.assertEqual(settings.CSRF_COOKIE_SECURE, not settings.DEBUG)
