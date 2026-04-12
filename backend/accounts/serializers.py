import re

from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from rest_framework import serializers


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MAX_PASSWORD_LENGTH = 128


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=32, trim_whitespace=True)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=MAX_PASSWORD_LENGTH,
        trim_whitespace=False,
    )

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Введите логин.")
        if not USERNAME_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Логин должен быть 3-32 символа: латиница, цифры, точка, дефис или подчёркивание."
            )
        normalized = value.lower()
        if User.objects.filter(username__iexact=normalized).exists():
            raise serializers.ValidationError("Пользователь уже существует.")
        return normalized

    def validate_password(self, value: str) -> str:
        if len(value) > MAX_PASSWORD_LENGTH:
            raise serializers.ValidationError("Пароль слишком длинный: максимум 128 символов.")
        if value != value.strip() or any(ch.isspace() for ch in value):
            raise serializers.ValidationError("Пароль не должен содержать пробелы или переносы строк.")
        return value

    def validate(self, attrs):
        password_validation.validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=32, trim_whitespace=True)
    password = serializers.CharField(
        write_only=True,
        max_length=MAX_PASSWORD_LENGTH,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        username = (attrs.get("username") or "").strip().lower()
        password = attrs.get("password") or ""
        if not USERNAME_RE.fullmatch(username) or len(password) > MAX_PASSWORD_LENGTH:
            raise serializers.ValidationError("Неверный пользователь/пароль.")
        user = authenticate(username=username, password=password)
        if user is None:
            raise serializers.ValidationError("Неверный пользователь/пароль.")
        if not user.is_active:
            raise serializers.ValidationError("Пользователь не активен.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "is_staff", "is_superuser"]


class UserEnvelopeSerializer(serializers.Serializer):
    user = UserSerializer()


class AuthStatusSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserSerializer(allow_null=True, required=False)


class OkSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
