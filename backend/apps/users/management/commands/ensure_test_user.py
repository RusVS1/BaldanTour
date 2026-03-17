from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure a test user exists (for Swagger/manual testing)."

    def add_arguments(self, parser):
        parser.add_argument("--login", dest="login", default=os.getenv("TEST_USER_LOGIN", "db_test_user"))
        parser.add_argument(
            "--password",
            dest="password",
            default=os.getenv("TEST_USER_PASSWORD", "db_test_password_123"),
        )

    def handle(self, *args, **options):
        login = str(options["login"]).strip()
        password = str(options["password"])
        if not login:
            raise SystemExit("login is required")
        if len(password) < 8:
            raise SystemExit("password must be at least 8 chars")

        User = get_user_model()
        user, created = User.objects.get_or_create(username=login, defaults={"is_active": True})
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"[created] {login}"))
            return

        # Ensure password matches what we expect (idempotent for dev).
        if not user.check_password(password):
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(self.style.WARNING(f"[updated password] {login}"))
        else:
            self.stdout.write(f"[ok] {login}")

