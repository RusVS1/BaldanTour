# backend/tests/test_auth.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

@pytest.mark.django_db
class TestRegistration:
    def test_register_new_user(self, api_client):
        """Успешная регистрация"""
        response = api_client.post("/api/auth/register/", {
            "username": "newuser",
            "email": "new@test.com",
            "password": "SecurePass123!"
        }, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert response.data["user"]["username"] == "newuser"
        assert User.objects.filter(username="newuser").exists()

    def test_register_duplicate_username(self, api_client):
        """Регистрация с существующим логином"""
        User.objects.create_user(username="existing", password="pass")
        
        response = api_client.post("/api/auth/register/", {
            "username": "existing",
            "email": "dup@test.com",
            "password": "pass"
        }, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data

@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client):
        """Успешный вход"""
        User.objects.create_user(username="testuser", password="TestPass123!")
        
        response = api_client.post("/api/auth/login/", {
            "username": "testuser",
            "password": "TestPass123!"
        }, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert response.data["user"]["username"] == "testuser"

    def test_login_wrong_password(self, api_client):
        """Вход с неверным паролем"""
        User.objects.create_user(username="testuser", password="CorrectPass")
        
        response = api_client.post("/api/auth/login/", {
            "username": "testuser",
            "password": "WrongPass"
        }, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

@pytest.mark.django_db
class TestLogout:
    def test_logout_authenticated(self, authenticated_client):
        """Выход из системы"""
        response = authenticated_client.post("/api/auth/logout/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["ok"] is True

    def test_logout_unauthenticated(self, api_client):
        """Выход без авторизации"""
        response = api_client.post("/api/auth/logout/")
        # DRF может вернуть 401 или 403 — оба допустимы
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

@pytest.mark.django_db
class TestProfile:
    def test_get_profile_authenticated(self, authenticated_client):
        """Получение профиля авторизованного пользователя"""
        response = authenticated_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["username"] == "testuser"

    def test_get_profile_unauthenticated(self, api_client):
        """Получение профиля без авторизации"""
        response = api_client.get("/api/auth/me/")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_auth_status(self, api_client):
        """Проверка статуса аутентификации"""
        # Без авторизации
        response = api_client.get("/api/auth/status/")
        assert response.data["authenticated"] is False
        
        # С авторизацией
        User.objects.create_user(username="statuser", password="pass")
        api_client.login(username="statuser", password="pass")
        response = api_client.get("/api/auth/status/")
        assert response.data["authenticated"] is True