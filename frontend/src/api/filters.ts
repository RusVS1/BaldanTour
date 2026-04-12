import { apiFetch } from './api';

export type TourBase = {
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
  buy_link?: string | null;
  meta: {
    townfrom: string;
    country_slug: string;
    rest_type: string;
    hotel_type: string;
    hotel_category: string | number | null;
    meal: string | null;
  };
};

export type Tour = TourBase & {
  hotel_slug: string;
  hotel_stars?: number | null;
  hotel_type: string | null;
  meal: string | null;
  common_description: string;
  target_description: string;
  meta?: Record<string, string>;
};

export type FavoriteTour = TourBase;

export type FilterOption = {
  label: string;
  value: string | number;
};

export type RegularSearchParams = {
  from: string | null;
  to: string | null;
  dateFrom: string;
  dateTo: string;
  nights: number | null;
  adults: number;
  children: number;
};

export type AiSearchParams = {
  aiQuery: string;
  tab: 'ai';
};

export type SearchParams = RegularSearchParams | AiSearchParams;

export type FilterParams = {
  type?: string | null;
  priceFrom?: number | null;
  priceTo?: number | null;
  hotelType?: string | null;
  category?: string | null;
  food?: string | null;
  sort?: string | null;
};

export type SearchResponse = {
  meta: {
    requested: Record<string, unknown>;
    page: number;
    page_size: number;
    count: number;
  };
  results: Tour[];
};

export const aiSearch = (query: string) => {
  return apiFetch<SearchResponse>('/api/ai/search/', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
};

export const getFilterOptions = {
  country: () => apiFetch<{ values: FilterOption[] }>('/api/filters/country/'),
  hotelCategory: () => apiFetch<{ values: FilterOption[] }>('/api/filters/hotel-category/'),
  hotelType: () => apiFetch<{ values: string[] }>('/api/filters/hotel-type/'),
  meal: () => apiFetch<{ values: string[] }>('/api/filters/meal/'),
  restType: () => apiFetch<{ values: string[] }>('/api/filters/rest-type/'),
  townFrom: () => apiFetch<{ values: FilterOption[] }>('/api/filters/townfrom/'),
};

export const searchTours = (
  searchParams: RegularSearchParams | AiSearchParams,
  filterParams?: FilterParams,
) => {
  const convertDate = (date: string): string => {
    if (!date || !date.includes('.')) return date;
    const [day, month] = date.split('.');
    const year = new Date().getFullYear();
    return `${year}-${month?.padStart(2, '0')}-${day?.padStart(2, '0')}`;
  };

  const payload: Record<string, unknown> = {};

  if ('from' in searchParams) {
    payload.townfrom = searchParams.from ?? undefined;
    payload.country_slug = searchParams.to ?? undefined;
    payload.departure_from = searchParams.dateFrom ? convertDate(searchParams.dateFrom) : undefined;
    payload.departure_to = searchParams.dateTo ? convertDate(searchParams.dateTo) : undefined;
    payload.nights_min = searchParams.nights ?? undefined;
    payload.nights_max = searchParams.nights ?? undefined;
    payload.adult = searchParams.adults ?? undefined;
    payload.child = searchParams.children ?? undefined;
  }

  if ('aiQuery' in searchParams) {
    payload.query = searchParams.aiQuery;
  }

  if (filterParams) {
    if (filterParams.type) payload.rest_type = filterParams.type;
    if (filterParams.priceFrom != null) payload.price_from = filterParams.priceFrom;
    if (filterParams.priceTo != null) payload.price_to = filterParams.priceTo;
    if (filterParams.hotelType) payload.hotel_type = filterParams.hotelType;
    if (filterParams.category != null) payload.hotel_category = filterParams.category;
    if (filterParams.food) payload.meal = filterParams.food;
    if (filterParams.sort) payload.sort = filterParams.sort;
  }

  const queryString = new URLSearchParams(
    Object.entries(payload)
      .filter(([, value]) => value != null)
      .map(([k, v]) => [k, String(v)]),
  ).toString();

  return apiFetch<SearchResponse>(`/api/tours/?${queryString}`);
};

export const formatOptions = (values: (string | number | FilterOption)[]): FilterOption[] => {
  return values.map((v) => {
    if (typeof v === 'object' && v !== null && 'label' in v && 'value' in v) {
      return v;
    }
    return {
      label: String(v),
      value: v,
    };
  });
};

export const formatSlugOptions = (values: FilterOption[]): FilterOption[] => {
  return values;
};

export const cleanFilters = <T extends Record<string, unknown>>(filters: T): Partial<T> => {
  return Object.fromEntries(
    Object.entries(filters).filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    ),
  ) as Partial<T>;
};
