from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.favorites.models import Favorite
from apps.favorites.serializers import FavoriteCreateSerializer, FavoriteSerializer
from apps.parsed_tours.models import ParsedAvailableTour


class FavoritesListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related("tour", "tour__country")


class FavoritesCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["favorites"],
        request=FavoriteCreateSerializer,
        responses={
            201: FavoriteSerializer,
            400: OpenApiResponse(description="Некорректные данные"),
            404: OpenApiResponse(description="Тур не найден"),
        },
        summary="Добавить в избранное",
    )
    def post(self, request):
        ser = FavoriteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tour_id = ser.validated_data["tour_id"]

        try:
            tour = ParsedAvailableTour.objects.select_related("country").get(id=tour_id)
        except ParsedAvailableTour.DoesNotExist:
            return Response({"message": "Tour not found"}, status=status.HTTP_404_NOT_FOUND)

        fav, _created = Favorite.objects.get_or_create(user=request.user, tour=tour)
        fav = Favorite.objects.select_related("tour", "tour__country").get(id=fav.id)
        return Response(FavoriteSerializer(fav).data, status=status.HTTP_201_CREATED)


class FavoritesDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["favorites"],
        responses={
            204: OpenApiResponse(description="Удалено"),
        },
        summary="Удалить из избранного",
    )
    def delete(self, request, tour_id: int):
        Favorite.objects.filter(user=request.user, tour_id=tour_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

