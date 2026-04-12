from django.contrib.auth import login as session_login, logout as session_logout
from django.core.cache import cache
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    AuthStatusSerializer,
    LoginSerializer,
    OkSerializer,
    RegisterSerializer,
    UserEnvelopeSerializer,
    UserSerializer,
)


def _client_ip(request) -> str:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR") or "unknown"


class RegisterAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=RegisterSerializer, responses={201: UserEnvelopeSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        session_login(request, user)

        return Response(
            {"user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses={200: UserEnvelopeSerializer})
    def post(self, request):
        username = (request.data.get("username") or "").strip().lower()
        cache_key = f"auth:login:{_client_ip(request)}:{username}"
        failures = int(cache.get(cache_key, 0) or 0)
        if failures >= 5:
            return Response(
                {"error": "too_many_attempts", "detail": "Слишком много попыток входа. Повторите позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            cache.set(cache_key, failures + 1, timeout=15 * 60)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.validated_data["user"]

        session_login(request, user)
        cache.delete(cache_key)
        cache.set(f"audit:login:{user.id}:{timezone.now().timestamp()}", _client_ip(request), timeout=24 * 60 * 60)

        return Response({"user": UserSerializer(user).data})


class LogoutAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: OkSerializer})
    def post(self, request):
        session_logout(request)
        return Response({"ok": True})


class MeAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: UserEnvelopeSerializer})
    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


class AuthStatusAPI(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: AuthStatusSerializer})
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": UserSerializer(request.user).data})
