<template>
  <q-page class="q-pa-lg">
    <div class="row justify-center">
      <SearchBar class="q-mb-md border-radius-md col-12 col-md-10" @search="handleSearch" />
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
        <ToursList :tours="displayedTours" :has-searched="hasSearched" :loading="loading" />
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

const filtersRef = ref<InstanceType<typeof FiltersSidebar>>();
const loading = ref(false);
const tours = ref<Tour[]>([]);
const hasSearched = ref(false);

let currentSearchParams: RegularSearchParams | AiSearchParams | null = null;
let currentFilters: FilterParams = {};

const displayedTours = computed(() => {
  let result = [...tours.value];
  if (currentFilters.priceFrom != null) {
    result = result.filter((t) => t.price_per_person >= currentFilters.priceFrom!);
  }
  if (currentFilters.priceTo != null) {
    result = result.filter((t) => t.price_per_person <= currentFilters.priceTo!);
  }
  return result;
});

async function handleSearch(params: RegularSearchParams | AiSearchParams, isAi: boolean) {
  currentSearchParams = params;
  hasSearched.value = true;
  await fetchTours(isAi);
}

async function handleFilterChange(newFilters: FilterParams) {
  currentFilters = newFilters;
  if (currentSearchParams) {
    const isAi = currentSearchParams && 'aiQuery' in currentSearchParams;
    await fetchTours(isAi);
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
        currentFilters,
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

onMounted(async () => {
  if (auth.user) {
    await favorites.loadFavorites();
  }
});
</script>
