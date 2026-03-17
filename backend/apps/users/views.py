from django.contrib.auth import authenticate
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, MeResponseSerializer, RegisterSerializer, TokenResponseSerializer


def _token_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        'user': {
            'id': user.id,
            'login': user.username,
            'created_at': user.date_joined,
        },
        'token': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _first_error(errors):
    for value in errors.values():
        if isinstance(value, list) and value:
            return str(value[0])
        return str(value)
    return 'Invalid input data'


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=RegisterSerializer,
        responses={
            201: TokenResponseSerializer,
            400: OpenApiResponse(description="Некорректные данные"),
        },
        summary="Регистрация",
        description="Создает пользователя по `login` и `password` и возвращает JWT токены.",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        return Response(_token_response(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            400: OpenApiResponse(description="Некорректные данные"),
            401: OpenApiResponse(description="Неверный логин или пароль"),
        },
        summary="Вход",
        description="Аутентифицирует пользователя по `login` и `password` и возвращает JWT токены.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        login = serializer.validated_data['login']
        password = serializer.validated_data['password']
        user = authenticate(username=login, password=password)

        if user is None:
            return Response({'message': 'Invalid login or password'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(_token_response(user), status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["account"],
        responses={200: MeResponseSerializer},
        summary="Личный кабинет",
        description="Возвращает данные текущего пользователя и количество избранных туров.",
    )
    def get(self, request):
        user = request.user
        favorites_count = getattr(user, "favorites", None).count() if hasattr(user, "favorites") else 0
        return Response(
            {
                "user": {"id": user.id, "login": user.username, "created_at": user.date_joined},
                "favorites_count": favorites_count,
            },
            status=status.HTTP_200_OK,
        )
