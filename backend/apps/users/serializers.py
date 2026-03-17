from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    login = serializers.RegexField(regex=r'^[A-Za-z0-9_.-]{3,64}$')
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_login(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('User with this login already exists')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['login'],
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TokenUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    login = serializers.CharField()
    created_at = serializers.DateTimeField()


class TokenResponseSerializer(serializers.Serializer):
    user = TokenUserSerializer()
    token = serializers.CharField()
    refresh = serializers.CharField()


class MeResponseSerializer(serializers.Serializer):
    user = TokenUserSerializer()
    favorites_count = serializers.IntegerField()
