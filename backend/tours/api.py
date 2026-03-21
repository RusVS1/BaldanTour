from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.shortcuts import get_object_or_404

from .filters import TourFilter
from .models import Favorite, Tour
from .serializers import TourSerializer


class TourListAPI(ListAPIView):
    serializer_class = TourSerializer
    queryset = Tour.objects.all().prefetch_related("amenities").order_by("price_value", "id")
    filterset_class = TourFilter
    ordering_fields = ["price_value", "nights", "checkin_beg", "checkin_end", "meal", "hotel_category", "id"]
    ordering = ["price_value", "id"]
    search_fields = ["room", "placement", "meal", "raw_text", "description"]


class TourDetailAPI(RetrieveAPIView):
    serializer_class = TourSerializer
    queryset = Tour.objects.all().prefetch_related("amenities")


class FavoriteListAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TourSerializer

    def get(self, request):
        tours = (
            Tour.objects.filter(favorites__user=request.user)
            .prefetch_related("amenities")
            .order_by("price_value", "id")
        )
        return Response(TourSerializer(tours, many=True).data)


class OkSerializer(serializers.Serializer):
    ok = serializers.BooleanField()


class FavoriteToggleAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OkSerializer

    def post(self, request, tour_id: int):
        Favorite.objects.get_or_create(user=request.user, tour_id=tour_id)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)

    def delete(self, request, tour_id: int):
        Favorite.objects.filter(user=request.user, tour_id=tour_id).delete()
        return Response({"ok": True}, status=status.HTTP_200_OK)
