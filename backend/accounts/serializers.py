from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Введите пользователя.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь уже существует.")
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
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=(attrs.get("username") or "").strip(),
            password=attrs.get("password") or "",
        )
        if user is None:
            raise serializers.ValidationError("Неверный пользователь\пароль.")
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
