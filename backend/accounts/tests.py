from django.test import TestCase

from .serializers import RegisterSerializer


class RegisterSerializerTests(TestCase):
    def test_rejects_case_duplicate_usernames(self):
        serializer = RegisterSerializer(data={"username": "TestUser", "password": "StrongPass123"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        duplicate = RegisterSerializer(data={"username": "testuser", "password": "StrongPass123"})
        self.assertFalse(duplicate.is_valid())

    def test_rejects_unsafe_username_and_password_whitespace(self):
        serializer = RegisterSerializer(data={"username": "иван", "password": "StrongPass123"})
        self.assertFalse(serializer.is_valid())

        serializer = RegisterSerializer(data={"username": "safe_user", "password": "Strong Pass 123"})
        self.assertFalse(serializer.is_valid())
