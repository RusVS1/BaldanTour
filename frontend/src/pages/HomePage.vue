<template>
  <q-page class="q-pa-lg">
    <div class="row justify-center">
      <SearchBar
        class="q-mb-md border-radius-md col-12 col-md-10"
        @search="handleSearch"
      />
    </div>

    <div class="row q-col-gutter-lg">
      <div class="col-12 col-md-3">
        <FiltersSidebar
          ref="filtersRef"
          class="border-radius-md"
          style="position: sticky; top: 90px"
          @filter-change="handleFilterChange"
        />
      </div>

      <div class="col-12 col-md-9">
        <ToursList
          :tours="displayedTours"
          :has-searched="hasSearched"
          :loading="loading"
          :is-ai="isAiSearch"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import SearchBar from 'components/home/SearchBar.vue';
import FiltersSidebar from 'components/home/FiltersSidebar.vue';
import ToursList from 'components/home/ToursList.vue';
import {
  searchTours,
  aiSearch,
  type RegularSearchParams,
  type AiSearchParams,
  type FilterParams,
  type Tour,
} from 'src/api/filters';
import { useFavoritesStore } from 'src/stores/favorites';
import { useAuthStore } from 'src/stores/auth';

const auth = useAuthStore();
const favorites = useFavoritesStore();

const loading = ref(false);
const tours = ref<Tour[]>([]);
const hasSearched = ref(false);
const isAiSearch = ref(false);

let currentSearchParams: RegularSearchParams | AiSearchParams | null = null;
const currentFilters = ref<FilterParams>({});

async function handleSearch(
  params: RegularSearchParams | AiSearchParams,
  isAi: boolean
) {
  currentSearchParams = params;
  hasSearched.value = true;
  isAiSearch.value = isAi;

  await fetchTours(isAi);
}

async function handleFilterChange(newFilters: FilterParams) {
  currentFilters.value = newFilters;

  if (!currentSearchParams) return;

  if (!isAiSearch.value) {
    await fetchTours(false);
  }
}

async function fetchTours(isAi = false) {
  if (!currentSearchParams) return;

  loading.value = true;

  try {
    if (isAi && 'aiQuery' in currentSearchParams) {
      const response = await aiSearch(currentSearchParams.aiQuery);
      tours.value = response.results;
    } else {
      const response = await searchTours(
        currentSearchParams as RegularSearchParams,
        currentFilters.value
      );
      tours.value = response.results;
    }
  } catch (e) {
    console.error('Search failed:', e);
    tours.value = [];
  } finally {
    loading.value = false;
  }
}

const displayedTours = computed(() => {
  if (!isAiSearch.value) {
    return tours.value;
  }

  return tours.value
    .filter((t) => {
      const meta = t.meta || {};

      if (currentFilters.value.type && meta.rest_type !== currentFilters.value.type)
        return false;

      if (
        currentFilters.value.hotelType &&
        meta.hotel_type !== currentFilters.value.hotelType
      )
        return false;

      if (
        currentFilters.value.category != null &&
        String(meta.hotel_category) !== String(currentFilters.value.category)
      )
        return false;

      if (currentFilters.value.food && meta.meal !== currentFilters.value.food)
        return false;

      if (
        currentFilters.value.priceFrom != null &&
        t.price_per_person < currentFilters.value.priceFrom
      )
        return false;

      if (
        currentFilters.value.priceTo != null &&
        t.price_per_person > currentFilters.value.priceTo
      )
        return false;

      return true;
    })
    .sort((a, b) => {
      switch (currentFilters.value.sort) {
        case 'price_asc':
          return a.price_per_person - b.price_per_person;

        case 'price_desc':
          return b.price_per_person - a.price_per_person;

        case 'hotel_category':
          return (
            Number(b.meta?.hotel_category || 0) -
            Number(a.meta?.hotel_category || 0)
          );

        case 'hotel_type':
          return (a.meta?.hotel_type || '').localeCompare(
            b.meta?.hotel_type || ''
          );

        case 'rest_type':
          return (a.meta?.rest_type || '').localeCompare(
            b.meta?.rest_type || ''
          );

        case 'meal':
          return (a.meta?.meal || '').localeCompare(
            b.meta?.meal || ''
          );

        default:
          return 0;
      }
    });
});

onMounted(async () => {
  if (auth.user) {
    await favorites.loadFavorites();
  }
});
</script>