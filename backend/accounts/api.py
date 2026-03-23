from django.contrib.auth import login as session_login, logout as session_logout
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AuthStatusSerializer,
    LoginSerializer,
    OkSerializer,
    RegisterSerializer,
    UserEnvelopeSerializer,
    UserSerializer,
)


class RegisterAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

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

    @extend_schema(request=LoginSerializer, responses={200: UserEnvelopeSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        session_login(request, user)

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
