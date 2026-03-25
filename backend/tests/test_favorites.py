# backend/tests/test_favorites.py
import pytest
from rest_framework import status
from tours.models import Favorite, Tour

@pytest.mark.django_db
class TestFavoritesAccess:
    def test_get_favorites_own(self, authenticated_client, sample_tours):
        """Пользователь получает своё избранное"""
        # Добавляем тур в избранное
        Favorite.objects.create(user=authenticated_client.test_user, tour=sample_tours[0])
        
        response = authenticated_client.get(f"/api/favorites/{authenticated_client.test_user.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["meta"]["user_id"] == authenticated_client.test_user.id
        assert len(response.data["results"]) >= 1

    def test_get_favorites_other_user(self, authenticated_client, another_user, sample_tours):
        """Попытка получить избранное другого пользователя (IDOR)"""
        # Добавляем тур в избранное другому пользователю
        Favorite.objects.create(user=another_user, tour=sample_tours[0])
        
        response = authenticated_client.get(f"/api/favorites/{another_user.id}/")
        # Должен быть запрещён доступ
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_add_to_favorites(self, authenticated_client, sample_tours):
        """Добавление тура в избранное"""
        tour = sample_tours[0]
        response = authenticated_client.post(
            f"/api/favorites/{authenticated_client.test_user.id}/",
            {"tour_id": tour.id},
            format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["ok"] is True
        assert Favorite.objects.filter(
            user=authenticated_client.test_user, tour=tour
        ).exists()

    def test_remove_from_favorites(self, authenticated_client, sample_tours):
        """Удаление тура из избранного"""
        tour = sample_tours[0]
        Favorite.objects.create(user=authenticated_client.test_user, tour=tour)
        
        response = authenticated_client.delete(
            f"/api/favorites/{authenticated_client.test_user.id}/{tour.id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["ok"] is True
        assert not Favorite.objects.filter(
            user=authenticated_client.test_user, tour=tour
        ).exists()

@pytest.mark.django_db
class TestFavoritesFilters:
    def test_favorite_filter_country(self, authenticated_client, sample_tours):
        """Фильтрация избранного по стране"""
        user = authenticated_client.test_user
        # Добавляем туры разных стран в избранное
        for tour in sample_tours:
            Favorite.objects.create(user=user, tour=tour)
        
        response = authenticated_client.get(
            f"/api/favorites/{user.id}/filters/country/"
        )
        assert response.status_code == status.HTTP_200_OK
        countries = [v["value"] for v in response.data["values"]]
        assert "abkhazia" in countries
        assert "belarus" in countries