import { apiFetch } from './api';

export type FavoriteTour = {
  id: number;
  base_link?: string | null;
  hotel_name: string;
  hotel_rating: string | null;
  trip_dates?: string;
  departure_from?: string | null;
  departure_to?: string | null;
  nights?: number | null;
  price_per_person: number;
  answer_description: string;
  main_image_url: string | null;
  booking_url?: string | null;
  buy_link: string;
  meta: {
    townfrom: string;
    country_slug: string;
    rest_type: string;
    hotel_type: string;
    hotel_category: string | number | null;
    meal: string | null;
  };
};

export function getFavorites(userId: number) {
  return apiFetch<{ results: FavoriteTour[] }>(`/api/favorites/${userId}/`);
}

export function addFavorite(userId: number, tourId: number) {
  return apiFetch(`/api/favorites/${userId}/`, {
    method: 'POST',
    body: JSON.stringify({ tour_id: tourId }),
  });
}

export function removeFavorite(userId: number, tourId: number) {
  return apiFetch(`/api/favorites/${userId}/${tourId}/`, {
    method: 'DELETE',
  });
}

export type FilterOption = {
  label: string;
  value: string | number;
};

export const getFavoriteFilters = {
  country: (userId: number) =>
    apiFetch<{ values: FilterOption[] }>(`/api/favorites/${userId}/filters/country/`),
  hotelCategory: (userId: number) =>
    apiFetch<{ values: FilterOption[] }>(`/api/favorites/${userId}/filters/hotel-category/`),
  hotelType: (userId: number) =>
    apiFetch<{ values: string[] }>(`/api/favorites/${userId}/filters/hotel-type/`),
  meal: (userId: number) =>
    apiFetch<{ values: string[] }>(`/api/favorites/${userId}/filters/meal/`),
  restType: (userId: number) =>
    apiFetch<{ values: string[] }>(`/api/favorites/${userId}/filters/rest-type/`),
  townFrom: (userId: number) =>
    apiFetch<{ values: FilterOption[] }>(`/api/favorites/${userId}/filters/townfrom/`),
};
